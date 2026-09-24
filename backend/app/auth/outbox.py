"""Auth-scoped delivery; no capability or recipient is persisted in this queue.

Committing dispatching is the irrevocable send boundary. Cancellation only removes
pending work, never recalls that dispatch. No SQL transaction spans SMTP. The
workspace dispatch gate fences privacy mutations until the physical send returns;
this embedded-worker gate is single-process, not a multi-process SMTP guarantee.
Accepted means SMTP accepted, not delivered to an inbox. Unknown outcomes never retry.
"""

import hashlib
import hmac
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, func, or_, select, update

from app.auth.models import AuthDelivery, OneTimeToken, User, WorkspaceInvite
from app.auth.security import token_hash, utcnow
from app.common.errors import DomainError

TERMINAL = {"sent", "failed", "uncertain", "cancelled"}


def capability(settings, purpose, source_id):
    if purpose not in {"verify", "reset", "workspace_invite", "recruitment_invite"}:
        raise ValueError("Unknown delivery purpose")
    message = f"elseview:auth-mail:v1:{purpose}:{source_id}".encode("ascii")
    return hmac.new(
        settings.secret_key.get_secret_value().encode(), message, hashlib.sha256
    ).hexdigest()


def enqueue(session, source, purpose):
    now = utcnow()
    source_filter = (
        AuthDelivery.invite_id == source.id
        if purpose == "workspace_invite"
        else AuthDelivery.token_id == source.id
    )
    previous = session.scalar(
        select(AuthDelivery).where(source_filter).order_by(AuthDelivery.created_at.desc()).limit(1)
    )
    if previous and (
        previous.state in {"pending", "dispatching"}
        or (
            previous.outcome != "restore_quarantine"
            and previous.created_at > now - timedelta(seconds=60)
        )
    ):
        return previous.id
    row = AuthDelivery(
        id=uuid4(),
        purpose=purpose,
        token_id=None if purpose == "workspace_invite" else source.id,
        invite_id=source.id if purpose == "workspace_invite" else None,
        expires_at=source.expires_at,
    )
    session.add(row)
    session.flush()
    return row.id


def enqueue_auth(session, user, purpose, settings):
    session.refresh(user, with_for_update=True)
    if purpose not in {"verify", "reset"}:
        raise ValueError("Unknown auth purpose")
    now = utcnow()
    candidates = session.scalars(
        select(OneTimeToken)
        .where(
            OneTimeToken.user_id == user.id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.used_at.is_(None),
            OneTimeToken.expires_at > now + timedelta(seconds=30),
        )
        .order_by(OneTimeToken.expires_at.desc())
    )
    source = next(
        (
            candidate
            for candidate in candidates
            if hmac.compare_digest(
                candidate.token_hash, token_hash(capability(settings, purpose, candidate.id))
            )
        ),
        None,
    )
    if source is None:
        source = OneTimeToken(
            id=uuid4(),
            user_id=user.id,
            purpose=purpose,
            expires_at=now + timedelta(seconds=settings.auth_verify_seconds),
        )
        source.token_hash = token_hash(capability(settings, purpose, source.id))
        session.add(source)
        session.flush()
    return enqueue(session, source, purpose)


def recover(session):
    now = utcnow()
    rows = session.scalars(
        select(AuthDelivery)
        .where(
            ((AuthDelivery.state == "dispatching") & (AuthDelivery.lease_expires_at <= now))
            | ((AuthDelivery.state == "pending") & (AuthDelivery.expires_at <= now))
        )
        .order_by(AuthDelivery.created_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    for row in rows:
        row.state = "uncertain" if row.state == "dispatching" else "cancelled"
        row.outcome = "dispatch_expired" if row.state == "uncertain" else "capability_expired"


def _claim(session, settings, delivery_id=None):
    query = select(AuthDelivery).where(
        AuthDelivery.state == "pending", AuthDelivery.run_after <= utcnow()
    )
    if delivery_id is not None:
        query = query.where(AuthDelivery.id == delivery_id)
    row = session.scalar(query.order_by(AuthDelivery.created_at, AuthDelivery.id).limit(1))
    if row is None:
        return None
    source = (
        session.get(WorkspaceInvite, row.invite_id)
        if row.invite_id
        else session.get(OneTimeToken, row.token_id)
    )
    if source is None:
        return None
    # Match identity/privacy lock order: workspace (invitations) or user, then outbox.
    if row.invite_id:
        from app.common.privacy import lock_workspace

        owner = lock_workspace(session, source.workspace_id)
    else:
        owner = session.scalar(select(User).where(User.id == source.user_id).with_for_update())
    row = session.scalar(
        select(AuthDelivery)
        .where(AuthDelivery.id == row.id, AuthDelivery.state == "pending")
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )
    if row is None or row.run_after > utcnow():
        return None
    # A privacy transaction may have deleted the source while we waited for its owner.
    source = session.get(type(source), source.id, populate_existing=True)
    if source is None:
        return None
    raw = capability(settings, row.purpose, source.id)
    valid = (
        owner is not None
        and owner.status == "active"
        and source.expires_at > utcnow()
        and hmac.compare_digest(source.token_hash, token_hash(raw))
    )
    if row.invite_id:
        from app.auth.service import require_workspace
        from app.common.privacy import restricted

        recipient = session.scalar(select(User).where(User.email == source.email))
        valid = (
            valid
            and source.revoked_at is None
            and source.accepted_at is None
            and not restricted(session, source.workspace_id, source.invited_by)
            and (
                recipient is None
                or (
                    recipient.status == "active"
                    and not restricted(session, source.workspace_id, recipient.id)
                )
            )
        )
        try:
            actor = require_workspace(
                session, source.invited_by, source.workspace_id, "members.manage"
            )
            valid = valid and (actor.role == "owner" or source.role != "admin")
        except DomainError:
            valid = False
        email = source.email
    else:
        valid = (
            valid
            and source.purpose == row.purpose
            and source.used_at is None
            and (row.purpose == "reset" or owner.verified_at is None)
        )
        email = owner.email if owner else ""
    if not valid or row.attempts >= 3:
        row.state, row.outcome = "cancelled", "authority_changed"
        return ()
    row.state, row.outcome = "dispatching", None
    row.attempts += 1
    row.lease_token = uuid4()
    row.lease_expires_at = utcnow() + timedelta(seconds=settings.smtp_timeout_seconds * 8 + 30)
    return row.id, row.lease_token, email, row.purpose, raw


def dispatch_one(database, settings, delivery_id=None, sender=None):
    from app.auth.delivery import deliver
    from app.privacy_ops.restore import restore_ready

    if not restore_ready(database.engine, settings.private_root):
        return False
    # Recovery touches only delivery rows and commits before acquiring an owner.
    with database.sessions.begin() as session:
        recover(session)
        prune(session)
    if settings.mail_mode == "disabled":
        return False
    gate = None
    try:
        with database.sessions.begin() as session:
            claimed = _claim(session, settings, delivery_id)
            if claimed and claimed[3] == "workspace_invite":
                from app.common.dispatch_gate import transfer

                row = session.get(AuthDelivery, claimed[0])
                source = session.get(WorkspaceInvite, row.invite_id)
                gate = transfer(session, source.workspace_id)
        if claimed is None:
            return False
        if not claimed:
            return True
        row_id, lease_token, email, purpose, raw = claimed
        outcome = send_outcome(
            sender or (lambda *args: deliver(settings, *args)), email, purpose, raw
        )
    finally:
        # Release before completion's SQL lock: privacy may hold workspace and wait here.
        if gate is not None:
            gate.release()
    with database.sessions.begin() as session:
        row = session.scalar(
            select(AuthDelivery)
            .where(
                AuthDelivery.id == row_id,
                AuthDelivery.lease_token == lease_token,
                AuthDelivery.state == "dispatching",
            )
            .with_for_update()
        )
        if row is not None:
            row.outcome = outcome
            if outcome == "accepted":
                row.state, row.sent_at = "sent", utcnow()
            elif (
                outcome == "DELIVERY_UNAVAILABLE"
                and row.attempts < 3
                and row.expires_at > utcnow() + timedelta(seconds=60)
            ):
                row.state = "pending"
                row.run_after = utcnow() + timedelta(seconds=30 * 2 ** (row.attempts - 1))
            else:
                row.state = "uncertain" if outcome == "DELIVERY_UNCERTAIN" else "failed"
    return True


def send_outcome(sender, email, purpose, raw):
    try:
        sender(email, purpose, raw)
    except DomainError as exc:
        return (
            exc.code
            if exc.code in {"DELIVERY_UNAVAILABLE", "DELIVERY_REJECTED", "DELIVERY_UNCERTAIN"}
            else "DELIVERY_UNCERTAIN"
        )
    except Exception:
        return "DELIVERY_UNCERTAIN"
    return "accepted"


def dispatch_local(database, settings, delivery_id, sender):
    if (
        delivery_id is not None
        and settings.app_env in {"development", "test"}
        and settings.mail_mode == "local"
        and not settings.job_runner_enabled
    ):
        dispatch_one(database, settings, delivery_id, sender)


def quarantine_restored(session):
    """A pre-send snapshot cannot prove that mail was not accepted after backup."""
    session.execute(
        update(AuthDelivery)
        .where(AuthDelivery.state.in_(["pending", "dispatching"]))
        .values(state="uncertain", outcome="restore_quarantine")
    )


def cancel_invites(session, invite_ids, outcome="authority_changed"):
    # Caller holds workspace locks (or global erasure's ordered scopes and user lock).
    session.execute(
        update(AuthDelivery)
        .where(AuthDelivery.invite_id.in_(invite_ids), AuthDelivery.state == "pending")
        .values(state="cancelled", outcome=outcome)
    )


def restrict_subject(session, workspace_id, subject_id):
    email = session.scalar(select(User.email).where(User.id == subject_id))
    ids = select(WorkspaceInvite.id).where(
        WorkspaceInvite.workspace_id == workspace_id,
        or_(WorkspaceInvite.invited_by == subject_id, WorkspaceInvite.email == email),
    )
    cancel_invites(session, ids, "privacy_restricted")
    session.execute(
        update(WorkspaceInvite).where(WorkspaceInvite.id.in_(ids)).values(revoked_at=utcnow())
    )


def prune(session):
    """Bounded batches; source verifiers survive metadata expiry so old links still work."""
    ids = (
        select(AuthDelivery.id)
        .where(
            AuthDelivery.state.in_(TERMINAL),
            AuthDelivery.expires_at < utcnow() - timedelta(days=7),
        )
        .order_by(AuthDelivery.expires_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    session.execute(delete(AuthDelivery).where(AuthDelivery.id.in_(ids)))


def aggregates(session):
    """Internal bounded, PII-free projection; deliberately not a public endpoint."""
    rows = session.execute(
        select(
            AuthDelivery.state,
            AuthDelivery.outcome,
            func.count(),
            func.min(AuthDelivery.created_at),
        ).group_by(AuthDelivery.state, AuthDelivery.outcome)
    ).all()
    now = utcnow()
    return [
        dict(
            state=state,
            outcome=outcome,
            count=count,
            oldest_age_seconds=max(0, int((now - oldest).total_seconds())),
        )
        for state, outcome, count, oldest in rows
    ]


def cancel_tokens(session, user_id, purpose):
    session.execute(
        update(AuthDelivery)
        .where(
            AuthDelivery.token_id.in_(
                select(OneTimeToken.id).where(
                    OneTimeToken.user_id == user_id, OneTimeToken.purpose == purpose
                )
            ),
            AuthDelivery.state == "pending",
        )
        .values(state="cancelled", outcome="capability_used")
    )
