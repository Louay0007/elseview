from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select

from app.auth.dependencies import check_origin, current_user, rate_limit
from app.auth.models import AuditEvent, Membership, RefreshToken, User, Workspace
from app.auth.schemas import (
    EmailBody,
    InviteBody,
    LoginBody,
    MemberBody,
    RegisterBody,
    ResetBody,
    TokenBody,
    WorkspaceBody,
)
from app.auth.security import utcnow
from app.auth.service import (
    accept_invite,
    change_member,
    create_workspace,
    invite_member,
    require_workspace,
)
from app.common.errors import DomainError

router = APIRouter(prefix="/api/v1")
Actor = Annotated[User, Depends(current_user)]
GENERIC = {"message": "If the request is eligible, instructions will be delivered."}
COOKIE = "elseview_refresh"


def user_view(user):
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name}


def member_view(member):
    return {
        "id": str(member.id),
        "user_id": str(member.user_id),
        "role": member.role,
        "status": member.status,
    }


def login_response(request, response, result):
    raw = result.pop("refresh_token")
    response.set_cookie(
        COOKIE,
        raw,
        httponly=True,
        secure=request.app.state.settings.app_env == "production",
        samesite="strict",
        path="/api/v1/auth",
        max_age=request.app.state.settings.auth_refresh_days * 86400,
    )
    return result


@router.post("/auth/register", status_code=202)
def register(body: RegisterBody, request: Request):
    check_origin(request)
    rate_limit(request, "register", body.email, 5)
    request.app.state.auth.register(body.email, body.password.get_secret_value(), body.display_name)
    return GENERIC


@router.post("/auth/verification/request", status_code=202)
def verification_request(body: EmailBody, request: Request):
    check_origin(request)
    rate_limit(request, "verification", body.email, 5)
    request.app.state.auth.request_token(body.email, "verify")
    return GENERIC


@router.post("/auth/verify-email")
def verify_email(body: TokenBody, request: Request):
    check_origin(request)
    rate_limit(request, "verify", request.client.host)
    request.app.state.auth.consume_token(body.token.get_secret_value(), "verify")
    return {"status": "ok"}


@router.post("/auth/login")
def login(body: LoginBody, request: Request, response: Response):
    check_origin(request)
    rate_limit(request, "login", body.email)
    result = request.app.state.auth.login(body.email, body.password.get_secret_value())
    return login_response(request, response, result)


@router.post("/auth/refresh")
def refresh(request: Request, response: Response):
    check_origin(request)
    rate_limit(request, "refresh", request.client.host, 30)
    raw, csrf = request.cookies.get(COOKIE), request.headers.get("x-csrf-token")
    if not raw or not csrf or len(raw) > 256 or len(csrf) > 256:
        raise DomainError("CSRF_FAILED", "Request verification failed.", 403)
    return login_response(request, response, request.app.state.auth.refresh(raw, csrf))


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: Actor):
    # Bearer auth is not automatically attached by a browser. If refresh cookie is present,
    # additionally verify its bound CSRF secret, preventing cookie-authenticated mutation.
    check_origin(request)
    raw = request.cookies.get(COOKIE)
    if raw:
        import secrets

        from app.auth.security import token_hash

        csrf = request.headers.get("x-csrf-token", "")
        with request.app.state.database.sessions() as session:
            record = session.scalar(
                select(RefreshToken).where(
                    RefreshToken.token_hash == token_hash(raw), RefreshToken.user_id == user.id
                )
            )
            if not record or not secrets.compare_digest(record.csrf_hash, token_hash(csrf)):
                raise DomainError("CSRF_FAILED", "Request verification failed.", 403)
    request.app.state.auth.revoke_family(user.id, request.state.auth_family_id)
    response.delete_cookie(COOKIE, path="/api/v1/auth")


@router.post("/auth/password-reset/request", status_code=202)
def reset_request(body: EmailBody, request: Request):
    check_origin(request)
    rate_limit(request, "reset", body.email, 5)
    request.app.state.auth.request_token(body.email, "reset")
    return GENERIC


@router.post("/auth/password-reset/confirm")
def reset_confirm(body: ResetBody, request: Request):
    check_origin(request)
    rate_limit(request, "reset_confirm", request.client.host)
    request.app.state.auth.consume_token(
        body.token.get_secret_value(), "reset", body.password.get_secret_value()
    )
    return {"status": "ok"}


@router.get("/me")
def me(user: Actor):
    return user_view(user)


@router.get("/me/login-sessions")
def sessions(request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        rows = session.scalars(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.used_at.is_(None),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > utcnow(),
            )
            .order_by(RefreshToken.created_at.desc())
            .limit(100)
        ).all()
        return {"items": [{"id": str(row.family_id), "expires_at": row.expires_at} for row in rows]}


@router.delete("/me/login-sessions/{family_id}", status_code=204)
def revoke_session(family_id: UUID, request: Request, user: Actor):
    request.app.state.auth.revoke_family(user.id, family_id)


@router.post("/workspaces", status_code=201)
def new_workspace(body: WorkspaceBody, request: Request, user: Actor):
    rate_limit(request, "workspace_create", str(user.id), 10)
    with request.app.state.database.sessions.begin() as session:
        row = create_workspace(session, user.id, body.name)
        return {
            "id": str(row.id),
            "name": row.name,
            "country": row.country,
            "timezone": row.timezone,
        }


@router.get("/workspaces")
def list_workspaces(
    request: Request,
    user: Actor,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    with request.app.state.database.sessions() as session:
        rows = session.scalars(
            select(Workspace)
            .join(Membership)
            .where(
                Membership.user_id == user.id,
                Membership.status == "active",
                Workspace.status == "active",
            )
            .order_by(Workspace.created_at, Workspace.id)
            .offset(offset)
            .limit(limit)
        ).all()
        return {"items": [{"id": str(r.id), "name": r.name} for r in rows]}


@router.get("/workspaces/{workspace_id}")
def get_workspace(workspace_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "workspace.read")
        row = session.get(Workspace, workspace_id)
        return {
            "id": str(row.id),
            "name": row.name,
            "country": row.country,
            "timezone": row.timezone,
        }


@router.get("/workspaces/{workspace_id}/members")
def members(
    workspace_id: UUID,
    request: Request,
    user: Actor,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "members.read")
        return {
            "items": [
                member_view(m)
                for m in session.scalars(
                    select(Membership)
                    .where(Membership.workspace_id == workspace_id)
                    .order_by(Membership.id)
                    .offset(offset)
                    .limit(limit)
                )
            ]
        }


@router.post("/workspaces/{workspace_id}/invitations", status_code=202)
def invite(workspace_id: UUID, body: InviteBody, request: Request, user: Actor):
    rate_limit(request, "invite", str(user.id), 20)
    with request.app.state.database.sessions.begin() as session:
        record, raw = invite_member(session, user.id, workspace_id, body.email, body.role)
        record_id = record.id
    request.app.state.auth.deliver(body.email, "workspace_invite", raw)
    return {"id": str(record_id), "status": "invited"}


@router.post("/workspace-invitations/accept")
def accept(body: TokenBody, request: Request, user: Actor):
    rate_limit(request, "invite_accept", str(user.id), 20)
    with request.app.state.database.sessions.begin() as session:
        return member_view(accept_invite(session, user, body.token.get_secret_value()))


@router.patch("/workspaces/{workspace_id}/members/{member_id}")
def change_role(
    workspace_id: UUID, member_id: UUID, body: MemberBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        return member_view(change_member(session, user.id, workspace_id, member_id, body.role))


@router.delete("/workspaces/{workspace_id}/members/{member_id}", status_code=204)
def remove_member(workspace_id: UUID, member_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        change_member(session, user.id, workspace_id, member_id)


@router.get("/workspaces/{workspace_id}/audit")
def audit_log(
    workspace_id: UUID,
    request: Request,
    user: Actor,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0, le=10000),
):
    with request.app.state.database.sessions() as session:
        require_workspace(session, user.id, workspace_id, "audit.read")
        rows = session.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == workspace_id)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id)
            .offset(offset)
            .limit(limit)
        )
        return {
            "items": [
                {
                    "id": str(row.id),
                    "action": row.action,
                    "actor_id": str(row.actor_id),
                    "details": row.details,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        }
