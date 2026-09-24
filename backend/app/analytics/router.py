from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User

from . import service

router = APIRouter(prefix="/api/v1", tags=["analytics"])
Actor = Annotated[User, Depends(current_user)]
BASE = "/workspaces/{workspace_id}/analytics"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotBody(Strict):
    study_id: UUID
    version_id: UUID


class ReportBody(Strict):
    snapshot_id: UUID


class RevisionBody(Strict):
    expected_revision: int = Field(ge=1)


class ReviseBody(RevisionBody):
    snapshot_id: UUID


class ShareBody(Strict):
    ttl_seconds: int = Field(default=86400, ge=60, le=2592000)


class ExportBody(Strict):
    format: Literal["json", "csv"]
    scope: Literal["summary", "raw"] = "summary"


def guard(request, response, actor):
    response.headers["Cache-Control"] = "no-store"
    rate_limit(request, "analytics", str(actor.id), 60)


@router.post(BASE + "/snapshots", status_code=201)
def snapshot_create(
    workspace_id: UUID, body: SnapshotBody, request: Request, response: Response, user: Actor
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        snapshot = service.freeze(session, workspace_id, user.id, body.study_id, body.version_id)
        return service.snapshot_view(session, workspace_id, user.id, snapshot.id)


@router.get(BASE + "/snapshots/{snapshot_id}")
def snapshot_get(
    workspace_id: UUID, snapshot_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.snapshot_view(session, workspace_id, user.id, snapshot_id)


@router.get(BASE + "/snapshots/{snapshot_id}/sources")
def sources_get(
    workspace_id: UUID, snapshot_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.source_access_summary(session, workspace_id, user.id, snapshot_id)


@router.get(BASE + "/comparisons")
def compare(
    workspace_id: UUID,
    left_id: UUID,
    right_id: UUID,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.compare(session, workspace_id, user.id, left_id, right_id)


@router.post(BASE + "/reports", status_code=201)
def report_create(
    workspace_id: UUID, body: ReportBody, request: Request, response: Response, user: Actor
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.create_report(session, workspace_id, user.id, body.snapshot_id)


@router.get(BASE + "/reports/{report_id}")
def report_get(
    workspace_id: UUID,
    report_id: UUID,
    request: Request,
    response: Response,
    user: Actor,
    revision: int | None = Query(default=None, ge=1),
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.report_view(session, workspace_id, user.id, report_id, revision)


@router.post(BASE + "/reports/{report_id}/approve")
def report_approve(
    workspace_id: UUID,
    report_id: UUID,
    body: RevisionBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.approve(session, workspace_id, user.id, report_id, body.expected_revision)


@router.post(BASE + "/reports/{report_id}/revise", status_code=201)
def report_revise(
    workspace_id: UUID,
    report_id: UUID,
    body: ReviseBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.revise(
            session, workspace_id, user.id, report_id, body.snapshot_id, body.expected_revision
        )


@router.post(BASE + "/reports/{report_id}/exports", status_code=201)
def export_create(
    workspace_id: UUID,
    report_id: UUID,
    body: ExportBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.create_export(
            session, workspace_id, user.id, report_id, body.format, body.scope
        )


@router.get(BASE + "/exports/{export_id}")
def export_download(
    workspace_id: UUID, export_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        content, media_type = service.download_export(session, workspace_id, user.id, export_id)
        return Response(
            content,
            media_type=media_type,
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'attachment; filename="report.'
                + ("csv" if media_type == "text/csv" else "json")
                + '"',
                "X-Content-Type-Options": "nosniff",
            },
        )


@router.post(BASE + "/reports/{report_id}/shares", status_code=201)
def share_create(
    workspace_id: UUID,
    report_id: UUID,
    body: ShareBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.create_share(session, workspace_id, user.id, report_id, body.ttl_seconds)


@router.delete(BASE + "/shares/{share_id}")
def share_revoke(
    workspace_id: UUID, share_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response, user)
    with request.app.state.database.sessions.begin() as session:
        return service.revoke_share(session, workspace_id, user.id, share_id)


@router.get("/report-shares/{token}")
def share_get(token: str, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    rate_limit(request, "report_share", request.client.host if request.client else "unknown", 30)
    with request.app.state.database.sessions.begin() as session:
        return service.read_share(session, token)
