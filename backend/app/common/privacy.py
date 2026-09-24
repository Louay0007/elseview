import hashlib
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, select

from app.auth.models import Membership, Workspace
from app.auth.security import utcnow
from app.auth.service import audit, require_workspace
from app.common.errors import DomainError
from app.common.privacy_models import (
    Asset,
    AssetLink,
    ConsentDocument,
    ConsentReceipt,
    PrivacyRequest,
    PrivacyRestriction,
    RetentionPolicy,
    UploadIntent,
)
from app.common.private_storage import EXTENSIONS, LIMITS, PrivateStorage


def lock_workspace(session, workspace_id):
    workspace = session.scalar(
        select(Workspace)
        .where(Workspace.id == workspace_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if workspace is None:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    from app.common.dispatch_gate import acquire_for_session

    acquire_for_session(session, workspace_id)
    return workspace


def restricted(session, workspace_id, subject_id):
    return (
        session.scalar(
            select(PrivacyRestriction.id).where(
                PrivacyRestriction.workspace_id == workspace_id,
                PrivacyRestriction.subject_id == subject_id,
            )
        )
        is not None
    )


def require_unrestricted(session, workspace_id, subject_id):
    if restricted(session, workspace_id, subject_id):
        raise DomainError("PRIVACY_RESTRICTED", "Data use has been withdrawn.", 403)


def get_scoped(session, model, workspace_id, resource_id):
    record = session.scalar(
        select(model).where(model.workspace_id == workspace_id, model.id == resource_id)
    )
    if record is None:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    return record


def create_document(session, workspace_id, actor_id, body):
    lock_workspace(session, workspace_id)
    require_workspace(session, actor_id, workspace_id, "privacy.manage")
    data = body.model_dump()
    prior = session.scalar(
        select(ConsentDocument).where(
            ConsentDocument.workspace_id == workspace_id,
            ConsentDocument.document_key == body.document_key,
            ConsentDocument.version == body.version,
            ConsentDocument.locale == body.locale,
        )
    )
    digest = hashlib.sha256(body.body.encode()).hexdigest()
    if prior:
        if prior.digest != digest or prior.purpose != body.purpose:
            raise DomainError("IMMUTABLE_DOCUMENT", "This document version already exists.", 409)
        return prior
    record = ConsentDocument(workspace_id=workspace_id, digest=digest, **data)
    session.add(record)
    session.flush()
    audit(session, "consent.document_created", actor_id, workspace_id, record.id)
    return record


def create_retention(session, workspace_id, actor_id, body):
    lock_workspace(session, workspace_id)
    require_workspace(session, actor_id, workspace_id, "privacy.manage")
    prior = session.scalar(
        select(RetentionPolicy).where(
            RetentionPolicy.workspace_id == workspace_id,
            RetentionPolicy.policy_key == body.policy_key,
            RetentionPolicy.version == body.version,
        )
    )
    if prior:
        if any(getattr(prior, key) != value for key, value in body.model_dump().items()):
            raise DomainError("IMMUTABLE_POLICY", "This retention version already exists.", 409)
        return prior
    record = RetentionPolicy(workspace_id=workspace_id, **body.model_dump())
    session.add(record)
    session.flush()
    audit(session, "retention.created", actor_id, workspace_id, record.id)
    return record


def consent_granted(
    session, workspace_id, subject_id, purpose, document_id=None, study_version_id=None
):
    if purpose == "study" and study_version_id is None:
        return False
    if restricted(session, workspace_id, subject_id):
        return False
    query = (
        select(ConsentReceipt)
        .join(ConsentDocument, ConsentDocument.id == ConsentReceipt.document_id)
        .where(
            ConsentReceipt.workspace_id == workspace_id,
            ConsentReceipt.subject_id == subject_id,
            ConsentDocument.purpose == purpose,
            ConsentReceipt.study_version_id == study_version_id,
        )
    )
    if document_id is not None:
        query = query.where(ConsentReceipt.document_id == document_id)
    latest = session.scalar(
        query.order_by(ConsentReceipt.created_at.desc(), ConsentReceipt.id.desc()).limit(1)
    )
    return latest is not None and latest.decision == "granted"


def record_consent(session, workspace_id, subject_id, body):
    workspace = lock_workspace(session, workspace_id)
    require_workspace(session, subject_id, workspace_id, "workspace.read")
    document = get_scoped(session, ConsentDocument, workspace_id, body.document_id)
    if document.digest != body.presented_digest:
        raise DomainError("CONSENT_MISMATCH", "The displayed consent version does not match.", 409)
    if document.purpose == "study":
        from app.studies.models import StudyVersion

        if body.study_version_id is None:
            raise DomainError(
                "CONSENT_SCOPE_REQUIRED", "Study consent requires the exact published version.", 422
            )
        version = get_scoped(session, StudyVersion, workspace_id, body.study_version_id)
        if version.state != "published" or version.consent_documents.get(document.locale) != str(
            document.id
        ):
            raise DomainError("CONSENT_MISMATCH", "Consent does not match this study version.", 409)
    elif body.study_version_id is not None:
        raise DomainError(
            "CONSENT_MISMATCH", "This consent purpose is not study-version scoped.", 422
        )
    prior = session.scalar(
        select(ConsentReceipt).where(
            ConsentReceipt.workspace_id == workspace_id,
            ConsentReceipt.subject_id == subject_id,
            ConsentReceipt.receipt_key == body.receipt_key,
        )
    )
    if prior:
        if any(getattr(prior, key) != value for key, value in body.model_dump().items()):
            raise DomainError("IDEMPOTENCY_CONFLICT", "Receipt key already used.", 409)
        return prior
    if body.decision == "granted":
        require_unrestricted(session, workspace_id, subject_id)
    receipt = ConsentReceipt(
        workspace_id=workspace_id, subject_id=subject_id, created_at=utcnow(), **body.model_dump()
    )
    session.add(receipt)
    if body.decision != "granted":
        from app.privacy_ops.events import record_event

        # Reference grants already present in older backups, not this new receipt.
        for prior_grant in session.scalars(
            select(ConsentReceipt)
            .join(ConsentDocument, ConsentDocument.id == ConsentReceipt.document_id)
            .where(
                ConsentReceipt.workspace_id == workspace_id,
                ConsentReceipt.subject_id == subject_id,
                ConsentReceipt.study_version_id == body.study_version_id,
                ConsentDocument.purpose == document.purpose,
                ConsentReceipt.decision == "granted",
            )
        ):
            record_event(session, workspace_id, "consent_revoke", prior_grant.id)
        workspace.privacy_epoch += 1
        if document.purpose == "recording":
            for asset in session.scalars(
                select(Asset).where(
                    Asset.workspace_id == workspace_id,
                    Asset.owner_id == subject_id,
                    Asset.purpose == "recording",
                    Asset.state != "purged",
                )
            ):
                asset.state = "blocked"
    session.flush()
    audit(session, "consent.recorded", subject_id, workspace_id, receipt.id, decision=body.decision)
    return receipt


def create_upload(session, workspace_id, actor_id, body, settings):
    lock_workspace(session, workspace_id)
    require_workspace(session, actor_id, workspace_id, "assets.create")
    require_unrestricted(session, workspace_id, actor_id)
    if (
        body.size_bytes > LIMITS[body.media_type]
        or body.filename.rsplit(".", 1)[-1] != EXTENSIONS[body.media_type]
    ):
        raise DomainError("INVALID_FILE", "File type or size is unsupported.", 422)
    if body.media_type == "audio/wav" and body.purpose != "recording":
        raise DomainError("RECORDING_CONSENT_REQUIRED", "Audio requires recording consent.", 422)
    if body.purpose == "recording" and (
        body.media_type != "audio/wav"
        or not consent_granted(session, workspace_id, actor_id, "recording")
    ):
        raise DomainError("RECORDING_CONSENT_REQUIRED", "Recording consent is required.", 403)
    policy = get_scoped(session, RetentionPolicy, workspace_id, body.retention_policy_id)
    prior = session.scalar(
        select(UploadIntent).where(
            UploadIntent.workspace_id == workspace_id,
            UploadIntent.uploader_id == actor_id,
            UploadIntent.upload_key == body.upload_key,
        )
    )
    if prior:
        asset = get_scoped(session, Asset, workspace_id, prior.asset_id)
        expected = {
            "media_type": body.media_type,
            "purpose": body.purpose,
            "size_bytes": body.size_bytes,
            "checksum": body.checksum,
            "retention_policy_id": body.retention_policy_id,
            "extension": EXTENSIONS[body.media_type],
        }
        if any(getattr(asset, key) != value for key, value in expected.items()):
            raise DomainError("IDEMPOTENCY_CONFLICT", "Upload key already used.", 409)
        return asset, prior
    from sqlalchemy import func

    total = session.scalar(
        select(func.coalesce(func.sum(Asset.size_bytes), 0)).where(
            Asset.workspace_id == workspace_id, Asset.state != "purged"
        )
    )
    if total + body.size_bytes > settings.private_workspace_bytes:
        raise DomainError("STORAGE_QUOTA", "Workspace storage quota exceeded.", 409)
    asset = Asset(
        workspace_id=workspace_id,
        owner_id=actor_id,
        storage_key=uuid4().hex,
        media_type=body.media_type,
        extension=EXTENSIONS[body.media_type],
        purpose=body.purpose,
        size_bytes=body.size_bytes,
        checksum=body.checksum,
        retention_policy_id=policy.id,
        retention_until=utcnow()
        + timedelta(
            days=policy.media_days
            if body.media_type.startswith(("audio/", "image/"))
            else policy.raw_days
        ),
    )
    session.add(asset)
    session.flush()
    intent = UploadIntent(
        workspace_id=workspace_id,
        asset_id=asset.id,
        uploader_id=actor_id,
        upload_key=body.upload_key,
        expires_at=utcnow() + timedelta(hours=1),
    )
    session.add(intent)
    session.flush()
    audit(session, "asset.intent_created", actor_id, workspace_id, asset.id)
    return asset, intent


def authorized_asset(session, workspace_id, actor_id, asset_id, *, owner=False, ready=True):
    member = require_workspace(session, actor_id, workspace_id, "workspace.read")
    asset = get_scoped(session, Asset, workspace_id, asset_id)
    allowed = asset.owner_id == actor_id or member.role in {"owner", "admin"}
    if not allowed and not owner:
        allowed = (
            session.scalar(
                select(AssetLink.id).where(
                    AssetLink.workspace_id == workspace_id,
                    AssetLink.asset_id == asset.id,
                    AssetLink.owner_membership_id == member.id,
                    AssetLink.revoked_at.is_(None),
                )
            )
            is not None
        )
    if not allowed:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    require_unrestricted(session, workspace_id, asset.owner_id)
    if ready and (asset.state != "ready" or asset.retention_until <= utcnow()):
        raise DomainError("ASSET_UNAVAILABLE", "Asset is not available.", 409)
    if asset.purpose == "recording" and not consent_granted(
        session, workspace_id, asset.owner_id, "recording"
    ):
        raise DomainError("RECORDING_CONSENT_REQUIRED", "Recording consent is required.", 403)
    if asset.purpose == "recording":
        from app.longitudinal.models import Recording
        from app.longitudinal.service import recording_allowed

        if session.scalar(
            select(Recording.id).where(Recording.asset_id == asset.id)
        ) and not recording_allowed(session, asset):
            raise DomainError(
                "RECORDING_CONSENT_REQUIRED", "Participant recording consent is required.", 403
            )
    return asset


def create_request(session, workspace_id, subject_id, body, *, account_request_id=None):
    workspace = lock_workspace(session, workspace_id)
    member = session.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == subject_id
        )
    )
    if member is None:
        from app.recruiting.models import Candidate

        participant = session.scalar(
            select(Candidate.id)
            .where(
                Candidate.workspace_id == workspace_id,
                Candidate.subject_id == subject_id,
            )
            .limit(1)
        )
        if participant is None:
            from app.privacy_ops.account_models import AccountErasure

            account_request = (
                session.get(AccountErasure, account_request_id) if account_request_id else None
            )
            if not (
                account_request
                and account_request.subject_id == subject_id
                and str(workspace_id) in account_request.workspace_ids
                and body.kind == "erasure"
            ):
                raise DomainError("NOT_FOUND", "Resource not found.", 404)
    prior = session.scalar(
        select(PrivacyRequest).where(
            PrivacyRequest.workspace_id == workspace_id,
            PrivacyRequest.subject_id == subject_id,
            PrivacyRequest.request_key == body.request_key,
        )
    )
    if prior:
        if prior.kind != body.kind:
            raise DomainError("IDEMPOTENCY_CONFLICT", "Request key already used.", 409)
        return prior
    record = PrivacyRequest(workspace_id=workspace_id, subject_id=subject_id, **body.model_dump())
    session.add(record)
    session.flush()
    if body.kind != "access":
        from app.privacy_ops.service import tombstone

        tombstone(
            session,
            workspace_id,
            subject_id,
            "erasure" if body.kind == "erasure" else "restriction",
        )
        from app.collaboration.privacy import invalidate_subject as invalidate_collaboration

        invalidate_collaboration(session, workspace_id, subject_id)
        from app.privacy_ops.service import invalidate_subject_safely

        invalidate_subject_safely(session, workspace_id, subject_id)
        if not restricted(session, workspace_id, subject_id):
            session.add(PrivacyRestriction(workspace_id=workspace_id, subject_id=subject_id))
        workspace.privacy_epoch += 1
        from app.collection.privacy import withdraw_subject
        from app.privacy_ops.service import held

        if not held(session, workspace_id, subject_id):
            withdraw_subject(session, workspace_id, subject_id)
        for asset in session.scalars(
            select(Asset).where(
                Asset.workspace_id == workspace_id,
                Asset.owner_id == subject_id,
                Asset.state != "purged",
            )
        ):
            asset.state = "purging" if body.kind == "erasure" else "blocked"
        if body.kind == "erasure":
            from app.jobs.service import enqueue

            session.flush()
            enqueue(
                session,
                workspace_id=workspace_id,
                requester_id=subject_id,
                kind="privacy.erase",
                target_id=record.id,
                command_key=f"privacy-{record.id}",
                internal=True,
            )
        else:
            record.state, record.completed_at = "completed", utcnow()
    else:
        record.state, record.completed_at = "completed", utcnow()
    audit(session, "privacy.requested", subject_id, workspace_id, record.id, kind=body.kind)
    return record


def privacy_job_allowed(session, job):
    return (
        session.scalar(
            select(PrivacyRequest.id).where(
                PrivacyRequest.id == job.target_id,
                PrivacyRequest.workspace_id == job.workspace_id,
                PrivacyRequest.subject_id == job.requester_id,
                PrivacyRequest.kind == "erasure",
            )
        )
        is not None
    )


def erase_files(database, settings, job):
    with database.sessions.begin() as session:
        lock_workspace(session, job.workspace_id)
        request = get_scoped(session, PrivacyRequest, job.workspace_id, job.target_id)
        from app.privacy_ops.service import workspace_held

        if workspace_held(session, job.workspace_id):
            return {"status": "ok"}
        keys = list(
            session.scalars(
                select(Asset.storage_key).where(
                    Asset.workspace_id == job.workspace_id,
                    Asset.owner_id == request.subject_id,
                    Asset.state != "purged",
                )
            )
        )
        from app.longitudinal.service import recording_assets

        keys.extend(
            asset.storage_key
            for asset in recording_assets(session, job.workspace_id, request.subject_id)
        )
        storage = PrivateStorage(settings.private_root)
        for key in keys:
            storage.delete(key)
    return {"status": "ok"}


# Registry callbacks are lazy to avoid model/service import cycles. Dependencies are
# explicit and failures propagate: never mark an incomplete erase completed.
_ERASURE_HANDLERS = {}


def register_handler(name, callback, *, after=()):
    if name in _ERASURE_HANDLERS:
        raise ValueError("Duplicate privacy handler: " + name)
    _ERASURE_HANDLERS[name] = (callback, tuple(after))


def run_erasure_handlers(session, workspace_id, subject_id):
    pending = dict(_ERASURE_HANDLERS)
    done = set()
    while pending:
        ready = [name for name, (_, deps) in pending.items() if set(deps) <= done]
        if not ready:
            raise RuntimeError("Privacy registry dependency cycle or missing dependency")
        for name in ready:
            callback, _ = pending.pop(name)
            callback(session, workspace_id, subject_id)
            session.flush()
            done.add(name)


def _lazy_handler(module, function):
    def call(session, workspace_id, subject_id):
        from importlib import import_module

        getattr(import_module(module), function)(session, workspace_id, subject_id)

    return call


def _linked_assets(session, workspace_id, subject_id):
    from app.longitudinal.service import recording_assets

    for asset in recording_assets(session, workspace_id, subject_id):
        asset.state = "purged"
        session.execute(delete(AssetLink).where(AssetLink.asset_id == asset.id))
        session.execute(delete(UploadIntent).where(UploadIntent.asset_id == asset.id))


def _assets_receipts(session, workspace_id, subject_id):
    for asset in session.scalars(
        select(Asset).where(Asset.workspace_id == workspace_id, Asset.owner_id == subject_id)
    ):
        asset.state = "purged"
        session.execute(delete(AssetLink).where(AssetLink.asset_id == asset.id))
        session.execute(delete(UploadIntent).where(UploadIntent.asset_id == asset.id))
    session.execute(
        delete(ConsentReceipt).where(
            ConsentReceipt.workspace_id == workspace_id, ConsentReceipt.subject_id == subject_id
        )
    )


register_handler("linked_assets", _linked_assets)
register_handler(
    "longitudinal",
    _lazy_handler("app.longitudinal.service", "purge_subject"),
    after=("linked_assets",),
)
register_handler(
    "collection_analytics_ai_reviews",
    _lazy_handler("app.collection.privacy", "purge_subject"),
    after=("longitudinal",),
)
register_handler(
    "evaluation",
    _lazy_handler("app.evaluation.privacy", "purge_subject"),
    after=("collection_analytics_ai_reviews",),
)
register_handler(
    "financial", _lazy_handler("app.reviews.privacy", "minimize_financial"), after=("evaluation",)
)
register_handler(
    "recruiting", _lazy_handler("app.recruiting.service", "erase_subject"), after=("financial",)
)
register_handler("assets_consent", _assets_receipts, after=("recruiting",))
register_handler(
    "studies_templates",
    _lazy_handler("app.studies.service", "purge_owned_studies"),
    after=("assets_consent",),
)
register_handler(
    "operational_collaboration",
    _lazy_handler("app.privacy_ops.producers", "purge_subject"),
    after=("studies_templates",),
)


def finish_erasure(session, job):
    request = get_scoped(session, PrivacyRequest, job.workspace_id, job.target_id)
    from app.privacy_ops.service import workspace_held

    if workspace_held(session, job.workspace_id):
        return
    run_erasure_handlers(session, job.workspace_id, request.subject_id)
    request.state, request.completed_at = "completed", utcnow()


def sweep_storage(database, settings, workspace_id, actor_id):
    with database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        require_workspace(session, actor_id, workspace_id, "privacy.manage")
        expired = select(UploadIntent.asset_id).where(
            UploadIntent.expires_at <= utcnow(), UploadIntent.completed_at.is_(None)
        )
        from sqlalchemy import and_, or_

        from app.longitudinal.models import Recording
        from app.privacy_ops.events import record_event
        from app.privacy_ops.models import LegalHold
        from app.privacy_ops.service import held_asset, reviewed_cutoff

        media = or_(Asset.media_type.like("audio/%"), Asset.media_type.like("image/%"))
        expiry = [
            Asset.retention_until <= utcnow(),
            Asset.id.in_(expired),
            Asset.state == "purging",
        ]
        for purpose, predicate in (("media", media), ("raw", ~media)):
            cutoff = reviewed_cutoff(session, workspace_id, purpose)
            if cutoff is not None:
                expiry.append(and_(predicate, Asset.created_at <= cutoff))
        owner_hold = (
            select(LegalHold.id)
            .where(
                LegalHold.workspace_id == Asset.workspace_id,
                LegalHold.subject_id == Asset.owner_id,
                LegalHold.released_at.is_(None),
            )
            .exists()
        )
        recording_hold = (
            select(Recording.id)
            .join(
                LegalHold,
                and_(
                    LegalHold.workspace_id == Recording.workspace_id,
                    LegalHold.subject_id == Recording.subject_id,
                    LegalHold.released_at.is_(None),
                ),
            )
            .where(Recording.workspace_id == Asset.workspace_id, Recording.asset_id == Asset.id)
            .exists()
        )
        assets = session.scalars(
            select(Asset)
            .where(
                Asset.workspace_id == workspace_id,
                Asset.state != "purged",
                or_(*expiry),
                ~owner_hold,
                ~recording_hold,
            )
            .order_by(Asset.created_at, Asset.id)
            .limit(100)
        ).all()
        selected = [(asset.id, asset.storage_key) for asset in assets]
        for asset in assets:
            record_event(session, workspace_id, "asset_delete", asset.id)
            asset.state = "purging"
    storage = PrivateStorage(settings.private_root)
    purged = 0
    for asset_id, key in selected:
        with database.sessions.begin() as session:
            lock_workspace(session, workspace_id)
            asset = get_scoped(session, Asset, workspace_id, asset_id)
            if held_asset(session, asset):
                asset.state = "blocked"
                continue
            storage.delete(key)
            asset.state = "purged"
            purged += 1
    return purged
