"""Optional source-linked mail on the embedded worker, never arbitrary job payloads.

Workspace -> recipient -> delivery is the claim lock order. Recovery commits in a
separate transaction. Committed dispatching is irrevocable; pending cancellation
cannot recall SMTP. The process-local privacy gate spans physical SMTP, not SQL.
Only known pre-dispatch unavailability retries. Restored work is quarantined.
"""

import hmac
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, func, or_, select, update

from app.auth.models import User, Workspace
from app.auth.outbox import TERMINAL, capability, send_outcome
from app.auth.security import token_hash, utcnow
from app.collaboration.models import NotificationDelivery, NotificationPreference
from app.common.errors import DomainError
from app.common.privacy import lock_workspace, require_unrestricted


def email_allowed(session, wid, uid):
    row = session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.workspace_id == wid, NotificationPreference.user_id == uid
        )
    )
    return bool(row and row.reminders and row.email_reminders)


def _deny():
    raise DomainError("NOTIFICATION_UNAVAILABLE", "Notification is not available.", 409)


def _source_filter(purpose, source_id):
    column = {
        "recruitment_invite": NotificationDelivery.invitation_id,
        "interview_reminder": NotificationDelivery.notification_id,
        "diary_reminder": NotificationDelivery.occurrence_id,
    }[purpose]
    return column == source_id


def enqueue(session, wid, recipient, issuer, purpose, source_id, expires_at, run_after=None):
    """Caller owns workspace/source serialization; no external effects here."""
    previous = session.scalar(
        select(NotificationDelivery)
        .where(NotificationDelivery.workspace_id == wid, _source_filter(purpose, source_id))
        .order_by(NotificationDelivery.created_at.desc(), NotificationDelivery.id.desc())
        .limit(1)
    )
    if previous and (
        purpose != "recruitment_invite"
        or previous.state in {"pending", "dispatching"}
        or (
            previous.outcome != "restore_quarantine"
            and previous.created_at > utcnow() - timedelta(seconds=60)
        )
    ):
        return previous.id
    row = NotificationDelivery(
        workspace_id=wid,
        recipient_id=recipient,
        issuer_id=issuer,
        purpose=purpose,
        invitation_id=source_id if purpose == "recruitment_invite" else None,
        notification_id=source_id if purpose == "interview_reminder" else None,
        occurrence_id=source_id if purpose == "diary_reminder" else None,
        privacy_epoch=session.get(Workspace, wid).privacy_epoch,
        expires_at=expires_at,
        run_after=run_after or utcnow(),
    )
    session.add(row)
    session.flush()
    return row.id


def enqueue_invitation(session, settings, wid, issuer, invitation_id):
    from app.recruiting.models import Candidate, Invitation
    from app.recruiting.service import manage_launch, validate_source

    lock_workspace(session, wid)
    invite = session.get(Invitation, invitation_id)
    if not invite or invite.workspace_id != wid or invite.issued_by != issuer:
        _deny()
    candidate = session.get(Candidate, invite.candidate_id)
    manage_launch(session, wid, issuer, candidate.launch_id)
    validate_source(session, candidate)
    raw = capability(settings, "recruitment_invite", invite.id)
    if (
        candidate.source_kind != "public"
        or not candidate.subject_id
        or candidate.status not in {"invited", "eligible"}
        or invite.revoked_at
        or invite.redeemed_at
        or invite.expires_at <= utcnow()
        or not hmac.compare_digest(invite.token_hash, token_hash(raw))
    ):
        _deny()
    return enqueue(
        session,
        wid,
        candidate.subject_id,
        issuer,
        "recruitment_invite",
        invite.id,
        invite.expires_at,
    )


def enqueue_booking(session, note):
    from app.longitudinal.models import Booking, ScheduleSlot

    booking = session.get(Booking, note.booking_id)
    slot = session.get(ScheduleSlot, booking.slot_id)
    if email_allowed(session, note.workspace_id, booking.subject_id):
        return enqueue(
            session,
            note.workspace_id,
            booking.subject_id,
            slot.host_id,
            "interview_reminder",
            note.id,
            slot.starts_at,
            max(utcnow(), slot.starts_at - timedelta(hours=24)),
        )


def enqueue_diary(session, occurrence, issuer):
    from app.collection.models import CollectionSession

    base = session.get(CollectionSession, occurrence.base_session_id)
    if email_allowed(session, occurrence.workspace_id, base.subject_id):
        return enqueue(
            session,
            occurrence.workspace_id,
            base.subject_id,
            issuer,
            "diary_reminder",
            occurrence.id,
            occurrence.due_at,
            max(utcnow(), occurrence.opens_at),
        )


def _authorize(session, settings, row):
    recipient = session.scalar(select(User).where(User.id == row.recipient_id).with_for_update())
    issuer = session.get(User, row.issuer_id)
    for user in (recipient, issuer):
        if not user or user.status != "active" or not user.verified_at:
            _deny()
        require_unrestricted(session, row.workspace_id, user.id)
    if row.purpose == "recruitment_invite":
        from app.recruiting.models import Candidate, Invitation
        from app.recruiting.service import manage_launch, validate_source

        invite = session.get(Invitation, row.invitation_id, populate_existing=True)
        if (
            not invite
            or invite.workspace_id != row.workspace_id
            or invite.issued_by != row.issuer_id
            or invite.revoked_at
            or invite.redeemed_at
            or invite.expires_at <= utcnow()
        ):
            _deny()
        candidate = session.get(Candidate, invite.candidate_id, populate_existing=True)
        if (
            not candidate
            or candidate.subject_id != row.recipient_id
            or candidate.source_kind != "public"
            or candidate.status not in {"invited", "eligible"}
        ):
            _deny()
        manage_launch(session, row.workspace_id, row.issuer_id, candidate.launch_id)
        validate_source(session, candidate)
        raw = capability(settings, "recruitment_invite", invite.id)
        if not hmac.compare_digest(invite.token_hash, token_hash(raw)):
            _deny()
        return recipient.email, raw
    if not email_allowed(session, row.workspace_id, row.recipient_id):
        _deny()
    from app.longitudinal.service import participant_version, staff_version

    if row.purpose == "interview_reminder":
        from app.longitudinal.models import Booking, Notification, ScheduleSlot

        note = session.get(Notification, row.notification_id, populate_existing=True)
        booking = session.get(Booking, note.booking_id, populate_existing=True) if note else None
        slot = session.get(ScheduleSlot, booking.slot_id) if booking else None
        if (
            not booking
            or booking.subject_id != row.recipient_id
            or booking.state != "booked"
            or booking.revision != note.booking_revision
            or slot.host_id != row.issuer_id
            or slot.starts_at <= utcnow()
        ):
            _deny()
        version_id = slot.version_id
    else:
        from app.collection.models import CollectionSession
        from app.longitudinal.models import DiaryOccurrence

        occurrence = session.get(DiaryOccurrence, row.occurrence_id, populate_existing=True)
        base = session.get(CollectionSession, occurrence.base_session_id) if occurrence else None
        child = session.scalar(
            select(CollectionSession).where(
                CollectionSession.diary_occurrence_id == row.occurrence_id
            )
        )
        if (
            not base
            or base.subject_id != row.recipient_id
            or base.state != "submitted"
            or not occurrence.opens_at <= utcnow() < occurrence.due_at
            or (child and child.state in {"submitted", "withdrawn", "erased"})
        ):
            _deny()
        version_id = base.version_id
    participant_version(session, row.workspace_id, row.recipient_id, version_id)
    staff_version(session, row.workspace_id, row.issuer_id, version_id, "edit")
    return recipient.email, None


def recover(session):
    now = utcnow()
    for row in session.scalars(
        select(NotificationDelivery)
        .where(
            (
                (NotificationDelivery.state == "dispatching")
                & (NotificationDelivery.lease_expires_at <= now)
            )
            | ((NotificationDelivery.state == "pending") & (NotificationDelivery.expires_at <= now))
        )
        .order_by(NotificationDelivery.created_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    ):
        row.state = "uncertain" if row.state == "dispatching" else "cancelled"
        row.outcome = "dispatch_expired" if row.state == "uncertain" else "source_expired"
    ids = (
        select(NotificationDelivery.id)
        .where(
            NotificationDelivery.state.in_(TERMINAL),
            NotificationDelivery.expires_at < now - timedelta(days=7),
        )
        .order_by(NotificationDelivery.expires_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    session.execute(delete(NotificationDelivery).where(NotificationDelivery.id.in_(ids)))


def _claim(session, settings, delivery_id=None):
    query = select(NotificationDelivery).where(
        NotificationDelivery.state == "pending", NotificationDelivery.run_after <= utcnow()
    )
    if delivery_id is not None:
        query = query.where(NotificationDelivery.id == delivery_id)
    hint = session.scalar(
        query.order_by(NotificationDelivery.run_after, NotificationDelivery.id).limit(1)
    )
    if hint is None:
        return None
    workspace = lock_workspace(session, hint.workspace_id)
    valid = workspace.status == "active" and workspace.privacy_epoch == hint.privacy_epoch
    content = None
    if valid:
        try:
            content = _authorize(session, settings, hint)
        except DomainError:
            valid = False
    row = session.scalar(
        select(NotificationDelivery)
        .where(NotificationDelivery.id == hint.id, NotificationDelivery.state == "pending")
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    )
    if row is None or row.run_after > utcnow():
        return None
    if not valid or row.attempts >= 3 or row.expires_at <= utcnow():
        row.state, row.outcome = "cancelled", "authority_changed"
        return ()
    row.state, row.outcome = "dispatching", None
    row.attempts += 1
    row.lease_token = uuid4()
    row.lease_expires_at = utcnow() + timedelta(seconds=settings.smtp_timeout_seconds * 8 + 30)
    return row.id, row.lease_token, row.workspace_id, content[0], row.purpose, content[1]


def dispatch_one(database, settings, delivery_id=None, sender=None):
    from app.auth.delivery import deliver
    from app.common.dispatch_gate import transfer
    from app.privacy_ops.restore import restore_ready

    if not restore_ready(database.engine, settings.private_root):
        return False
    with database.sessions.begin() as session:
        recover(session)
    if settings.mail_mode == "disabled":
        return False
    gate = None
    try:
        with database.sessions.begin() as session:
            claimed = _claim(session, settings, delivery_id)
            if claimed:
                gate = transfer(session, claimed[2])
        if claimed is None:
            return False
        if not claimed:
            return True
        row_id, lease, _, email, purpose, raw = claimed
        outcome = send_outcome(
            sender or (lambda *args: deliver(settings, *args)), email, purpose, raw
        )
    finally:
        if gate is not None:
            gate.release()
    with database.sessions.begin() as session:
        row = session.scalar(
            select(NotificationDelivery)
            .where(
                NotificationDelivery.id == row_id,
                NotificationDelivery.state == "dispatching",
                NotificationDelivery.lease_token == lease,
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


def dispatch_local(database, settings, delivery_id):
    if (
        delivery_id is not None
        and settings.app_env in {"development", "test"}
        and settings.mail_mode == "local"
        and not settings.job_runner_enabled
    ):
        dispatch_one(database, settings, delivery_id)


def cancel_subject(session, subject_id, workspace_id=None, reminders_only=False):
    """Workspace privacy callers own its lock; global panel callers own the user lock."""
    query = update(NotificationDelivery).where(
        NotificationDelivery.state == "pending",
        or_(
            NotificationDelivery.recipient_id == subject_id,
            NotificationDelivery.issuer_id == subject_id,
        ),
    )
    if workspace_id is not None:
        query = query.where(NotificationDelivery.workspace_id == workspace_id)
    if reminders_only:
        query = query.where(
            NotificationDelivery.purpose != "recruitment_invite",
            NotificationDelivery.recipient_id == subject_id,
        )
    session.execute(query.values(state="cancelled", outcome="consent_changed"))


def cancel_booking(session, booking_id):
    from app.longitudinal.models import Notification

    session.execute(
        update(NotificationDelivery)
        .where(
            NotificationDelivery.state == "pending",
            NotificationDelivery.notification_id.in_(
                select(Notification.id).where(Notification.booking_id == booking_id)
            ),
        )
        .values(state="cancelled", outcome="source_changed")
    )


def quarantine_restored(session):
    session.execute(
        update(NotificationDelivery)
        .where(NotificationDelivery.state.in_(["pending", "dispatching"]))
        .values(state="uncertain", outcome="restore_quarantine")
    )


def aggregates(session):
    return [
        dict(
            state=state,
            outcome=outcome,
            count=count,
            oldest_age_seconds=max(0, int((utcnow() - oldest).total_seconds())),
        )
        for state, outcome, count, oldest in session.execute(
            select(
                NotificationDelivery.state,
                NotificationDelivery.outcome,
                func.count(),
                func.min(NotificationDelivery.created_at),
            ).group_by(NotificationDelivery.state, NotificationDelivery.outcome)
        )
    ]
