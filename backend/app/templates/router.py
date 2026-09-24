from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.auth.service import require_workspace
from app.common.idempotency import execute_idempotent
from app.common.privacy import lock_workspace, require_unrestricted

from . import catalogue, service
from .schemas import InstantiateBody

router = APIRouter(prefix="/api/v1", tags=["templates"])
Actor = Annotated[User, Depends(current_user)]
Idempotency = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]


@router.get("/templates")
def index(user: Actor):
    return {"schema_version": 1, "templates": catalogue.catalogue()}


@router.get("/templates/{template_key}")
def detail(template_key: str, user: Actor, version: Annotated[int, Query(ge=1)] = 1):
    return catalogue.get_recipe(template_key, version)


@router.post("/workspaces/{workspace_id}/templates/{template_key}/instantiate", status_code=201)
def instantiate(
    workspace_id: UUID,
    template_key: str,
    body: InstantiateBody,
    request: Request,
    user: Actor,
    idempotency_key: Idempotency,
):
    rate_limit(request, "template_instantiate", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        require_workspace(session, user.id, workspace_id, "studies.create")
        require_unrestricted(session, workspace_id, user.id)
        _, result = execute_idempotent(
            session,
            workspace_id,
            user.id,
            "template.instantiate",
            idempotency_key,
            {"template_key": template_key, **body.model_dump(mode="json")},
            lambda: (201, service.instantiate(session, workspace_id, user.id, template_key, body)),
        )
        return result
