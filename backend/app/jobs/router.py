from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.dependencies import current_user, rate_limit
from app.jobs import service

USER_DEPENDENCY = Depends(current_user)

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/jobs", tags=["jobs"])


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["system.check"] = "system.check"
    command_key: str = Field(min_length=1, max_length=128)
    payload: dict = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def empty_payload(cls, value):
        if value:
            raise ValueError("system.check accepts only an empty payload")
        return value


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    requester_id: UUID
    kind: str
    state: str
    created_at: datetime
    run_after: datetime
    attempt_count: int
    max_attempts: int
    result: dict | None
    error_code: str | None


@router.post("", response_model=JobView, status_code=202)
def create(workspace_id: UUID, body: JobCreate, request: Request, user=USER_DEPENDENCY):
    rate_limit(request, "job_create", str(user.id), 30)
    with request.app.state.database.sessions() as session, session.begin():
        job = service.enqueue(
            session, workspace_id=workspace_id, requester_id=user.id, **body.model_dump()
        )
        return JobView.model_validate(job)


@router.get("", response_model=list[JobView])
def index(
    workspace_id: UUID,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    user=USER_DEPENDENCY,
):
    with request.app.state.database.sessions() as session:
        return [
            JobView.model_validate(job)
            for job in service.list_jobs(session, workspace_id, user.id, limit)
        ]


@router.get("/{job_id}", response_model=JobView)
def detail(workspace_id: UUID, job_id: UUID, request: Request, user=USER_DEPENDENCY):
    with request.app.state.database.sessions() as session:
        return JobView.model_validate(service.get_job(session, workspace_id, user.id, job_id))


@router.post("/{job_id}/cancel", response_model=JobView)
def cancel(workspace_id: UUID, job_id: UUID, request: Request, user=USER_DEPENDENCY):
    with request.app.state.database.sessions() as session, session.begin():
        job = service.cancel(session, workspace_id=workspace_id, user_id=user.id, job_id=job_id)
        return JobView.model_validate(job)
