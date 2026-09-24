"""Admin-only, workspace-scoped unlinked contact lifecycle."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.auth.dependencies import current_user
from app.auth.models import User
from app.auth.security import utcnow
from app.auth.service import audit
from app.common.errors import DomainError
from app.common.privacy import get_scoped
from app.privacy_ops.lifecycle import erase_contact
from app.privacy_ops.lifecycle_models import ContactHold
from app.privacy_ops.router import authorize
from app.recruiting.models import PrivateContact

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/privacy-ops", tags=["privacy-ops"])
Actor = Annotated[User, Depends(current_user)]


class ContactHoldBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contact_id: UUID
    reason_code: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    review_deadline: AwareDatetime


@router.post("/contact-holds", status_code=201)
def create_contact_hold(workspace_id: UUID, body: ContactHoldBody, request: Request, user: Actor):
    if body.review_deadline <= utcnow():
        raise DomainError("INVALID_REVIEW", "Future review deadline required.", 422)
    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        get_scoped(session, PrivateContact, workspace_id, body.contact_id)
        row = ContactHold(workspace_id=workspace_id, reviewed_by=user.id, **body.model_dump())
        session.add(row)
        session.flush()
        audit(session, "privacy.contact_hold_created", user.id, workspace_id, row.id)
        return {"id": row.id, "contact_id": row.contact_id, "review_deadline": row.review_deadline}


@router.post("/contact-holds/{hold_id}/release")
def release_contact_hold(workspace_id: UUID, hold_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        row = get_scoped(session, ContactHold, workspace_id, hold_id)
        row.released_at = row.released_at or utcnow()
        audit(session, "privacy.contact_hold_released", user.id, workspace_id, row.id)
        return {"id": row.id, "released_at": row.released_at}


@router.post("/contacts/{contact_id}/erase")
def erase_private_contact(workspace_id: UUID, contact_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        erase_contact(session, workspace_id, contact_id)
        audit(session, "privacy.contact_erased", user.id, workspace_id, contact_id)
        return {"contact_id": contact_id, "scope": "private_recruitment", "status": "erased"}
