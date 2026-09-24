"""Optional processing decisions are actor- and study-version-bound, never implied."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.auth.security import utcnow
from app.collection.models import CollectionSession
from app.common.errors import DomainError
from app.common.privacy import get_scoped, lock_workspace, require_unrestricted
from app.common.privacy_models import ConsentDocument, ConsentReceipt
from app.common.privacy_schemas import Digest, RequestKey, StrictBody
from app.studies.models import Study, StudyVersion

router = APIRouter(prefix="/api/v1/collection/sessions", tags=["participant-consent"])
Actor = Annotated[User, Depends(current_user)]
Purpose = Literal["ai_processing", "accessibility_context", "recording"]


class OptionalConsent(StrictBody):
    purpose: Purpose
    document_id: UUID
    presented_digest: Digest
    decision: Literal["granted", "declined", "withdrawn"]
    receipt_key: RequestKey


def own_session(session, session_id, user_id):
    hint = session.get(CollectionSession, session_id)
    if hint is None or hint.subject_id != user_id:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    lock_workspace(session, hint.workspace_id)
    session.refresh(hint)
    if hint.state == "erased":
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    return hint


@router.get("/{session_id}/optional-consent")
def documents(session_id: UUID, purpose: Purpose, request: Request, user: Actor):
    rate_limit(request, "optional_consent", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        row = own_session(session, session_id, user.id)
        docs = session.scalars(
            select(ConsentDocument)
            .where(
                ConsentDocument.workspace_id == row.workspace_id,
                ConsentDocument.purpose == purpose,
                ConsentDocument.locale == row.locale,
            )
            .order_by(ConsentDocument.created_at.desc(), ConsentDocument.id)
            .limit(25)
        ).all()
        return {
            "optional": True,
            "purpose": purpose,
            "study_version_id": str(row.version_id),
            "documents": [
                {
                    "id": str(doc.id),
                    "body": doc.body,
                    "digest": doc.digest,
                    "version": doc.version,
                    "locale": doc.locale,
                }
                for doc in docs
            ],
        }


@router.post("/{session_id}/optional-consent")
def record(session_id: UUID, body: OptionalConsent, request: Request, user: Actor):
    rate_limit(request, "optional_consent", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        row = own_session(session, session_id, user.id)
        doc = get_scoped(session, ConsentDocument, row.workspace_id, body.document_id)
        if (
            doc.purpose != body.purpose
            or doc.locale != row.locale
            or doc.digest != body.presented_digest
        ):
            raise DomainError("CONSENT_MISMATCH", "Displayed document does not match.", 409)
        prior = session.scalar(
            select(ConsentReceipt).where(
                ConsentReceipt.workspace_id == row.workspace_id,
                ConsentReceipt.subject_id == user.id,
                ConsentReceipt.receipt_key == body.receipt_key,
            )
        )
        if prior:
            if (
                prior.document_id,
                prior.study_version_id,
                prior.decision,
                prior.presented_digest,
            ) != (doc.id, row.version_id, body.decision, body.presented_digest):
                raise DomainError("IDEMPOTENCY_CONFLICT", "Consent receipt key already used.", 409)
            return {"id": str(prior.id), "decision": prior.decision, "optional": True}
        if body.decision == "granted":
            require_unrestricted(session, row.workspace_id, user.id)
            if row.state not in {"active", "submitted"}:
                raise DomainError("CONSENT_UNAVAILABLE", "Participation is withdrawn.", 403)
            version = get_scoped(session, StudyVersion, row.workspace_id, row.version_id)
            study = get_scoped(session, Study, row.workspace_id, version.study_id)
            if body.purpose == "ai_processing" and study.ai_policy == "human_only":
                raise DomainError("AI_DISABLED", "This study permits human-only processing.", 403)
        receipt = ConsentReceipt(
            workspace_id=row.workspace_id,
            subject_id=user.id,
            document_id=doc.id,
            study_version_id=row.version_id,
            receipt_key=body.receipt_key,
            decision=body.decision,
            presented_digest=body.presented_digest,
            created_at=utcnow(),
        )
        session.add(receipt)
        if body.decision != "granted":
            from app.privacy_ops.events import record_event

            # Snapshot replay must preserve this optional-purpose withdrawal,
            # not turn it into withdrawal from unrelated study participation.
            previous_grants = session.scalars(
                select(ConsentReceipt)
                .join(ConsentDocument, ConsentDocument.id == ConsentReceipt.document_id)
                .where(
                    ConsentReceipt.workspace_id == row.workspace_id,
                    ConsentReceipt.subject_id == user.id,
                    ConsentReceipt.study_version_id == row.version_id,
                    ConsentReceipt.decision == "granted",
                    ConsentDocument.purpose == body.purpose,
                )
            ).all()
            for grant in previous_grants:
                record_event(session, row.workspace_id, "consent_revoke", grant.id)
            from app.ai.service import invalidate_sessions

            invalidate_sessions(session, row.workspace_id, [row.id])
            if body.purpose == "recording":
                from app.longitudinal.service import recording_revoke

                recording_revoke(session, row.workspace_id, user.id, row.version_id)
        session.flush()
        return {"id": str(receipt.id), "decision": receipt.decision, "optional": True}
