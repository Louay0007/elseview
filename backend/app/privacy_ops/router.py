from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.auth.dependencies import current_user
from app.auth.models import User
from app.auth.security import utcnow
from app.auth.service import audit, require_workspace
from app.common.errors import DomainError
from app.common.privacy import get_scoped, lock_workspace
from app.privacy_ops.models import LegalHold, ReviewedRetention

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/privacy-ops", tags=["privacy-ops"])
Actor = Annotated[User, Depends(current_user)]


class HoldBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    subject_id: UUID
    reason: str = Field(min_length=1, max_length=2000)
    review_deadline: AwareDatetime


class PolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    # Financial minima are administered by the settlement-policy API, not this sweep.
    purpose: Literal["raw", "media", "derived", "export"]
    version: int = Field(ge=1, strict=True)
    days: int = Field(ge=1, le=3650, strict=True)
    reason: str = Field(min_length=1, max_length=2000)
    review_deadline: AwareDatetime


def authorize(session, wid, actor):
    lock_workspace(session, wid)
    require_workspace(session, actor, wid, "privacy.manage")


def future(body):
    if body.review_deadline <= utcnow() or not body.reason.strip():
        raise DomainError(
            "INVALID_REVIEW", "A reason and future review deadline are required.", 422
        )


@router.post("/holds", status_code=201)
def create_hold(workspace_id: UUID, body: HoldBody, request: Request, user: Actor):
    future(body)
    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        from app.auth.models import Membership
        from app.recruiting.models import Candidate

        if not session.scalar(
            select(Membership.id).where(
                Membership.workspace_id == workspace_id, Membership.user_id == body.subject_id
            )
        ) and not session.scalar(
            select(Candidate.id)
            .where(Candidate.workspace_id == workspace_id, Candidate.subject_id == body.subject_id)
            .limit(1)
        ):
            raise DomainError("NOT_FOUND", "Resource not found.", 404)
        row = LegalHold(workspace_id=workspace_id, reviewed_by=user.id, **body.model_dump())
        session.add(row)
        session.flush()
        audit(session, "privacy.hold_created", user.id, workspace_id, row.id)
        return {"id": row.id, "review_deadline": row.review_deadline}


@router.post("/holds/{hold_id}/release")
def release_hold(workspace_id: UUID, hold_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        row = get_scoped(session, LegalHold, workspace_id, hold_id)
        row.released_at = row.released_at or utcnow()
        audit(session, "privacy.hold_released", user.id, workspace_id, row.id)
        return {"id": row.id, "released_at": row.released_at}


@router.get("/holds")
def list_holds(workspace_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "privacy.manage")
        return {
            "items": [
                {
                    "id": x.id,
                    "subject_id": x.subject_id,
                    "reason": x.reason,
                    "review_deadline": x.review_deadline,
                    "review_overdue": x.review_deadline <= utcnow(),
                    "released_at": x.released_at,
                }
                for x in session.scalars(
                    select(LegalHold)
                    .where(LegalHold.workspace_id == workspace_id)
                    .order_by(LegalHold.created_at)
                    .limit(100)
                )
            ]
        }


@router.post("/retention", status_code=201)
def create_policy(workspace_id: UUID, body: PolicyBody, request: Request, user: Actor):
    future(body)
    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        prior = session.scalar(
            select(ReviewedRetention).where(
                ReviewedRetention.workspace_id == workspace_id,
                ReviewedRetention.purpose == body.purpose,
                ReviewedRetention.version == body.version,
            )
        )
        if prior:
            if any(getattr(prior, k) != v for k, v in body.model_dump().items()):
                raise DomainError("IMMUTABLE_POLICY", "This version already exists.", 409)
            return {"id": prior.id}
        row = ReviewedRetention(workspace_id=workspace_id, reviewed_by=user.id, **body.model_dump())
        session.add(row)
        session.flush()
        audit(session, "privacy.retention_reviewed", user.id, workspace_id, row.id)
        return {"id": row.id}


@router.post("/retention/sweep")
def sweep_retention(workspace_id: UUID, request: Request, user: Actor):
    from app.common.private_storage import PrivateStorage
    from app.privacy_ops.lifecycle import sweep_lifecycle
    from app.privacy_ops.service import sweep_producers

    with request.app.state.database.sessions.begin() as session:
        authorize(session, workspace_id, user.id)
        counts = sweep_producers(session, workspace_id)
        counts.update(
            sweep_lifecycle(
                session,
                workspace_id,
                storage=PrivateStorage(request.app.state.settings.private_root),
            )
        )
        audit(session, "privacy.retention_swept", user.id, workspace_id)
        return counts
