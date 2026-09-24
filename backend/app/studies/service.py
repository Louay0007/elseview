import copy
import hashlib
import random
from datetime import timedelta
from uuid import UUID, uuid4

import jwt
from pydantic import ValidationError
from sqlalchemy import select

from app.auth.models import Membership, RefreshToken, User
from app.auth.security import utcnow
from app.auth.service import audit, require_workspace
from app.common.cache import canonical_json
from app.common.errors import DomainError
from app.common.privacy import authorized_asset, get_scoped, lock_workspace, require_unrestricted
from app.common.privacy_models import ConsentDocument, RetentionPolicy
from app.studies import methods
from app.studies.models import Launch, Study, StudyGrant, StudyVersion

ROLE_CAPABILITIES = {
    "owner": {"read", "edit", "publish", "preview", "raw", "export", "ai", "review"},
    "admin": {"read", "edit", "publish", "preview", "raw", "export", "ai", "review"},
    "researcher": {"read", "edit", "publish", "preview", "raw", "export", "ai"},
    "reviewer": {"read", "review"},
    "viewer": {"read"},
}


def authorize(session, workspace_id, user_id, study_id, capability):
    member = require_workspace(session, user_id, workspace_id, "workspace.read")
    study = get_scoped(session, Study, workspace_id, study_id)
    owner = get_scoped(session, Membership, workspace_id, study.owner_membership_id)
    require_unrestricted(session, workspace_id, owner.user_id)
    require_unrestricted(session, workspace_id, user_id)
    if capability == "grants":
        if member.role not in {"owner", "admin"} and member.id != study.owner_membership_id:
            raise DomainError("FORBIDDEN", "Study administration is not permitted.", 403)
        return study
    if capability not in ROLE_CAPABILITIES[member.role]:
        raise DomainError("FORBIDDEN", "Study capability is not permitted.", 403)
    if member.id != study.owner_membership_id:
        grant = session.scalar(
            select(StudyGrant).where(
                StudyGrant.workspace_id == workspace_id,
                StudyGrant.study_id == study_id,
                StudyGrant.membership_id == member.id,
                StudyGrant.revoked_at.is_(None),
            )
        )
        if grant is None or capability not in grant.capabilities:
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
    if capability == "ai" and study.ai_policy == "human_only":
        raise DomainError("AI_DISABLED", "This study permits human-only processing.", 403)
    return study


def create_study(session, workspace_id, actor_id, body):
    lock_workspace(session, workspace_id)
    member = require_workspace(session, actor_id, workspace_id, "studies.create")
    require_unrestricted(session, workspace_id, actor_id)
    get_scoped(session, RetentionPolicy, workspace_id, body.retention_policy_id)
    study = Study(workspace_id=workspace_id, owner_membership_id=member.id, **body.model_dump())
    session.add(study)
    session.flush()
    version = StudyVersion(workspace_id=workspace_id, study_id=study.id, number=1)
    session.add(version)
    session.flush()
    audit(session, "study.created", actor_id, workspace_id, study.id)
    return study, version


def version_for(session, workspace_id, actor_id, study_id, version_id, capability):
    study = authorize(session, workspace_id, actor_id, study_id, capability)
    version = get_scoped(session, StudyVersion, workspace_id, version_id)
    if version.study_id != study.id:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    return study, version


def assert_revision(version, revision):
    if version.revision != revision:
        raise DomainError("REVISION_CONFLICT", "The draft changed. Reload before editing.", 409)


def edit_version(session, workspace_id, actor_id, study_id, version_id, body):
    lock_workspace(session, workspace_id)
    require_unrestricted(session, workspace_id, actor_id)
    study, version = version_for(session, workspace_id, actor_id, study_id, version_id, "edit")
    if version.state != "draft" or study.status in {"closed", "archived"}:
        raise DomainError(
            "IMMUTABLE_VERSION", "Create a new draft to change published content.", 409
        )
    assert_revision(version, body.expected_revision)
    try:
        for block in body.blocks_json:
            methods.parse_block(block)
        canonical_json(body.model_dump(mode="json"))
    except (ValueError, TypeError):
        raise DomainError(
            "INVALID_BLOCK", "Unsupported or invalid block configuration.", 422
        ) from None
    version.blocks_json = copy.deepcopy(body.blocks_json)
    version.rules_json = copy.deepcopy(body.rules_json)
    version.locales = body.locales
    version.consent_documents = {key: str(value) for key, value in body.consent_documents.items()}
    version.revision += 1
    audit(session, "study.draft_changed", actor_id, workspace_id, version.id)
    return version


def validate_version(session, workspace_id, actor_id, version):
    try:
        blocks = methods.validate_structure(
            version.blocks_json, version.locales, version.rules_json
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        raise DomainError(
            "INVALID_STUDY", "Study methods, rules, branches or translations are invalid.", 422
        ) from None
    if set(version.consent_documents) != set(version.locales):
        raise DomainError(
            "CONSENT_REQUIRED", "Every study language requires a consent document.", 422
        )
    identity = None
    for locale, document_id in version.consent_documents.items():
        document = get_scoped(session, ConsentDocument, workspace_id, UUID(document_id))
        if document.purpose != "study" or document.locale != locale:
            raise DomainError(
                "CONSENT_MISMATCH", "Consent purpose or language does not match.", 422
            )
        current = (document.document_key, document.version)
        if identity and identity != current:
            raise DomainError(
                "CONSENT_MISMATCH", "Translations must share a document version.", 422
            )
        identity = current
    study = get_scoped(session, Study, workspace_id, version.study_id)
    owner = get_scoped(session, Membership, workspace_id, study.owner_membership_id)
    require_unrestricted(session, workspace_id, owner.user_id)
    for block in blocks:
        for ref in methods.asset_refs(block):
            asset = authorized_asset(session, workspace_id, owner.user_id, ref.asset_id)
            if block.type == "language.review":
                if (
                    asset.purpose != "stimulus"
                    or asset.media_type != "text/plain"
                    or hashlib.sha256(block.config.source_text.encode("utf-8")).hexdigest()
                    != asset.checksum
                ):
                    raise DomainError(
                        "INVALID_SOURCE", "Source text must match the pinned UTF-8 stimulus.", 422
                    )
                continue
            if block.type == "first_click" and (
                asset.width != block.config.asset_width or asset.height != block.config.asset_height
            ):
                raise DomainError(
                    "INVALID_DIMENSIONS", "Dimensions must match the pinned asset.", 422
                )
            if (
                asset.purpose != "stimulus"
                or asset.media_type != "image/png"
                or not asset.width
                or not asset.height
            ):
                raise DomainError(
                    "INVALID_STIMULUS", "Core visual methods require a validated PNG stimulus.", 422
                )
    return blocks


def publish(session, workspace_id, actor_id, study_id, version_id, revision):
    lock_workspace(session, workspace_id)
    require_unrestricted(session, workspace_id, actor_id)
    study, version = version_for(session, workspace_id, actor_id, study_id, version_id, "publish")
    assert_revision(version, revision)
    if version.state == "published":
        validate_version(session, workspace_id, actor_id, version)
        return version
    if study.status in {"closed", "archived"}:
        raise DomainError("STUDY_CLOSED", "This study is closed.", 409)
    validate_version(session, workspace_id, actor_id, version)
    content = {
        "blocks": version.blocks_json,
        "rules": version.rules_json,
        "locales": version.locales,
        "consent": version.consent_documents,
        "retention_policy_id": str(study.retention_policy_id),
        "ai_policy": study.ai_policy,
        "method_schema": 1,
    }
    version.content_hash = hashlib.sha256(canonical_json(content)).hexdigest()
    version.state, version.published_at = "published", utcnow()
    session.flush()
    session.add(Launch(workspace_id=workspace_id, version_id=version.id))
    from app.billing.service import publication_charge

    publication_charge(session, workspace_id, version.id)
    study.status = "ready"
    audit(session, "study.published", actor_id, workspace_id, version.id)
    return version


def new_version(session, workspace_id, actor_id, study_id, version_id):
    lock_workspace(session, workspace_id)
    study, source = version_for(session, workspace_id, actor_id, study_id, version_id, "edit")
    require_unrestricted(session, workspace_id, actor_id)
    if study.status in {"closed", "archived"}:
        raise DomainError("STUDY_CLOSED", "This study is closed.", 409)
    existing = session.scalar(
        select(StudyVersion).where(StudyVersion.study_id == study_id, StudyVersion.state == "draft")
    )
    if existing:
        raise DomainError("DRAFT_EXISTS", "Edit the existing draft first.", 409)
    from sqlalchemy import func

    number = (
        session.scalar(
            select(func.max(StudyVersion.number)).where(StudyVersion.study_id == study_id)
        )
        + 1
    )
    version = StudyVersion(
        workspace_id=workspace_id,
        study_id=study.id,
        number=number,
        blocks_json=copy.deepcopy(source.blocks_json),
        rules_json=copy.deepcopy(source.rules_json),
        locales=list(source.locales),
        consent_documents=dict(source.consent_documents),
    )
    session.add(version)
    session.flush()
    audit(session, "study.version_created", actor_id, workspace_id, version.id)
    return version


def clone_study(session, workspace_id, actor_id, study_id, version_id, body):
    lock_workspace(session, workspace_id)
    _, source = version_for(session, workspace_id, actor_id, study_id, version_id, "edit")
    study, draft = create_study(session, workspace_id, actor_id, body)
    for name in ("blocks_json", "rules_json", "locales", "consent_documents"):
        setattr(draft, name, copy.deepcopy(getattr(source, name)))
    audit(session, "study.cloned", actor_id, workspace_id, study.id)
    return study, draft


def grant_access(session, workspace_id, actor_id, study_id, body):
    workspace = lock_workspace(session, workspace_id)
    authorize(session, workspace_id, actor_id, study_id, "grants")
    actor = require_workspace(session, actor_id, workspace_id, "workspace.read")
    target = get_scoped(session, Membership, workspace_id, body.membership_id)
    if (
        target.status != "active"
        or not set(body.capabilities) <= ROLE_CAPABILITIES[target.role]
        or not set(body.capabilities) <= ROLE_CAPABILITIES[actor.role]
    ):
        raise DomainError("FORBIDDEN", "Grant exceeds the permitted role capabilities.", 403)
    grant = session.scalar(
        select(StudyGrant).where(
            StudyGrant.workspace_id == workspace_id,
            StudyGrant.study_id == study_id,
            StudyGrant.membership_id == target.id,
        )
    )
    if grant is None:
        grant = StudyGrant(workspace_id=workspace_id, study_id=study_id, membership_id=target.id)
        session.add(grant)
    grant.capabilities, grant.revoked_at = body.capabilities, None
    workspace.privacy_epoch += 1
    session.flush()
    audit(
        session,
        "study.grant_changed",
        actor_id,
        workspace_id,
        grant.id,
        capabilities=body.capabilities,
    )
    return grant


def preview_token(session, settings, workspace_id, actor, family_id, study_id, version_id, locale):
    workspace = lock_workspace(session, workspace_id)
    study, version = version_for(session, workspace_id, actor.id, study_id, version_id, "preview")
    require_unrestricted(session, workspace_id, actor.id)
    if study.status in {"closed", "archived"}:
        raise DomainError("STUDY_CLOSED", "This study is closed.", 409)
    validate_version(session, workspace_id, actor.id, version)
    if locale not in version.locales:
        raise DomainError("INVALID_LOCALE", "Study language is unavailable.", 422)
    now = utcnow()
    return jwt.encode(
        {
            "iss": "elseview-preview",
            "aud": "elseview-preview",
            "type": "preview",
            "sub": str(actor.id),
            "family": str(family_id),
            "auth_version": actor.auth_version,
            "workspace": str(workspace_id),
            "study": str(study_id),
            "version": str(version_id),
            "revision": version.revision,
            "epoch": workspace.privacy_epoch,
            "locale": locale,
            "jti": uuid4().hex,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )


def resolve_preview(session, settings, token):
    try:
        claims = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
            issuer="elseview-preview",
            audience="elseview-preview",
            options={
                "require": [
                    "sub",
                    "family",
                    "workspace",
                    "study",
                    "version",
                    "revision",
                    "epoch",
                    "locale",
                    "jti",
                    "iat",
                    "exp",
                    "auth_version",
                    "type",
                ]
            },
        )
        if claims["type"] != "preview":
            raise ValueError()
        workspace_id, user_id = UUID(claims["workspace"]), UUID(claims["sub"])
        workspace = lock_workspace(session, workspace_id)
        user = session.get(User, user_id)
        family = session.scalar(
            select(RefreshToken.id).where(
                RefreshToken.family_id == UUID(claims["family"]),
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.used_at.is_(None),
                RefreshToken.expires_at > utcnow(),
            )
        )
        if (
            not user
            or not family
            or user.auth_version != claims["auth_version"]
            or workspace.privacy_epoch != claims["epoch"]
        ):
            raise ValueError()
        require_unrestricted(session, workspace_id, user_id)
        study, version = version_for(
            session,
            workspace_id,
            user_id,
            UUID(claims["study"]),
            UUID(claims["version"]),
            "preview",
        )
        if version.revision != claims["revision"] or study.status in {"closed", "archived"}:
            raise ValueError()
        return claims, version, validate_version(session, workspace_id, user_id, version)
    except (jwt.PyJWTError, ValueError, KeyError, TypeError, ValidationError):
        raise DomainError(
            "PREVIEW_EXPIRED", "Preview expired or changed. Create a new preview.", 401
        ) from None


def purge_owned_studies(session, workspace_id, subject_id):
    from sqlalchemy import delete

    memberships = select(Membership.id).where(
        Membership.workspace_id == workspace_id, Membership.user_id == subject_id
    )
    studies = list(
        session.scalars(
            select(Study.id).where(
                Study.workspace_id == workspace_id, Study.owner_membership_id.in_(memberships)
            )
        )
    )
    if not studies:
        return
    versions = select(StudyVersion.id).where(StudyVersion.study_id.in_(studies))
    launch_ids = list(session.scalars(select(Launch.id).where(Launch.version_id.in_(versions))))
    from app.analytics.service import purge_studies
    from app.collection.privacy import purge_launches
    from app.evaluation.privacy import purge_studies as purge_evaluation
    from app.longitudinal.service import purge_studies as purge_longitudinal
    from app.recruiting.service import erase_launches

    purge_longitudinal(session, workspace_id, studies)

    purge_evaluation(session, workspace_id, studies)
    purge_studies(session, workspace_id, studies)
    purge_launches(session, workspace_id, launch_ids)
    erase_launches(session, workspace_id, launch_ids)
    from app.common.privacy_models import ConsentReceipt

    session.execute(delete(ConsentReceipt).where(ConsentReceipt.study_version_id.in_(versions)))
    session.execute(delete(Launch).where(Launch.version_id.in_(versions)))
    session.execute(delete(StudyGrant).where(StudyGrant.study_id.in_(studies)))
    session.execute(delete(StudyVersion).where(StudyVersion.study_id.in_(studies)))
    session.execute(delete(Study).where(Study.id.in_(studies)))


def assignment(claims, block):
    return hashlib.sha256(f"{claims['jti']}:{block.block_key}".encode()).hexdigest()


def safe_block(claims, block):
    result = block.model_dump(mode="json", exclude={"branches"})
    result["prompt"] = block.prompt[claims["locale"]]
    config = result["config"]
    if isinstance(block.config, methods.ChoiceConfig):
        for option in config["options"]:
            option["label"] = option["label"][claims["locale"]]
        if block.config.randomize_options:
            random.Random(assignment(claims, block)).shuffle(config["options"])
    if isinstance(block.config, methods.PreferenceConfig):
        for variant in config["variants"]:
            variant["label"] = variant["label"][claims["locale"]]
        random.Random(assignment(claims, block)).shuffle(config["variants"])
        result["assignment_id"] = assignment(claims, block)
    if isinstance(block.config, methods.ExposureConfig):
        result["attempt_id"] = assignment(claims, block)
    if isinstance(block.config, methods.RatingConfig):
        config["endpoint_labels"] = {
            key: value[claims["locale"]] for key, value in config["endpoint_labels"].items()
        }
    if isinstance(block.config, methods.PrototypeConfig) and isinstance(
        block.config.target, methods.ExternalLink
    ):
        config["target"].pop("authorization_ref")
    return methods.advanced.project(result, claims["locale"])


def preview_step(claims, blocks, answers):
    if len(answers) > 100:
        raise DomainError("INVALID_PREVIEW", "Too many preview answers.", 422)
    positions = {block.block_key: index for index, block in enumerate(blocks)}
    key = blocks[0].block_key
    validated = {}
    try:
        while key is not None and key in answers:
            block = blocks[positions[key]]
            validated[key] = methods.validate_answer(
                block,
                answers[key],
                [claims["locale"]],
                assignment(claims, block),
                assignment(claims, block),
            )
            if validated[key]["status"] == "unable":
                key = None
                break
            key = methods.next_key(blocks, positions[key], validated)
    except (ValueError, TypeError):
        raise DomainError("INVALID_PREVIEW_ANSWER", "Preview answer is invalid.", 422) from None
    stale = set(answers) - set(validated)
    if stale:
        raise DomainError(
            "INVALID_PREVIEW_PATH", "Remove answers outside the current study path.", 409
        )
    return {
        "preview": True,
        "persisted": False,
        "rewards": False,
        "locale": claims["locale"],
        "complete": key is None,
        "incomplete": any(value["status"] == "unable" for value in validated.values()),
        "block": safe_block(claims, blocks[positions[key]]) if key is not None else None,
        "answered": len(validated),
    }
