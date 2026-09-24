import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select

from app.auth.security import utcnow
from app.auth.service import require_workspace
from app.common.errors import DomainError
from app.common.privacy import lock_workspace, require_unrestricted

from .models import APIKey, NotificationPreference

SCOPES = {"reports:read", "templates:read"}


def deny():
    raise DomainError("NOT_FOUND", "Resource not found.", 404)


def member(session, wid, uid, admin=False):
    lock_workspace(session, wid)
    require_unrestricted(session, wid, uid)
    return require_workspace(session, uid, wid, "members.manage" if admin else "workspace.read")


def issue_key(session, wid, uid, scopes, days):
    member(session, wid, uid)
    if not scopes or not set(scopes) <= SCOPES:
        raise DomainError("INVALID_SCOPE", "Unsupported API key scope.", 422)
    raw = "evk_" + secrets.token_urlsafe(32)
    row = APIKey(
        workspace_id=wid,
        user_id=uid,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        scopes=sorted(set(scopes)),
        expires_at=utcnow() + timedelta(days=days),
    )
    session.add(row)
    session.flush()
    return {"id": str(row.id), "key": raw, "scopes": row.scopes, "expires_at": row.expires_at}


def key_actor(session, wid, raw, scope):
    if not raw or len(raw) > 128:
        deny()
    row = session.scalar(
        select(APIKey).where(
            APIKey.token_hash == hashlib.sha256(raw.encode()).hexdigest(),
            APIKey.workspace_id == wid,
        )
    )
    if not row or row.revoked_at or row.expires_at <= utcnow() or scope not in row.scopes:
        deny()
    member(session, wid, row.user_id)
    return row.user_id


def notification_allowed(session, workspace_id, user_id, kind="reminder"):
    if kind != "reminder":
        return False
    try:
        require_unrestricted(session, workspace_id, user_id)
    except DomainError:
        return False
    row = session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.workspace_id == workspace_id,
            NotificationPreference.user_id == user_id,
        )
    )
    return row is None or row.reminders


def require_notification_subject(session, workspace_id, user_id):
    """Participants may opt out without staff membership, but not in arbitrary tenants."""
    from app.auth.models import Membership
    from app.recruiting.models import Candidate

    require_unrestricted(session, workspace_id, user_id)
    if not session.scalar(
        select(Membership.id).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    ) and not session.scalar(
        select(Candidate.id)
        .where(Candidate.workspace_id == workspace_id, Candidate.subject_id == user_id)
        .limit(1)
    ):
        deny()
