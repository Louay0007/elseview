"""Explicit success projections; private keys have exactly one authority-only route."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.auth.service import audit
from app.recruiting import assessment_privacy as privacy
from app.recruiting import assessments as service
from app.recruiting.assessment_schemas import (
    AppealBody,
    ApprovalBody,
    AttemptOut,
    CatalogueOut,
    ConsentBody,
    ConsentDocumentOut,
    ConsentGrantsOut,
    ConsentOut,
    DecisionBody,
    HistoryOut,
    Language,
    PrivateMaterialOut,
    QueueOut,
    RetireBody,
    StartBody,
    SubmitBody,
    SweepOut,
    VersionBody,
    VersionDetailOut,
    VersionOut,
)
from app.recruiting.models import LanguageAssessmentVersion as Version

router = APIRouter(tags=["language-assessments"])
Actor = Annotated[User, Depends(current_user)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0, le=100000)]
ROOT = "/workspaces/{workspace_id}/language-assessments"
ATTEMPTS = "/panel/language-assessment-attempts"


@router.get("/panel/language-assessment-consent", response_model=ConsentDocumentOut)
def document():
    return dict(version="1", body=service.CONSENT_DOCUMENT, digest=service.CONSENT_DIGEST)


@router.put("/panel/language-assessment-consent", response_model=ConsentOut)
def consent(body: ConsentBody, request: Request, user: Actor):
    rate_limit(request, "language-consent", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        return service.consent_output(service.consent_update(session, user.id, body))


@router.get("/panel/language-assessment-consents", response_model=ConsentGrantsOut)
def consent_grants(request: Request, user: Actor, offset: Offset = 0, limit: Limit = 50):
    with request.app.state.database.sessions.begin() as session:
        return service.consent_grants(session, user.id, offset, limit)


@router.get("/panel/language-assessments", response_model=CatalogueOut)
def catalogue(request: Request, user: Actor, offset: Offset = 0, limit: Limit = 50):
    if not request.app.state.settings.language_assessment_authority_workspace_id:
        return dict(items=[], languages=service.LANGUAGES, next_offset=None)
    with request.app.state.database.sessions() as session:
        rows = list(
            session.scalars(
                select(Version)
                .where(Version.state == "approved")
                .order_by(Version.created_at, Version.id)
                .offset(offset)
                .limit(limit + 1)
            )
        )
        return dict(
            items=[service.version_output(v) for v in rows[:limit]],
            languages=service.LANGUAGES,
            next_offset=offset + limit if len(rows) > limit else None,
        )


@router.post(ATTEMPTS, response_model=AttemptOut, status_code=201)
def start(body: StartBody, request: Request, user: Actor):
    rate_limit(request, "language-start", str(user.id), 20)
    with request.app.state.database.sessions.begin() as session:
        return service.attempt_output(
            session, service.start(session, request.app.state.settings, user.id, body)
        )


@router.get(ATTEMPTS + "/{attempt_id}", response_model=AttemptOut)
def detail(attempt_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return service.attempt_output(session, service.owned_attempt(session, user.id, attempt_id))


@router.post(ATTEMPTS + "/{attempt_id}/submit", response_model=AttemptOut)
def submit(attempt_id: UUID, body: SubmitBody, request: Request, user: Actor):
    rate_limit(request, "language-submit", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        return service.attempt_output(session, service.submit(session, user.id, attempt_id, body))


@router.post(ATTEMPTS + "/{attempt_id}/appeal", response_model=AttemptOut)
def appeal(attempt_id: UUID, body: AppealBody, request: Request, user: Actor):
    rate_limit(request, "language-appeal", str(user.id), 10)
    with request.app.state.database.sessions.begin() as session:
        return service.attempt_output(session, service.appeal(session, user.id, attempt_id, body))


@router.get("/panel/language-qualifications", response_model=HistoryOut)
def history(request: Request, user: Actor, offset: Offset = 0, limit: Limit = 50):
    with request.app.state.database.sessions.begin() as session:
        return service.history(session, user.id, offset, limit)


@router.post(ROOT + "/versions", response_model=VersionDetailOut, status_code=201)
def create(workspace_id: UUID, body: VersionBody, request: Request, user: Actor):
    rate_limit(request, "language-author", str(user.id), 20)
    with request.app.state.database.sessions.begin() as session:
        return service.version_output(
            service.create_version(
                session, request.app.state.settings, workspace_id, user.id, body
            ),
            detail=True,
        )


@router.get(ROOT + "/versions/{version_id}", response_model=VersionDetailOut)
def version_detail(workspace_id: UUID, version_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        version = service.version_for(session, version_id)
        service.authority(
            session,
            request.app.state.settings,
            workspace_id,
            user.id,
            version.language,
            author=version.language
            not in request.app.state.settings.language_assessment_reviewers.get(user.id, []),
        )
        return service.version_output(version, detail=True)


@router.get(ROOT + "/versions/{version_id}/private-material", response_model=PrivateMaterialOut)
def material(workspace_id: UUID, version_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        version = service.version_for(session, version_id)
        service.authority(
            session, request.app.state.settings, workspace_id, user.id, version.language
        )
        return dict(version_id=version.id, material=service.checked_material(session, version))


@router.post(ROOT + "/versions/{version_id}/approve", response_model=VersionOut)
def approve(
    workspace_id: UUID, version_id: UUID, body: ApprovalBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        return service.version_output(
            service.approve_version(
                session, request.app.state.settings, workspace_id, user.id, version_id, body
            )
        )


@router.post(ROOT + "/versions/{version_id}/retire", response_model=VersionOut)
def retire(workspace_id: UUID, version_id: UUID, body: RetireBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return service.version_output(
            service.retire_version(
                session, request.app.state.settings, workspace_id, user.id, version_id, body
            )
        )


@router.get(ROOT + "/queue", response_model=QueueOut)
def queue(
    workspace_id: UUID,
    language: Language,
    request: Request,
    user: Actor,
    offset: Offset = 0,
    limit: Limit = 50,
):
    with request.app.state.database.sessions.begin() as session:
        return service.queue(
            session, request.app.state.settings, workspace_id, user.id, language, offset, limit
        )


@router.get(ROOT + "/attempts/{attempt_id}", response_model=AttemptOut)
def review_detail(workspace_id: UUID, attempt_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return service.attempt_output(
            session,
            service.review_attempt(
                session, request.app.state.settings, workspace_id, user.id, attempt_id
            ),
        )


@router.post(ROOT + "/attempts/{attempt_id}/decisions", response_model=AttemptOut)
def decide(workspace_id: UUID, attempt_id: UUID, body: DecisionBody, request: Request, user: Actor):
    rate_limit(request, "language-decide", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        return service.attempt_output(
            session,
            service.adjudicate(
                session, request.app.state.settings, workspace_id, user.id, attempt_id, body
            ),
        )


@router.post(ROOT + "/retention-sweep", response_model=SweepOut)
def sweep(
    workspace_id: UUID, language: Language, request: Request, user: Actor, limit: Limit = 100
):
    with request.app.state.database.sessions.begin() as session:
        service.authority(session, request.app.state.settings, workspace_id, user.id, language)
        purged = privacy.sweep(session, language=language, limit=limit)
        audit(
            session,
            "language.retention_swept",
            actor_id=user.id,
            workspace_id=workspace_id,
            language=language,
            purged=purged,
        )
        return dict(purged=purged)
