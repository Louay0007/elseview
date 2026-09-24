from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.common.privacy import get_scoped, lock_workspace
from app.jobs import service as jobs
from app.studies.service import authorize

from . import service
from .models import AIRun
from .schemas import ReconcileBody, RunBody

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/ai", tags=["ai"])
Actor = Annotated[User, Depends(current_user)]


def guard(request, response, user):
    response.headers["Cache-Control"] = "no-store"
    rate_limit(request, "ai", str(user.id), 30)


@router.post("/runs", status_code=202)
def create(workspace_id: UUID, body: RunBody, request: Request, response: Response, user: Actor):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.create(session, request.app.state.settings, workspace_id, user.id, body)


@router.get("/runs/{run_id}")
def get(workspace_id: UUID, run_id: UUID, request: Request, response: Response, user: Actor):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.view(session, workspace_id, user.id, run_id)


@router.post("/runs/{run_id}/approve")
def approve(workspace_id: UUID, run_id: UUID, request: Request, response: Response, user: Actor):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        run = get_scoped(session, AIRun, workspace_id, run_id)
        authorize(session, workspace_id, user.id, run.study_id, "edit")
        service.context(session, run)
        if run.state != "draft":
            service.denied("AI_APPROVAL_STATE")
        run.state, run.approved_at = "approved", jobs.now(session)
        return service.view(session, workspace_id, user.id, run_id)


@router.post("/runs/{run_id}/reconcile")
def reconcile(
    workspace_id: UUID,
    run_id: UUID,
    body: ReconcileBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.reconcile(session, workspace_id, user.id, run_id, body)
