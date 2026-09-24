from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.recruiting import history
from app.recruiting.history_schemas import (
    AttendanceHistory,
    HistoryPage,
    HistoryWorkspace,
    PaymentHistory,
    ResponseHistory,
    RewardHistory,
)

router = APIRouter(prefix="/participant/history", tags=["participant history"])
Actor = Annotated[User, Depends(current_user)]
Offset = Annotated[int, Query(ge=0, le=100_000)]
Limit = Annotated[int, Query(ge=1, le=50)]


def throttle(request, user):
    rate_limit(request, "participant-history", str(user.id), 60)


@router.get("", response_model=HistoryPage[HistoryWorkspace])
def workspaces(request: Request, user: Actor, offset: Offset = 0, limit: Limit = 25):
    throttle(request, user)
    with request.app.state.database.sessions() as session:
        return history.workspaces(session, user.id, offset, limit)


@router.get("/{workspace_id}/responses", response_model=HistoryPage[ResponseHistory])
def responses(
    workspace_id: UUID, request: Request, user: Actor, offset: Offset = 0, limit: Limit = 25
):
    throttle(request, user)
    with request.app.state.database.sessions.begin() as session:
        return history.responses(session, workspace_id, user.id, offset, limit)


@router.get("/{workspace_id}/rewards", response_model=HistoryPage[RewardHistory])
def rewards(
    workspace_id: UUID, request: Request, user: Actor, offset: Offset = 0, limit: Limit = 25
):
    throttle(request, user)
    with request.app.state.database.sessions.begin() as session:
        return history.rewards(session, workspace_id, user.id, offset, limit)


@router.get(
    "/{workspace_id}/rewards/{reward_id}/payments", response_model=HistoryPage[PaymentHistory]
)
def payments(
    workspace_id: UUID,
    reward_id: UUID,
    request: Request,
    user: Actor,
    offset: Offset = 0,
    limit: Limit = 25,
):
    throttle(request, user)
    with request.app.state.database.sessions.begin() as session:
        return history.payments(session, workspace_id, user.id, reward_id, offset, limit)


@router.get("/{workspace_id}/attendance", response_model=HistoryPage[AttendanceHistory])
def attendance(
    workspace_id: UUID, request: Request, user: Actor, offset: Offset = 0, limit: Limit = 25
):
    throttle(request, user)
    with request.app.state.database.sessions.begin() as session:
        return history.attendance(session, workspace_id, user.id, offset, limit)
