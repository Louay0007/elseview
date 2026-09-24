from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.auth.security import token_hash
from app.auth.service import require_workspace
from app.common.privacy import get_scoped, lock_workspace
from app.recruiting import service
from app.recruiting.models import (
    ParticipantProfile,
    PrivateContact,
    PrivateContactConsent,
    Qualification,
)
from app.recruiting.schemas import (
    ConfigBody,
    Filters,
    ImportBody,
    InviteBody,
    PanelBody,
    PublicRecruitBody,
    QualificationBody,
    ScreenBody,
)

router = APIRouter(prefix="/api/v1", tags=["recruiting"])
Actor = Annotated[User, Depends(current_user)]
Token = Annotated[str, Header(alias="X-Invitation-Token", min_length=20, max_length=512)]
ROOT = "/workspaces/{workspace_id}/recruiting"


@router.get("/panel/consent")
def panel_document():
    return {"version": "1", "body": service.PANEL_DOCUMENT, "digest": service.PANEL_DIGEST}


@router.put("/panel/profile")
def panel_profile(body: PanelBody, request: Request, user: Actor):
    rate_limit(request, "panel", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        profile = service.panel_update(session, user.id, body)
        return {
            "id": str(profile.id),
            "status": profile.status,
            "attributes": profile.attributes_json,
        }


@router.get("/panel/profile")
def get_profile(request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        profile = session.scalar(
            select(ParticipantProfile).where(ParticipantProfile.user_id == user.id)
        )
        if not profile:
            service.fail()
        return {
            "id": str(profile.id),
            "status": profile.status,
            "attributes": profile.attributes_json,
        }


@router.post(ROOT + "/contacts/import")
def import_contacts(workspace_id: UUID, body: ImportBody, request: Request, user: Actor):
    rate_limit(request, "contact-import", str(user.id), 20)
    with request.app.state.database.sessions.begin() as session:
        return service.import_contacts(
            session, request.app.state.settings, workspace_id, user.id, body
        )


@router.post(ROOT + "/contacts/{contact_id}/suppress")
def suppress(workspace_id: UUID, contact_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        lock_workspace(session, workspace_id)
        require_workspace(session, user.id, workspace_id, "privacy.manage")
        contact = get_scoped(session, PrivateContact, workspace_id, contact_id)
        service.suppress_contact(session, workspace_id, contact_id)
        previous = session.scalar(
            select(PrivateContactConsent)
            .where(PrivateContactConsent.contact_id == contact.id)
            .order_by(PrivateContactConsent.created_at.desc())
            .limit(1)
        )
        session.add(
            PrivateContactConsent(
                workspace_id=workspace_id,
                contact_id=contact.id,
                document_id=previous.document_id,
                decision="withdrawn",
                receipt_key="suppress:" + str(contact.id),
            )
        ) if previous and previous.decision != "withdrawn" else None
        return {"id": str(contact.id), "status": contact.status}


@router.post(ROOT + "/estimate")
def estimate(
    workspace_id: UUID, body: Filters, request: Request, user: Actor, source_kind: str = "private"
):
    rate_limit(request, "recruit-estimate", str(user.id), 20)
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "privacy.manage")
        if source_kind not in ("public", "private"):
            service.fail("INVALID_SOURCE", 422)
        sources = (
            session.scalars(
                select(PrivateContact).where(PrivateContact.workspace_id == workspace_id)
            )
            if source_kind == "private"
            else session.scalars(select(ParticipantProfile))
        )
        count = 0
        from app.common.errors import DomainError

        for source in sources:
            try:
                attrs, _ = service.source_attributes(session, workspace_id, source_kind, source.id)
            except DomainError:
                continue
            count += int(service.matches(attrs, body.model_dump()))
        # Tiny cohorts are suppressed; no source IDs/contact directory disclosure.
        return {
            "count": count if count >= 5 else None,
            "suppressed": count < 5,
            "availability_guaranteed": False,
        }


@router.post(ROOT + "/launches/{launch_id}/config", status_code=201)
def configure(workspace_id: UUID, launch_id: UUID, body: ConfigBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        config = service.configure(session, workspace_id, user.id, launch_id, body)
        return {
            "id": str(config.id),
            "capacity": config.capacity,
            "development_commitments_only": True,
        }


@router.post(ROOT + "/launches/{launch_id}/invitations", status_code=201)
def invite(workspace_id: UUID, launch_id: UUID, body: InviteBody, request: Request, user: Actor):
    rate_limit(request, "recruit-invite", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        invitation, candidate, raw = service.issue_invitation(
            session, workspace_id, user.id, launch_id, body
        )
        return {
            "invitation_id": str(invitation.id),
            "candidate_id": str(candidate.id),
            "invitation_token": raw,
            "expires_at": invitation.expires_at,
            "delivery": "manual",
        }


@router.get("/recruiting/invitation")
def invitation_info(request: Request, invitation_token: Token):
    rate_limit(request, "invitation", token_hash(invitation_token), 30)
    with request.app.state.database.sessions.begin() as session:
        _, candidate, launch, _ = service.resolve_invitation(session, invitation_token)
        config = service.config_for(session, candidate.workspace_id, launch.id)
        return {
            "status": candidate.status,
            "screeners": {
                key: {"prompt": v["prompt"], "options": v["options"]}
                for key, v in config.screener_json.items()
            },
            "screening_policy": config.screening_policy,
            "verified_identity_required": True,
            "development_commitments_only": True,
        }


@router.post("/recruiting/screen")
def screen(body: ScreenBody, request: Request, invitation_token: Token, user: Actor):
    rate_limit(request, "screener", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        service.bind_invitation(session, request.app.state.settings, invitation_token, user.id)
        eligible = service.screen(session, invitation_token, body.answers)
        return {"eligible": eligible, "decision": "eligible" if eligible else "screened_out"}


@router.post("/recruiting/reserve")
def reserve(request: Request, invitation_token: Token, user: Actor):
    rate_limit(request, "reservation", str(user.id), 30)
    with request.app.state.database.sessions.begin() as session:
        _, candidate, _, _ = service.bind_invitation(
            session, request.app.state.settings, invitation_token, user.id
        )
        hold = service.reserve_candidate(session, candidate.id, candidate.workspace_id)
        return {
            "reservation_id": str(hold.id),
            "expires_at": hold.expires_at,
            "state": hold.state,
            "reward_millimes": hold.reward_millimes,
            "development_commitments_only": True,
        }


@router.get("/panel/assessments/{language}")
def language_assessment(language: str, user: Actor):
    questions = service.ASSESSMENTS.get(language)
    if questions is None:
        service.fail()
    return {
        "assessment_version": "development-basic-v1",
        "language": language,
        "questions": [{"prompt": q[0], "options": q[1]} for q in questions],
        "scope": "basic_language_only_not_professional_expertise",
    }


@router.post("/panel/qualifications", status_code=201)
def qualify(body: QualificationBody, request: Request, user: Actor):
    rate_limit(request, "qualification", str(user.id), 10)
    with request.app.state.database.sessions.begin() as session:
        result = service.assess_language(session, user.id, body)
        return {
            "language": result.language,
            "passed": result.passed,
            "expires_at": result.expires_at,
            "scope": "basic_language_only_not_professional_expertise",
        }


@router.get("/panel/qualifications")
def qualifications(request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        results = session.scalars(
            select(Qualification)
            .join(ParticipantProfile, ParticipantProfile.id == Qualification.profile_id)
            .where(ParticipantProfile.user_id == user.id)
        )
        return {
            "items": [
                {
                    "language": q.language,
                    "passed": q.passed,
                    "expires_at": q.expires_at,
                    "assessment_version": q.assessment_version,
                }
                for q in results
            ]
        }


@router.post(ROOT + "/launches/{launch_id}/recruit-public", status_code=201)
def recruit_public(
    workspace_id: UUID, launch_id: UUID, body: PublicRecruitBody, request: Request, user: Actor
):
    rate_limit(request, "recruit-public", str(user.id), 10)
    with request.app.state.database.sessions.begin() as session:
        return service.recruit_public(session, workspace_id, user.id, launch_id, body)
