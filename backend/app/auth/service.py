"""Service-owned transactions and deny-by-default workspace capabilities."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.auth.models import (
    AuditEvent,
    Membership,
    OneTimeToken,
    RefreshToken,
    User,
    Workspace,
    WorkspaceInvite,
)
from app.auth.security import (
    DUMMY_HASH,
    access_token,
    new_secret,
    password_hasher,
    token_hash,
    utcnow,
    verify_password,
)
from app.common.errors import DomainError

CAPABILITIES = {
    "privacy.manage": {"owner", "admin"},
    "assets.create": {"owner", "admin", "researcher"},
    "studies.create": {"owner", "admin", "researcher"},
    "workspace.read": {"owner", "admin", "researcher", "reviewer", "viewer"},
    "members.read": {"owner", "admin"},
    "members.manage": {"owner", "admin"},
    "jobs.create": {"owner", "admin", "researcher"},
    "jobs.read": {"owner", "admin", "researcher", "reviewer", "viewer"},
    "audit.read": {"owner", "admin"},
}


def audit(session, action, actor_id=None, workspace_id=None, object_id=None, **details):
    session.add(
        AuditEvent(
            action=action,
            actor_id=actor_id,
            workspace_id=workspace_id,
            object_id=object_id,
            details=details,
        )
    )


def require_workspace(session, user_id, workspace_id, capability):
    member = session.scalar(
        select(Membership)
        .join(Workspace)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.user_id == user_id,
            Membership.workspace_id == workspace_id,
            Membership.status == "active",
            Workspace.status == "active",
            User.status == "active",
            User.verified_at.is_not(None),
        )
    )
    if member is None:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    if member.role not in CAPABILITIES.get(capability, set()):
        raise DomainError("FORBIDDEN", "Action not permitted.", 403)
    return member


def _issue_one_time(session, user, purpose, seconds):
    now = utcnow()
    session.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user.id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw = new_secret()
    session.add(
        OneTimeToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=token_hash(raw),
            expires_at=now + timedelta(seconds=seconds),
        )
    )
    return raw


class AuthService:
    def __init__(self, database, settings, deliver):
        self.database, self.settings, self.deliver = database, settings, deliver

    def register(self, email, password, display_name):
        # Hash in both new/duplicate cases; do not change an existing account's password.
        hashed = password_hasher.hash(password)
        raw = None
        with self.database.sessions.begin() as session:
            uid = session.scalar(
                insert(User)
                .values(
                    id=uuid4(),
                    email=email,
                    password_hash=hashed,
                    display_name=display_name,
                    status="active",
                    auth_version=0,
                )
                .on_conflict_do_nothing(index_elements=["email"])
                .returning(User.id)
            )
            if uid:
                user = session.get(User, uid)
                raw = _issue_one_time(session, user, "verify", self.settings.auth_verify_seconds)
                audit(session, "auth.register", user.id)
        if raw:
            self.deliver(email, "verify", raw)

    def request_token(self, email, purpose):
        raw = None
        with self.database.sessions.begin() as session:
            user = session.scalar(select(User).where(User.email == email).with_for_update())
            if (
                user
                and user.status == "active"
                and (purpose == "reset" or user.verified_at is None)
            ):
                raw = _issue_one_time(session, user, purpose, self.settings.auth_verify_seconds)
                audit(session, f"auth.{purpose}_requested", user.id)
        if raw:
            self.deliver(email, purpose, raw)

    def consume_token(self, raw, purpose, new_password=None):
        hashed = password_hasher.hash(new_password) if new_password is not None else None
        with self.database.sessions.begin() as session:
            token = session.scalar(
                select(OneTimeToken).where(OneTimeToken.token_hash == token_hash(raw))
            )
            if token is None:
                raise DomainError("INVALID_TOKEN", "Token is invalid or expired.", 400)
            # All changes to a user's auth state lock the user first.
            user = session.scalar(select(User).where(User.id == token.user_id).with_for_update())
            session.refresh(token, with_for_update=True)
            now = utcnow()
            if (
                token.purpose != purpose
                or token.used_at
                or token.expires_at <= now
                or user.status != "active"
            ):
                raise DomainError("INVALID_TOKEN", "Token is invalid or expired.", 400)
            token.used_at = now
            if purpose == "verify":
                user.verified_at = now
            else:
                user.password_hash = hashed
                user.auth_version += 1
                session.execute(
                    update(RefreshToken)
                    .where(RefreshToken.user_id == user.id)
                    .values(revoked_at=now)
                )
                session.execute(
                    update(OneTimeToken)
                    .where(
                        OneTimeToken.user_id == user.id,
                        OneTimeToken.purpose == "reset",
                        OneTimeToken.used_at.is_(None),
                    )
                    .values(used_at=now)
                )
            audit(session, f"auth.{purpose}_completed", user.id)

    def _new_login(self, session, user, family_id=None, expires_at=None):
        raw, csrf = new_secret(), new_secret()
        family_id = family_id or uuid4()
        record = RefreshToken(
            user_id=user.id,
            family_id=family_id,
            token_hash=token_hash(raw),
            csrf_hash=token_hash(csrf),
            expires_at=expires_at or utcnow() + timedelta(days=self.settings.auth_refresh_days),
        )
        session.add(record)
        session.flush()
        return {
            "access_token": access_token(user, family_id, self.settings),
            "token_type": "bearer",
            "expires_in": self.settings.auth_access_seconds,
            "csrf_token": csrf,
            "refresh_token": raw,
            "family_id": str(family_id),
        }

    def login(self, email, password):
        with self.database.sessions.begin() as session:
            user = session.scalar(select(User).where(User.email == email).with_for_update())
            valid = verify_password(password, user.password_hash if user else DUMMY_HASH)
            if not valid or user is None or user.status != "active" or user.verified_at is None:
                raise DomainError(
                    "UNAUTHORIZED", "Invalid credentials or account unavailable.", 401
                )
            result = self._new_login(session, user)
            audit(session, "auth.login", user.id)
            return result

    def refresh(self, raw, csrf):
        outcome = None
        invalid = False
        with self.database.sessions.begin() as session:
            token = session.scalar(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash(raw))
            )
            if token is None:
                raise DomainError("UNAUTHORIZED", "Authentication required.", 401)
            user = session.scalar(select(User).where(User.id == token.user_id).with_for_update())
            session.refresh(token, with_for_update=True)
            now = utcnow()
            import secrets

            if not secrets.compare_digest(token.csrf_hash, token_hash(csrf)):
                raise DomainError("CSRF_FAILED", "Request verification failed.", 403)
            if token.used_at:
                session.execute(
                    update(RefreshToken)
                    .where(RefreshToken.family_id == token.family_id)
                    .values(revoked_at=now)
                )
                audit(session, "auth.refresh_reuse", user.id)
                invalid = True
            elif (
                token.revoked_at
                or token.expires_at <= now
                or user.status != "active"
                or not user.verified_at
            ):
                invalid = True
            else:
                token.used_at = now
                outcome = self._new_login(session, user, token.family_id, token.expires_at)
        # Raise after commit so refresh replay revocation cannot be rolled back by the error.
        if invalid:
            raise DomainError("UNAUTHORIZED", "Authentication required.", 401)
        return outcome

    def revoke_family(self, user_id, family_id):
        with self.database.sessions.begin() as session:
            session.scalar(select(User).where(User.id == user_id).with_for_update())
            session.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == user_id, RefreshToken.family_id == family_id)
                .values(revoked_at=utcnow())
            )
            audit(session, "auth.session_revoked", user_id, object_id=family_id)


def create_workspace(session, user_id, name):
    workspace = Workspace(name=name)
    session.add(workspace)
    session.flush()
    session.add(Membership(workspace_id=workspace.id, user_id=user_id, role="owner"))
    audit(session, "workspace.created", user_id, workspace.id, workspace.id)
    return workspace


def change_member(session, actor_id, workspace_id, member_id, role=None):
    # Lock workspace before reading roles: serializes last-owner removal and escalation checks.
    from app.common.privacy import lock_workspace

    lock_workspace(session, workspace_id)
    actor = require_workspace(session, actor_id, workspace_id, "members.manage")
    target = session.scalar(
        select(Membership)
        .where(
            Membership.id == member_id,
            Membership.workspace_id == workspace_id,
            Membership.status == "active",
        )
        .with_for_update()
    )
    if target is None:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    if actor.role != "owner" and (target.role in {"owner", "admin"} or role in {"owner", "admin"}):
        raise DomainError("FORBIDDEN", "Action not permitted.", 403)
    if target.role == "owner" and role != "owner":
        count = session.scalar(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.workspace_id == workspace_id,
                Membership.status == "active",
                Membership.role == "owner",
            )
        )
        if count <= 1:
            raise DomainError("LAST_OWNER", "A workspace must retain an active owner.", 409)
    if role is None:
        target.status = "revoked"
    else:
        target.role = role
    audit(
        session,
        "membership.changed",
        actor_id,
        workspace_id,
        target.id,
        role=target.role,
        status=target.status,
    )
    return target


def invite_member(session, actor_id, workspace_id, email, role):
    session.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
    actor = require_workspace(session, actor_id, workspace_id, "members.manage")
    if actor.role != "owner" and role == "admin":
        raise DomainError("FORBIDDEN", "Action not permitted.", 403)
    now = utcnow()
    session.execute(
        update(WorkspaceInvite)
        .where(
            WorkspaceInvite.workspace_id == workspace_id,
            WorkspaceInvite.email == email,
            WorkspaceInvite.accepted_at.is_(None),
            WorkspaceInvite.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    raw = new_secret()
    record = WorkspaceInvite(
        workspace_id=workspace_id,
        invited_by=actor_id,
        email=email,
        role=role,
        token_hash=token_hash(raw),
        expires_at=now + timedelta(days=7),
    )
    session.add(record)
    session.flush()
    audit(session, "workspace.invited", actor_id, workspace_id, record.id, role=role)
    return record, raw


def accept_invite(session, user, raw):
    invite = session.scalar(
        select(WorkspaceInvite).where(WorkspaceInvite.token_hash == token_hash(raw))
    )
    if invite is None:
        raise DomainError("INVALID_TOKEN", "Invitation is invalid or expired.", 400)
    workspace = session.scalar(
        select(Workspace).where(Workspace.id == invite.workspace_id).with_for_update()
    )
    session.refresh(invite, with_for_update=True)
    if (
        invite.email != user.email
        or invite.revoked_at
        or invite.expires_at <= utcnow()
        or workspace.status != "active"
    ):
        raise DomainError("INVALID_TOKEN", "Invitation is invalid or expired.", 400)
    # Recheck inviter's current authority. A revoked inviter cannot confer rights later.
    actor = require_workspace(session, invite.invited_by, workspace.id, "members.manage")
    if actor.role != "owner" and invite.role == "admin":
        raise DomainError("FORBIDDEN", "Action not permitted.", 403)
    member = session.scalar(
        select(Membership).where(
            Membership.workspace_id == workspace.id, Membership.user_id == user.id
        )
    )
    if invite.accepted_at:
        if member and member.status == "active":
            return member
        raise DomainError("INVALID_TOKEN", "Invitation is invalid or expired.", 400)
    if member is None:
        member = Membership(workspace_id=workspace.id, user_id=user.id, role=invite.role)
        session.add(member)
    elif member.status == "revoked":
        member.status, member.role = "active", invite.role
    # Already-active users keep their current role, never silently downgrade an owner.
    invite.accepted_at = utcnow()
    session.flush()
    audit(session, "workspace.invite_accepted", user.id, workspace.id, member.id)
    return member
