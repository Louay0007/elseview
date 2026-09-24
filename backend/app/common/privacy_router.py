import asyncio
import csv
import hashlib
import os
import wave
import zlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import Membership, User
from app.auth.security import utcnow
from app.auth.service import require_workspace
from app.common import privacy
from app.common.errors import DomainError
from app.common.privacy_models import (
    AssetLink,
    ConsentDocument,
    ConsentReceipt,
    PrivacyRequest,
    RetentionPolicy,
    UploadIntent,
)
from app.common.privacy_schemas import (
    DocumentBody,
    LinkBody,
    PrivacyBody,
    ReceiptBody,
    RetentionBody,
    UploadBody,
)
from app.common.private_storage import PrivateStorage, validate_content

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}", tags=["privacy", "assets"])
Actor = Annotated[User, Depends(current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=10000)]


def view(record, fields):
    return {key: getattr(record, key) for key in ("id", *fields.split())}


def asset_view(asset):
    return view(
        asset,
        "media_type purpose size_bytes checksum state width height duration_ms retention_until",
    )


@router.post("/consent-documents", status_code=201)
def document_create(workspace_id: UUID, body: DocumentBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return view(
            privacy.create_document(session, workspace_id, user.id, body),
            "document_key version locale purpose body digest",
        )


@router.get("/consent-documents")
def documents(
    workspace_id: UUID, request: Request, user: Actor, limit: Limit = 25, offset: Offset = 0
):
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "workspace.read")
        return {
            "items": [
                view(row, "document_key version locale purpose body digest")
                for row in session.scalars(
                    select(ConsentDocument)
                    .where(ConsentDocument.workspace_id == workspace_id)
                    .order_by(ConsentDocument.created_at, ConsentDocument.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]
        }


@router.post("/consent-receipts", status_code=201)
def receipt_create(workspace_id: UUID, body: ReceiptBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return view(
            privacy.record_consent(session, workspace_id, user.id, body),
            "document_id study_version_id decision presented_digest created_at",
        )


@router.get("/consent-receipts")
def receipts(
    workspace_id: UUID, request: Request, user: Actor, limit: Limit = 25, offset: Offset = 0
):
    with request.app.state.database.sessions() as session:
        return {
            "items": [
                view(row, "document_id study_version_id decision presented_digest created_at")
                for row in session.scalars(
                    select(ConsentReceipt)
                    .where(
                        ConsentReceipt.workspace_id == workspace_id,
                        ConsentReceipt.subject_id == user.id,
                    )
                    .order_by(ConsentReceipt.created_at, ConsentReceipt.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]
        }


@router.post("/retention-policies", status_code=201)
def retention_create(workspace_id: UUID, body: RetentionBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return view(
            privacy.create_retention(session, workspace_id, user.id, body),
            "policy_key version raw_days media_days derived_days export_days legal_basis",
        )


@router.get("/retention-policies")
def policies(
    workspace_id: UUID, request: Request, user: Actor, limit: Limit = 25, offset: Offset = 0
):
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "workspace.read")
        return {
            "items": [
                view(
                    row,
                    "policy_key version raw_days media_days derived_days export_days legal_basis",
                )
                for row in session.scalars(
                    select(RetentionPolicy)
                    .where(RetentionPolicy.workspace_id == workspace_id)
                    .order_by(RetentionPolicy.created_at, RetentionPolicy.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]
        }


@router.post("/upload-intents", status_code=201)
def upload_create(workspace_id: UUID, body: UploadBody, request: Request, user: Actor):
    rate_limit(request, "upload_intent", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        asset, intent = privacy.create_upload(
            session, workspace_id, user.id, body, request.app.state.settings
        )
        return {"asset": asset_view(asset), "upload_id": intent.id, "expires_at": intent.expires_at}


def upload_record(session, workspace_id, user_id, upload_id):
    privacy.lock_workspace(session, workspace_id)
    require_workspace(session, user_id, workspace_id, "assets.create")
    intent = privacy.get_scoped(session, UploadIntent, workspace_id, upload_id)
    if intent.uploader_id != user_id:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    asset = privacy.authorized_asset(
        session, workspace_id, user_id, intent.asset_id, owner=True, ready=False
    )
    if intent.expires_at <= utcnow() and intent.completed_at is None:
        raise DomainError("UPLOAD_EXPIRED", "Upload intent has expired.", 409)
    return intent, asset


async def upload_io(function, *args):
    operation = asyncio.create_task(asyncio.to_thread(function, *args))
    try:
        return await asyncio.shield(operation)
    except asyncio.CancelledError:
        try:
            await operation
        except Exception:
            pass
        raise


@router.put("/upload-intents/{upload_id}/content", status_code=204)
async def upload_content(workspace_id: UUID, upload_id: UUID, request: Request, user: Actor):
    storage = PrivateStorage(request.app.state.settings.private_root)
    database = request.app.state.database
    opened = {}

    def begin():
        with database.sessions.begin() as session:
            intent, asset = upload_record(session, workspace_id, user.id, upload_id)
            if asset.state != "pending":
                raise DomainError("UPLOAD_STATE", "Create a new intent for a failed upload.", 409)
            if request.headers.get("content-type", "").split(";")[0] != asset.media_type:
                raise DomainError("INVALID_FILE", "Content type does not match the intent.", 422)
            descriptor = storage.create(asset.storage_key, asset.size_bytes)
            opened.update(descriptor=descriptor, key=asset.storage_key, asset_id=asset.id)
            asset.state = "uploading"
            return descriptor, asset.storage_key, asset.size_bytes

    descriptor = None
    key = None
    try:
        descriptor, key, expected = await upload_io(begin)
        count = 0
        async for chunk in request.stream():
            count += len(chunk)
            if count > expected:
                raise DomainError("PAYLOAD_TOO_LARGE", "Upload exceeds its declared size.", 413)

            def write(data):
                remaining = memoryview(data)
                while remaining:
                    written = os.write(descriptor, remaining)
                    remaining = remaining[written:]

            await upload_io(write, chunk)
        if count != expected:
            raise DomainError("INCOMPLETE_UPLOAD", "Upload length does not match the intent.", 422)
        await upload_io(os.fsync, descriptor)
        os.close(descriptor)
        descriptor = None
        opened["descriptor"] = None

        def finish():
            with database.sessions.begin() as session:
                _, asset = upload_record(session, workspace_id, user.id, upload_id)
                if asset.state != "uploading":
                    raise DomainError("UPLOAD_REVOKED", "Upload is no longer permitted.", 409)
                asset.state = "quarantined"

        await upload_io(finish)
    except BaseException as error:
        descriptor = opened.get("descriptor")
        key = opened.get("key")
        if descriptor is not None:
            os.close(descriptor)
        if key is not None:

            def cleanup():
                from app.common.privacy_models import Asset

                with database.sessions.begin() as session:
                    privacy.lock_workspace(session, workspace_id)
                    asset = session.get(Asset, opened["asset_id"])
                    if asset is not None and asset.state in {"quarantined", "ready"}:
                        return
                    if asset is not None and asset.state in {"pending", "uploading"}:
                        asset.state = "blocked"
                    storage.delete(key)

            await upload_io(cleanup)
        if isinstance(error, OSError):
            raise DomainError(
                "STORAGE_UNAVAILABLE", "Storage is temporarily unavailable.", 507
            ) from None
        raise


@router.post("/upload-intents/{upload_id}/complete")
def upload_complete(workspace_id: UUID, upload_id: UUID, request: Request, user: Actor):
    database = request.app.state.database
    storage = PrivateStorage(request.app.state.settings.private_root)
    with database.sessions.begin() as session:
        intent, asset = upload_record(session, workspace_id, user.id, upload_id)
        if asset.state == "ready" and intent.completed_at:
            return asset_view(asset)
        if asset.state != "quarantined":
            raise DomainError("UPLOAD_STATE", "Upload is not ready for validation.", 409)
        key, size, media_type, checksum = (
            asset.storage_key,
            asset.size_bytes,
            asset.media_type,
            asset.checksum,
        )
    try:
        content = storage.read(key, size)
        if len(content) != size:
            raise ValueError("Invalid size")
        dimensions = validate_content(content, media_type, checksum)
    except (
        ValueError,
        OSError,
        EOFError,
        UnicodeError,
        wave.Error,
        csv.Error,
        zlib.error,
    ):
        with database.sessions.begin() as session:
            _, asset = upload_record(session, workspace_id, user.id, upload_id)
            if asset.state == "quarantined":
                asset.state = "blocked"
        raise DomainError(
            "INVALID_FILE", "File failed format, size or checksum validation.", 422
        ) from None
    with database.sessions.begin() as session:
        intent, asset = upload_record(session, workspace_id, user.id, upload_id)
        if asset.state not in {"quarantined", "ready"}:
            raise DomainError("UPLOAD_REVOKED", "Upload is no longer permitted.", 409)
        for name, value in dimensions.items():
            setattr(asset, name, value)
        asset.state, intent.completed_at = "ready", intent.completed_at or utcnow()
        return asset_view(asset)


@router.get("/assets/{asset_id}")
def asset_metadata(workspace_id: UUID, asset_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        return asset_view(privacy.authorized_asset(session, workspace_id, user.id, asset_id))


@router.get("/assets/{asset_id}/content")
def asset_download(workspace_id: UUID, asset_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        privacy.lock_workspace(session, workspace_id)
        asset = privacy.authorized_asset(session, workspace_id, user.id, asset_id)
        try:
            content = PrivateStorage(request.app.state.settings.private_root).read(
                asset.storage_key, asset.size_bytes
            )
            if (
                len(content) != asset.size_bytes
                or hashlib.sha256(content).hexdigest() != asset.checksum
            ):
                raise ValueError("Asset integrity failure")
        except (OSError, ValueError):
            raise DomainError("ASSET_UNAVAILABLE", "Asset is not available.", 409) from None
        return Response(
            content,
            media_type=asset.media_type,
            headers={
                "Content-Disposition": f'attachment; filename="asset.{asset.extension}"',
                "Content-Security-Policy": "sandbox; default-src 'none'",
            },
        )


@router.post("/assets/{asset_id}/links", status_code=201)
def link_create(workspace_id: UUID, asset_id: UUID, body: LinkBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        privacy.lock_workspace(session, workspace_id)
        asset = privacy.authorized_asset(session, workspace_id, user.id, asset_id, owner=True)
        member = privacy.get_scoped(session, Membership, workspace_id, body.membership_id)
        if member.status != "active":
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        link = session.scalar(
            select(AssetLink).where(
                AssetLink.workspace_id == workspace_id,
                AssetLink.asset_id == asset_id,
                AssetLink.owner_membership_id == member.id,
                AssetLink.purpose == asset.purpose,
            )
        )
        if link is None:
            link = AssetLink(
                workspace_id=workspace_id,
                asset_id=asset_id,
                owner_membership_id=member.id,
                purpose=asset.purpose,
            )
            session.add(link)
        link.revoked_at = None
        session.flush()
        return view(link, "asset_id owner_membership_id purpose revoked_at")


@router.delete("/assets/{asset_id}/links/{link_id}", status_code=204)
def link_revoke(workspace_id: UUID, asset_id: UUID, link_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        workspace = privacy.lock_workspace(session, workspace_id)
        privacy.authorized_asset(session, workspace_id, user.id, asset_id, owner=True)
        link = privacy.get_scoped(session, AssetLink, workspace_id, link_id)
        if link.asset_id != asset_id:
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        link.revoked_at = utcnow()
        workspace.privacy_epoch += 1


@router.post("/privacy-requests", status_code=202)
def privacy_create(workspace_id: UUID, body: PrivacyBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return view(
            privacy.create_request(session, workspace_id, user.id, body),
            "kind state created_at completed_at",
        )


@router.get("/privacy-requests/{request_id}")
def privacy_status(workspace_id: UUID, request_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        record = privacy.get_scoped(session, PrivacyRequest, workspace_id, request_id)
        if record.subject_id != user.id:
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        return view(record, "kind state created_at completed_at")


@router.post("/privacy-requests/{request_id}/retry", status_code=202)
def privacy_retry(workspace_id: UUID, request_id: UUID, request: Request, user: Actor):
    from uuid import uuid4

    from app.jobs.models import Job
    from app.jobs.service import enqueue

    rate_limit(request, "privacy_retry", str(user.id), 10)
    with request.app.state.database.sessions.begin() as session:
        privacy.lock_workspace(session, workspace_id)
        record = privacy.get_scoped(session, PrivacyRequest, workspace_id, request_id)
        if record.subject_id != user.id or record.kind != "erasure":
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        active = session.scalar(
            select(Job.id).where(
                Job.workspace_id == workspace_id,
                Job.target_id == record.id,
                Job.kind == "privacy.erase",
                Job.state.in_(["pending", "running"]),
            )
        )
        if not active and record.state != "completed":
            enqueue(
                session,
                workspace_id=workspace_id,
                requester_id=user.id,
                kind="privacy.erase",
                target_id=record.id,
                command_key=f"privacy-retry-{uuid4()}",
                internal=True,
            )
        return view(record, "kind state created_at completed_at")


@router.get("/privacy-requests/{request_id}/data")
def privacy_data(
    workspace_id: UUID,
    request_id: UUID,
    request: Request,
    user: Actor,
    limit: Limit = 25,
    offset: Offset = 0,
    detail_offset: Offset = 0,
):
    from app.collection.privacy import subject_data
    from app.common.privacy_models import Asset
    from app.evaluation.privacy import subject_data as evaluation_data
    from app.longitudinal.service import subject_data as longitudinal_data
    from app.recruiting.service import access_summary
    from app.reviews.privacy import subject_financial_data

    with request.app.state.database.sessions() as session:
        record = privacy.get_scoped(session, PrivacyRequest, workspace_id, request_id)
        if record.subject_id != user.id or record.kind != "access":
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        privacy.require_unrestricted(session, workspace_id, user.id)
        return {
            "scope": "workspace_privacy_and_assets",
            "collection": subject_data(
                session,
                workspace_id,
                user.id,
                limit=limit,
                offset=offset,
                detail_offset=detail_offset,
            ),
            "recruitment": access_summary(session, workspace_id, user.id),
            "financial": subject_financial_data(
                session, workspace_id, user.id, limit=limit, offset=offset
            ),
            "evaluation": evaluation_data(
                session, workspace_id, user.id, limit=limit, offset=offset
            ),
            "longitudinal": longitudinal_data(
                session, workspace_id, user.id, limit=limit, offset=offset
            ),
            "identity": {"email": user.email, "display_name": user.display_name},
            "offset": offset,
            "limit": limit,
            "assets": [
                asset_view(row)
                for row in session.scalars(
                    select(Asset)
                    .where(Asset.workspace_id == workspace_id, Asset.owner_id == user.id)
                    .order_by(Asset.id)
                    .offset(offset)
                    .limit(limit)
                )
            ],
            "receipts": [
                view(row, "document_id study_version_id decision presented_digest created_at")
                for row in session.scalars(
                    select(ConsentReceipt)
                    .where(
                        ConsentReceipt.workspace_id == workspace_id,
                        ConsentReceipt.subject_id == user.id,
                    )
                    .order_by(ConsentReceipt.id)
                    .offset(offset)
                    .limit(limit)
                )
            ],
        }


@router.post("/assets/retention-sweep")
def retention_sweep(workspace_id: UUID, request: Request, user: Actor):
    return {
        "purged": privacy.sweep_storage(
            request.app.state.database, request.app.state.settings, workspace_id, user.id
        )
    }
