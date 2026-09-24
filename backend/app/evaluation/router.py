from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.auth.service import require_workspace
from app.evaluation import service
from app.evaluation.models import EvaluationAssignment as Assignment
from app.evaluation.models import EvaluationItem as Item
from app.evaluation.schemas import AssignmentBody, DatasetBody, ExportReviewBody, OutcomeBody


def guard(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    rate_limit(request, "evaluation", request.client.host if request.client else "unknown", 120)


router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/evaluation",
    tags=["evaluation"],
    dependencies=[Depends(guard)],
)
Actor = Annotated[User, Depends(current_user)]


@router.post("/datasets", status_code=201)
def create_dataset(workspace_id: UUID, body: DatasetBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        row = service.create_dataset(session, workspace_id, user.id, body)
        return {
            "id": str(row.id),
            "version": row.version,
            "items": [
                {"id": str(i.id), "key": i.key}
                for i in session.scalars(
                    select(Item).where(Item.dataset_id == row.id).order_by(Item.key)
                )
            ],
        }


@router.get("/datasets/{dataset_id}")
def dataset(workspace_id: UUID, dataset_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        row = service.dataset_for(session, workspace_id, user.id, dataset_id, "raw")
        return service.snapshot(session, row)


@router.post("/datasets/{dataset_id}/assignments", status_code=201)
def assign(
    workspace_id: UUID, dataset_id: UUID, body: AssignmentBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        row = service.assign(session, workspace_id, user.id, dataset_id, body)
        return {"id": str(row.id), "kind": row.kind, "item_id": str(row.item_id)}


@router.get("/assignments")
def assignments(
    workspace_id: UUID,
    request: Request,
    user: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    with request.app.state.database.sessions.begin() as session:
        require_workspace(session, user.id, workspace_id, "workspace.read")
        result = []
        rows = session.scalars(
            select(Assignment)
            .where(Assignment.workspace_id == workspace_id, Assignment.reviewer_id == user.id)
            .order_by(Assignment.created_at, Assignment.id)
            .offset(offset)
            .limit(limit)
        ).all()
        from app.common.errors import DomainError

        for row in rows:
            try:
                a, i, ds = service.assignment_context(session, workspace_id, user.id, row.id)
            except DomainError:
                continue
            result.append(
                {
                    "id": str(a.id),
                    "dataset_id": str(ds.id),
                    "item_id": str(i.id),
                    "kind": a.kind,
                    "task": ds.schema["task"],
                    "submitted": service.outcome_for(session, a) is not None,
                }
            )
        return {"items": result, "offset": offset, "limit": limit}


@router.get("/assignments/{assignment_id}")
def assignment(workspace_id: UUID, assignment_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        a, i, ds = service.assignment_context(session, workspace_id, user.id, assignment_id)
        return service.projection(session, a, i, ds)


@router.post("/assignments/{assignment_id}/outcome", status_code=201)
def outcome(
    workspace_id: UUID, assignment_id: UUID, body: OutcomeBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        row = service.submit(session, workspace_id, user.id, assignment_id, body)
        return {"id": str(row.id), "body": row.body}


@router.get("/datasets/{dataset_id}/report")
def report(workspace_id: UUID, dataset_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        row = service.dataset_for(session, workspace_id, user.id, dataset_id, "raw")
        return service.report(session, row)


@router.post("/datasets/{dataset_id}/export-review", status_code=201)
def review_export(
    workspace_id: UUID, dataset_id: UUID, body: ExportReviewBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        row = service.review_export(session, workspace_id, user.id, dataset_id, body)
        return {"id": str(row.id), "snapshot_digest": row.snapshot_digest}


@router.get("/datasets/{dataset_id}/export")
def export(workspace_id: UUID, dataset_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return service.export(session, workspace_id, user.id, dataset_id)


@router.get("/assignments/{assignment_id}/image")
def image(workspace_id: UUID, assignment_id: UUID, request: Request, user: Actor):
    import hashlib

    from app.common.private_storage import PrivateStorage

    with request.app.state.database.sessions.begin() as session:
        a, i, ds = service.assignment_context(session, workspace_id, user.id, assignment_id)
        asset = service.live_source(session, ds, i)
        if asset is None:
            service.fail("No image.", 404)
        try:
            data = PrivateStorage(request.app.state.settings.private_root).read(
                asset.storage_key, asset.size_bytes
            )
            if len(data) != asset.size_bytes or hashlib.sha256(data).hexdigest() != asset.checksum:
                raise ValueError("Integrity failure")
        except (ValueError, OSError):
            service.fail("Asset unavailable.", 409)
        return Response(
            data,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
            },
        )
