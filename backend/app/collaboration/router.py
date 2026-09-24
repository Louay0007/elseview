from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.analytics import service as reports
from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.auth.security import utcnow
from app.common.privacy import lock_workspace
from app.jobs.models import Job
from app.jobs.service import enqueue
from app.studies.service import authorize
from app.templates import catalogue
from app.templates.models import TemplateInstance

from . import service, webhooks
from .models import (
    APIKey,
    Integration,
    NotificationPreference,
    ReportComment,
    ReportGrant,
    TemplateGrant,
    WebhookDelivery,
)

router = APIRouter(prefix="/api/v1", tags=["collaboration"])
Actor = Annotated[User, Depends(current_user)]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KeyBody(Body):
    scopes: list[str] = Field(min_length=1, max_length=2)
    days: int = Field(default=30, ge=1, le=90)


class CommentBody(Body):
    text: str = Field(min_length=1, max_length=4000)


class GrantBody(Body):
    recipient_id: UUID


class PreferenceBody(Body):
    reminders: bool


class IntegrationBody(Body):
    destination: str = Field(max_length=2048)


class DeliveryBody(Body):
    command_key: UUID


@router.post("/workspaces/{wid}/collaboration/api-keys", status_code=201)
def issue(wid: UUID, body: KeyBody, request: Request, user: Actor):
    rate_limit(request, "collaboration_key_issue", str(user.id), 10)
    with request.app.state.database.sessions.begin() as s:
        return service.issue_key(s, wid, user.id, body.scopes, body.days)


@router.delete("/workspaces/{wid}/collaboration/api-keys/{kid}", status_code=204)
def revoke(wid: UUID, kid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id)
        key = s.get(APIKey, kid)
        if not key or key.workspace_id != wid or key.user_id != user.id:
            service.deny()
        key.revoked_at = utcnow()


@router.post("/workspaces/{wid}/collaboration/reports/{rid}/comments", status_code=201)
def comment(wid: UUID, rid: UUID, body: CommentBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id)
        reports.report_access(s, wid, user.id, rid, "raw")
        row = ReportComment(workspace_id=wid, report_id=rid, author_id=user.id, text=body.text)
        s.add(row)
        s.flush()
        return {"id": str(row.id), "classification": "raw"}


@router.get("/workspaces/{wid}/collaboration/reports/{rid}/comments")
def comments(wid: UUID, rid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id)
        reports.report_access(s, wid, user.id, rid, "raw")
        return [
            {"id": str(c.id), "text": c.text, "classification": "raw"}
            for c in s.scalars(
                select(ReportComment)
                .where(
                    ReportComment.workspace_id == wid,
                    ReportComment.report_id == rid,
                    ReportComment.restricted.is_(False),
                )
                .limit(100)
            )
        ]


@router.post("/workspaces/{wid}/collaboration/reports/{rid}/grants", status_code=201)
def report_grant(wid: UUID, rid: UUID, body: GrantBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id)
        service.member(s, wid, body.recipient_id)
        _, rv, _, _ = reports.report_access(s, wid, user.id, rid, "publish")
        if rv.state != "approved":
            service.deny()
        row = s.scalar(
            select(ReportGrant).where(
                ReportGrant.report_id == rid, ReportGrant.recipient_id == body.recipient_id
            )
        )
        if row is None:
            row = ReportGrant(
                workspace_id=wid,
                report_id=rid,
                recipient_id=body.recipient_id,
                issuer_id=user.id,
                revision=rv.number,
            )
            s.add(row)
        else:
            row.revoked = False
            row.revision = rv.number
            row.issuer_id = user.id
        s.flush()
        return {"id": str(row.id)}


def granted_report(s, wid, uid, rid):
    service.member(s, wid, uid)
    grant = s.scalar(
        select(ReportGrant).where(
            ReportGrant.workspace_id == wid,
            ReportGrant.report_id == rid,
            ReportGrant.recipient_id == uid,
            ReportGrant.revoked.is_(False),
        )
    )
    if not grant:
        service.deny()
    service.member(s, wid, grant.issuer_id)
    _, rv, snapshot, _ = reports.report_access(s, wid, grant.issuer_id, rid, "publish")
    if rv.number != grant.revision or rv.state != "approved":
        service.deny()
    if reports.release_suppressed(s, snapshot):
        return {"status": "approved", "suppressed": True}
    return reports.safe_summary(snapshot)


@router.get("/workspaces/{wid}/collaboration/reports/{rid}/granted")
def read_grant(wid: UUID, rid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return granted_report(s, wid, user.id, rid)


@router.get("/workspaces/{wid}/collaboration/api/reports/{rid}")
def api_report(wid: UUID, rid: UUID, request: Request, x_api_key: Annotated[str, Header()]):
    with request.app.state.database.sessions.begin() as s:
        return granted_report(s, wid, service.key_actor(s, wid, x_api_key, "reports:read"), rid)


@router.post("/workspaces/{wid}/collaboration/templates/{iid}/grants", status_code=201)
def template_grant(wid: UUID, iid: UUID, body: GrantBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id)
        service.member(s, wid, body.recipient_id)
        t = s.get(TemplateInstance, iid)
        if not t or t.workspace_id != wid:
            service.deny()
        authorize(s, wid, user.id, t.study_id, "edit")
        row = s.scalar(
            select(TemplateGrant).where(
                TemplateGrant.instance_id == iid, TemplateGrant.recipient_id == body.recipient_id
            )
        )
        if row is None:
            row = TemplateGrant(
                workspace_id=wid, instance_id=iid, issuer_id=user.id, recipient_id=body.recipient_id
            )
            s.add(row)
        else:
            row.revoked = False
            row.issuer_id = user.id
        s.flush()
        return {"id": str(row.id)}


def shared_template(s, wid, uid, iid):
    service.member(s, wid, uid)
    g = s.scalar(
        select(TemplateGrant).where(
            TemplateGrant.workspace_id == wid,
            TemplateGrant.instance_id == iid,
            TemplateGrant.recipient_id == uid,
            TemplateGrant.revoked.is_(False),
        )
    )
    if not g:
        service.deny()
    service.member(s, wid, g.issuer_id)
    t = s.get(TemplateInstance, iid)
    if not t or t.workspace_id != wid:
        service.deny()
    authorize(s, wid, g.issuer_id, t.study_id, "edit")
    # Share only versioned public recipe, never customized inputs/origin study content.
    return catalogue.get_recipe(t.template_key, t.template_version)


@router.get("/workspaces/{wid}/collaboration/templates/{iid}/shared")
def template_read(wid: UUID, iid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return shared_template(s, wid, user.id, iid)


@router.get("/workspaces/{wid}/collaboration/api/templates/{iid}")
def api_template(wid: UUID, iid: UUID, request: Request, x_api_key: Annotated[str, Header()]):
    with request.app.state.database.sessions.begin() as s:
        return shared_template(s, wid, service.key_actor(s, wid, x_api_key, "templates:read"), iid)


@router.delete("/workspaces/{wid}/collaboration/{kind}/grants/{gid}", status_code=204)
def revoke_grant(wid: UUID, kind: str, gid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id)
        model = {"reports": ReportGrant, "templates": TemplateGrant}.get(kind)
        if model is None:
            service.deny()
        g = s.get(model, gid)
        if not g or g.workspace_id != wid or g.issuer_id != user.id:
            service.deny()
        g.revoked = True


@router.put("/workspaces/{wid}/collaboration/notification-preferences")
def preference(wid: UUID, body: PreferenceBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        # Participants need not be workspace staff; consent restriction still applies.
        lock_workspace(s, wid)
        service.require_notification_subject(s, wid, user.id)
        row = s.scalar(
            select(NotificationPreference).where(
                NotificationPreference.workspace_id == wid,
                NotificationPreference.user_id == user.id,
            )
        )
        if not row:
            row = NotificationPreference(workspace_id=wid, user_id=user.id)
            s.add(row)
        row.reminders = body.reminders
        return {"reminders": row.reminders}


@router.get("/participant/bookings/{bid}/calendar.ics")
def calendar(bid: UUID, revision: Annotated[int, Query(ge=0)], request: Request, user: Actor):
    from .calendar import booking_ics

    with request.app.state.database.sessions.begin() as s:
        return Response(
            booking_ics(s, user.id, bid, revision),
            media_type="text/calendar",
            headers={"Cache-Control": "no-store"},
        )


@router.post("/workspaces/{wid}/collaboration/integrations", status_code=201)
def integration(wid: UUID, body: IntegrationBody, request: Request, user: Actor):
    settings = request.app.state.settings
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id, True)
        if getattr(settings, "collaboration_integration_mode", "disabled") not in {"mock", "live"}:
            service.deny()
        webhooks.validate_destination(body.destination, settings.collaboration_webhook_destinations)
        row = Integration(
            workspace_id=wid, creator_id=user.id, destination=body.destination, enabled=True
        )
        s.add(row)
        s.flush()
        return {"id": str(row.id), "mode": settings.collaboration_integration_mode}


@router.delete("/workspaces/{wid}/collaboration/integrations/{iid}", status_code=204)
def disable_integration(wid: UUID, iid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id, True)
        row = s.get(Integration, iid)
        if not row or row.workspace_id != wid:
            service.deny()
        row.enabled = False
        row.revision += 1


@router.post("/workspaces/{wid}/collaboration/integrations/{iid}/deliveries", status_code=202)
def deliver(wid: UUID, iid: UUID, body: DeliveryBody, request: Request, user: Actor):
    rate_limit(request, "collaboration_delivery", str(user.id), 30)
    with request.app.state.database.sessions.begin() as s:
        service.member(s, wid, user.id, True)
        i = s.get(Integration, iid)
        if not i or i.workspace_id != wid or not i.enabled:
            service.deny()
        row = s.scalar(
            select(WebhookDelivery).where(
                WebhookDelivery.integration_id == iid,
                WebhookDelivery.command_key == body.command_key,
            )
        )
        if row:
            if row.requester_id != user.id:
                service.deny()
            existing = s.scalar(
                select(Job).where(
                    Job.workspace_id == wid,
                    Job.kind == "collaboration.webhook",
                    Job.target_id == row.id,
                )
            )
            if existing:
                return {"id": str(row.id), "job_id": str(existing.id), "state": row.state}
        if not row:
            row = WebhookDelivery(
                workspace_id=wid,
                integration_id=iid,
                integration_revision=i.revision,
                requester_id=user.id,
                command_key=body.command_key,
            )
            s.add(row)
            s.flush()
        job = enqueue(
            s,
            workspace_id=wid,
            requester_id=user.id,
            command_key="webhook:" + str(row.id),
            kind="collaboration.webhook",
            target_id=row.id,
            internal=True,
            max_attempts=3,
        )
        return {"id": str(row.id), "job_id": str(job.id), "state": row.state}


@router.get("/workspaces/{wid}/collaboration/notification-preferences")
def get_preference(wid: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        lock_workspace(s, wid)
        service.require_notification_subject(s, wid, user.id)
        return {"reminders": service.notification_allowed(s, wid, user.id)}
