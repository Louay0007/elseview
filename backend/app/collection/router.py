from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.collection import service
from app.collection.schemas import AnswerBody, BatchBody, StartBody, SubmitBody

router = APIRouter(prefix="/api/v1/collection", tags=["collection"])
Token = Annotated[str, Header(alias="X-Session-Token", min_length=43, max_length=128)]


def guard(request, response):
    response.headers["Cache-Control"] = "no-store"
    rate_limit(
        request,
        "collection",
        service.digest(
            request.headers.get(
                "X-Session-Token", request.headers.get("Authorization", "anonymous")
            )
        ),
        120,
    )


@router.get("/consent")
def consent(
    request: Request,
    response: Response,
    locale: str,
    invitation_token: Annotated[
        str, Header(alias="X-Invitation-Token", min_length=20, max_length=4096)
    ],
    user: Annotated[User, Depends(current_user)],
):
    from app.common.privacy_models import ConsentDocument
    from app.recruiting.service import bind_invitation

    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        _, _, _, version = bind_invitation(
            session, request.app.state.settings, invitation_token, user.id
        )
        if locale not in version.consent_documents:
            service.fail("INVALID_LOCALE", "Unsupported consent locale.", 422)
        document = session.get(ConsentDocument, UUID(version.consent_documents[locale]))
        return {
            "version_id": str(version.id),
            "document_id": str(document.id),
            "body": document.body,
            "digest": document.digest,
            "locale": locale,
            "purpose": "study",
        }


@router.get("/sessions/{session_id}/assets/{asset_id}")
def asset(session_id: UUID, asset_id: UUID, token: Token, request: Request, response: Response):
    import hashlib

    from sqlalchemy import select

    from app.auth.models import Membership
    from app.auth.security import utcnow
    from app.collection.models import InteractionAttempt
    from app.common.privacy import authorized_asset
    from app.common.private_storage import PrivateStorage
    from app.studies.methods import asset_refs
    from app.studies.models import Study

    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        row = service.authorize(session, session_id, token)
        service.require_active(row, row.version_id)
        version, blocks = service.definition(session, row)
        current = service.current_answers(session, row)
        reachable, _ = service.path(blocks, {k: v[1].payload for k, v in current.items()})
        allowed = False
        # A stimulus reused by another block must not bypass timed-exposure concealment.
        for exposure in blocks:
            if exposure.type == "five_second" and exposure.config.asset_ref.asset_id == asset_id:
                timed = session.scalar(
                    select(InteractionAttempt).where(
                        InteractionAttempt.session_id == row.id,
                        InteractionAttempt.block_key == exposure.block_key,
                    )
                )
                if (
                    not timed
                    or timed.state != "started"
                    or (utcnow() - timed.started_at).total_seconds() > 5
                ):
                    service.fail(
                        "EXPOSURE_ASSET_CONCEALED",
                        "Timed stimulus is not available outside its exposure.",
                        404,
                    )
        for block in blocks:
            if block.block_key not in reachable or asset_id not in {
                ref.asset_id for ref in asset_refs(block)
            }:
                continue
            if block.type == "five_second":
                attempt = session.scalar(
                    select(InteractionAttempt).where(
                        InteractionAttempt.session_id == row.id,
                        InteractionAttempt.block_key == block.block_key,
                    )
                )
                if (
                    not attempt
                    or attempt.state != "started"
                    or (utcnow() - attempt.started_at).total_seconds() > 5
                ):
                    continue
            allowed = True
        if not allowed:
            service.fail("NOT_FOUND", "Asset is not currently available.", 404)
        study = session.get(Study, version.study_id)
        owner = session.get(Membership, study.owner_membership_id)
        item = authorized_asset(session, row.workspace_id, owner.user_id, asset_id)
        try:
            data = PrivateStorage(request.app.state.settings.private_root).read(
                item.storage_key, item.size_bytes
            )
            if len(data) != item.size_bytes or hashlib.sha256(data).hexdigest() != item.checksum:
                raise ValueError("integrity")
        except (ValueError, OSError):
            service.fail("ASSET_UNAVAILABLE", "Asset is unavailable.")
        return Response(
            data,
            media_type=item.media_type,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'none'; sandbox",
            },
        )


@router.post("/sessions", status_code=201)
def start(
    body: StartBody,
    request: Request,
    response: Response,
    user: Annotated[User, Depends(current_user)],
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.start(session, body, user.id, request.app.state.settings)


@router.get("/sessions/{session_id}")
def resume(session_id: UUID, token: Token, request: Request, response: Response):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.resume(session, service.authorize(session, session_id, token))


@router.put("/sessions/{session_id}/answers/{block_key}")
def answer(
    session_id: UUID,
    block_key: str,
    body: AnswerBody,
    token: Token,
    request: Request,
    response: Response,
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.save_answer(
            session, service.authorize(session, session_id, token), block_key, body
        )


@router.post("/sessions/{session_id}/events")
def events(session_id: UUID, body: BatchBody, token: Token, request: Request, response: Response):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.batch_events(session, service.authorize(session, session_id, token), body)


@router.post("/sessions/{session_id}/attempts/{block_key}")
def attempt(session_id: UUID, block_key: str, token: Token, request: Request, response: Response):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.start_attempt(
            session, service.authorize(session, session_id, token), block_key
        )


@router.post("/sessions/{session_id}/submit")
def submit(session_id: UUID, body: SubmitBody, token: Token, request: Request, response: Response):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.submit(session, service.authorize(session, session_id, token), body)


@router.post("/sessions/{session_id}/withdraw")
def withdraw(session_id: UUID, token: Token, request: Request, response: Response):
    from app.collection.privacy import withdraw_session

    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        row = service.authorize(session, session_id, token, allow_withdrawn=True)
        withdraw_session(session, row)
        return {"withdrawn": True}
