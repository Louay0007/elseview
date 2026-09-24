import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import Membership, User
from app.auth.security import utcnow
from app.auth.service import audit, require_workspace
from app.common.errors import DomainError
from app.common.idempotency import execute_idempotent
from app.common.privacy import authorized_asset, get_scoped, lock_workspace
from app.common.privacy_router import view
from app.common.private_storage import PrivateStorage
from app.studies import methods, service
from app.studies.models import Launch, Study, StudyGrant, StudyVersion
from app.studies.schemas import (
    GrantBody,
    PreviewAnswers,
    PreviewBody,
    RevisionBody,
    StateBody,
    StudyBody,
    VersionBody,
)

router = APIRouter(prefix="/api/v1", tags=["studies"])
Actor = Annotated[User, Depends(current_user)]
Idempotency = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]
PreviewToken = Annotated[str, Header(alias="X-Preview-Token", min_length=1, max_length=4096)]
BASE = "/workspaces/{workspace_id}/studies"
VERSION = BASE + "/{study_id}/versions/{version_id}"


def study_view(study):
    return view(study, "title status ai_policy retention_policy_id created_at")


def version_view(version, author=False):
    result = view(
        version, "study_id number revision state content_hash published_at locales created_at"
    )
    if author:
        result.update(
            blocks_json=version.blocks_json,
            rules_json=version.rules_json,
            consent_documents=version.consent_documents,
        )
    return result


@router.get("/research-methods")
def catalogue(user: Actor):
    return {
        "schema_version": 1,
        "methods": [
            {
                "type": kind,
                "renderer": kind in methods.RENDERERS,
                "events": sorted(methods.EVENTS[kind]),
            }
            for kind in sorted(methods.RENDERERS)
        ],
    }


@router.post(BASE, status_code=201)
def create(
    workspace_id: UUID, body: StudyBody, request: Request, user: Actor, idempotency_key: Idempotency
):
    rate_limit(request, "study_create", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        require_workspace(session, user.id, workspace_id, "studies.create")

        def action():
            study, version = service.create_study(session, workspace_id, user.id, body)
            return 201, {
                "study_id": str(study.id),
                "version_id": str(version.id),
                "revision": version.revision,
            }

        _, result = execute_idempotent(
            session,
            workspace_id,
            user.id,
            "study.create",
            idempotency_key,
            body.model_dump(mode="json"),
            action,
        )
        return result


@router.get(BASE)
def index(
    workspace_id: UUID,
    request: Request,
    user: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    with request.app.state.database.sessions() as session:
        from app.common.privacy import require_unrestricted
        from app.common.privacy_models import PrivacyRestriction

        member = require_workspace(session, user.id, workspace_id, "workspace.read")
        require_unrestricted(session, workspace_id, user.id)
        restricted_owners = (
            select(Membership.id)
            .join(
                PrivacyRestriction,
                (PrivacyRestriction.subject_id == Membership.user_id)
                & (PrivacyRestriction.workspace_id == Membership.workspace_id),
            )
            .where(Membership.workspace_id == workspace_id)
        )
        granted = select(StudyGrant.study_id).where(
            StudyGrant.workspace_id == workspace_id,
            StudyGrant.membership_id == member.id,
            StudyGrant.revoked_at.is_(None),
            StudyGrant.capabilities.contains(["read"]),
        )
        return {
            "items": [
                study_view(study)
                for study in session.scalars(
                    select(Study)
                    .where(
                        Study.workspace_id == workspace_id,
                        (Study.owner_membership_id == member.id) | Study.id.in_(granted),
                        Study.owner_membership_id.not_in(restricted_owners),
                    )
                    .order_by(Study.created_at, Study.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]
        }


@router.get(BASE + "/{study_id}")
def detail(workspace_id: UUID, study_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        return study_view(service.authorize(session, workspace_id, user.id, study_id, "read"))


@router.get(BASE + "/{study_id}/versions")
def versions(
    workspace_id: UUID,
    study_id: UUID,
    request: Request,
    user: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    with request.app.state.database.sessions() as session:
        service.authorize(session, workspace_id, user.id, study_id, "read")
        return {
            "items": [
                version_view(version)
                for version in session.scalars(
                    select(StudyVersion)
                    .where(
                        StudyVersion.workspace_id == workspace_id, StudyVersion.study_id == study_id
                    )
                    .order_by(StudyVersion.number)
                    .offset(offset)
                    .limit(limit)
                )
            ]
        }


@router.get(VERSION)
def version_detail(
    workspace_id: UUID, study_id: UUID, version_id: UUID, request: Request, user: Actor
):
    with request.app.state.database.sessions() as session:
        _, version = service.version_for(
            session, workspace_id, user.id, study_id, version_id, "edit"
        )
        return version_view(version, author=True)


@router.put(VERSION)
def edit(
    workspace_id: UUID,
    study_id: UUID,
    version_id: UUID,
    body: VersionBody,
    request: Request,
    user: Actor,
):
    with request.app.state.database.sessions.begin() as session:
        return version_view(
            service.edit_version(session, workspace_id, user.id, study_id, version_id, body),
            author=True,
        )


@router.post(VERSION + "/validate")
def validate(workspace_id: UUID, study_id: UUID, version_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        _, version = service.version_for(
            session, workspace_id, user.id, study_id, version_id, "edit"
        )
        service.validate_version(session, workspace_id, user.id, version)
        return {
            "valid": True,
            "revision": version.revision,
            "methods": sorted({block["type"] for block in version.blocks_json}),
        }


@router.post(VERSION + "/publish")
def publish(
    workspace_id: UUID,
    study_id: UUID,
    version_id: UUID,
    body: RevisionBody,
    request: Request,
    user: Actor,
):
    with request.app.state.database.sessions.begin() as session:
        return version_view(
            service.publish(
                session, workspace_id, user.id, study_id, version_id, body.expected_revision
            )
        )


@router.post(VERSION + "/new-draft", status_code=201)
def draft(
    workspace_id: UUID,
    study_id: UUID,
    version_id: UUID,
    request: Request,
    user: Actor,
    idempotency_key: Idempotency,
):
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        service.authorize(session, workspace_id, user.id, study_id, "edit")

        def action():
            version = service.new_version(session, workspace_id, user.id, study_id, version_id)
            return 201, {
                "version_id": str(version.id),
                "revision": version.revision,
                "number": version.number,
            }

        _, result = execute_idempotent(
            session,
            workspace_id,
            user.id,
            "study.new_draft",
            idempotency_key,
            {"study": str(study_id), "version": str(version_id)},
            action,
        )
        return result


@router.post(VERSION + "/clone", status_code=201)
def clone(
    workspace_id: UUID,
    study_id: UUID,
    version_id: UUID,
    body: StudyBody,
    request: Request,
    user: Actor,
    idempotency_key: Idempotency,
):
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        service.authorize(session, workspace_id, user.id, study_id, "edit")

        def action():
            study, version = service.clone_study(
                session, workspace_id, user.id, study_id, version_id, body
            )
            return 201, {
                "study_id": str(study.id),
                "version_id": str(version.id),
                "revision": version.revision,
            }

        _, result = execute_idempotent(
            session,
            workspace_id,
            user.id,
            "study.clone",
            idempotency_key,
            body.model_dump(mode="json") | {"source": str(version_id)},
            action,
        )
        return result


@router.post(BASE + "/{study_id}/grants", status_code=201)
def grant(workspace_id: UUID, study_id: UUID, body: GrantBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return view(
            service.grant_access(session, workspace_id, user.id, study_id, body),
            "membership_id capabilities revoked_at",
        )


@router.delete(BASE + "/{study_id}/grants/{grant_id}", status_code=204)
def revoke(workspace_id: UUID, study_id: UUID, grant_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        workspace = lock_workspace(session, workspace_id)
        service.authorize(session, workspace_id, user.id, study_id, "grants")
        grant = get_scoped(session, StudyGrant, workspace_id, grant_id)
        if grant.study_id != study_id:
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        grant.revoked_at = utcnow()
        workspace.privacy_epoch += 1
        audit(session, "study.grant_revoked", user.id, workspace_id, grant.id)


@router.patch(BASE + "/{study_id}/state")
def state(workspace_id: UUID, study_id: UUID, body: StateBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        workspace = lock_workspace(session, workspace_id)
        study = service.authorize(session, workspace_id, user.id, study_id, "publish")
        transitions = {
            "draft": {"closed"},
            "ready": {"paused", "closed"},
            "paused": {"ready", "closed"},
            "closed": {"archived"},
            "archived": set(),
        }
        if body.status != study.status and body.status not in transitions[study.status]:
            raise DomainError("INVALID_STATE", "Study transition is not permitted.", 409)
        study.status = body.status
        if body.status != "archived":
            for launch in session.scalars(
                select(Launch)
                .join(StudyVersion, Launch.version_id == StudyVersion.id)
                .where(StudyVersion.study_id == study.id)
            ):
                launch.state = body.status
        workspace.privacy_epoch += 1
        audit(session, "study.state_changed", user.id, workspace_id, study.id, status=body.status)
        return study_view(study)


@router.post(VERSION + "/preview")
def preview(
    workspace_id: UUID,
    study_id: UUID,
    version_id: UUID,
    body: PreviewBody,
    request: Request,
    user: Actor,
):
    with request.app.state.database.sessions.begin() as session:
        token = service.preview_token(
            session,
            request.app.state.settings,
            workspace_id,
            user,
            request.state.auth_family_id,
            study_id,
            version_id,
            body.locale,
        )
        return {
            "preview_token": token,
            "expires_in": 900,
            "path": "/#preview=" + token,
            "preview": True,
            "persisted": False,
        }


@router.post("/study-preview")
def preview_next(body: PreviewAnswers, request: Request, preview_token: PreviewToken):
    with request.app.state.database.sessions.begin() as session:
        from app.common.privacy_models import ConsentDocument

        claims, version, blocks = service.resolve_preview(
            session, request.app.state.settings, preview_token
        )
        consent = get_scoped(
            session,
            ConsentDocument,
            version.workspace_id,
            UUID(version.consent_documents[claims["locale"]]),
        )
        return service.preview_step(claims, blocks, body.answers) | {
            "consent": {
                "body": consent.body,
                "digest": consent.digest,
                "purpose": consent.purpose,
                "locale": consent.locale,
            }
        }


@router.get("/study-preview/assets/{asset_id}")
def preview_asset(asset_id: UUID, request: Request, preview_token: PreviewToken):
    with request.app.state.database.sessions.begin() as session:
        claims, version, blocks = service.resolve_preview(
            session, request.app.state.settings, preview_token
        )
        if asset_id not in {ref.asset_id for block in blocks for ref in methods.asset_refs(block)}:
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        study = get_scoped(session, Study, version.workspace_id, version.study_id)
        owner = get_scoped(session, Membership, version.workspace_id, study.owner_membership_id)
        asset = authorized_asset(session, version.workspace_id, owner.user_id, asset_id)
        try:
            data = PrivateStorage(request.app.state.settings.private_root).read(
                asset.storage_key, asset.size_bytes
            )
            if len(data) != asset.size_bytes or hashlib.sha256(data).hexdigest() != asset.checksum:
                raise ValueError("Asset integrity failure")
        except (ValueError, OSError):
            raise DomainError("ASSET_UNAVAILABLE", "Asset is not available.", 409) from None
        return Response(
            data,
            media_type="image/png",
            headers={"Content-Security-Policy": "default-src 'none'; sandbox"},
        )
