"""Workspace-serialized scheduling and immutable longitudinal evidence."""

from datetime import UTC, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, func, select, text

from app.auth.security import utcnow
from app.collection.models import CollectionSession
from app.collection.service import digest
from app.common.errors import DomainError
from app.common.privacy import consent_granted, get_scoped, lock_workspace, require_unrestricted
from app.common.privacy_models import Asset, AssetLink, ConsentDocument, ConsentReceipt
from app.longitudinal.models import (
    Booking,
    DiaryOccurrence,
    Notification,
    Recording,
    ScheduleSlot,
    TranscriptSegment,
)
from app.studies.models import StudyVersion
from app.studies.service import authorize


def fail(code="LONGITUDINAL_CONFLICT", message="Operation is not available.", status=409):
    raise DomainError(code, message, status)


def local_utc(value, zone):
    try:
        tz = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        fail("INVALID_TIMEZONE", "An IANA timezone is required.", 422)
    if value.local.tzinfo is not None:
        fail("INVALID_LOCAL_TIME", "Local time must not include an offset.", 422)
    candidates = {}
    for fold in (0, 1):
        aware = value.local.replace(tzinfo=tz, fold=fold)
        utc = aware.astimezone(UTC)
        back = utc.astimezone(tz)
        if back.replace(tzinfo=None) == value.local and back.fold == fold:
            candidates[fold] = utc
    if not candidates:
        fail("NONEXISTENT_LOCAL_TIME", "Local time falls in a daylight-saving gap.", 422)
    if len(candidates) > 1 and value.fold is None:
        fail("AMBIGUOUS_LOCAL_TIME", "Choose fold 0 or 1 for repeated local time.", 422)
    fold = value.fold if value.fold is not None else next(iter(candidates))
    if fold not in candidates:
        fail("INVALID_FOLD", "Fold is not valid at this local time.", 422)
    return candidates[fold]


def staff_version(session, wid, actor, vid, capability="edit"):
    version = get_scoped(session, StudyVersion, wid, vid)
    authorize(session, wid, actor, version.study_id, capability)
    if version.state != "published":
        fail("VERSION_UNPUBLISHED")
    return version


def participant_version(session, wid, actor, vid):
    require_unrestricted(session, wid, actor)
    if not consent_granted(session, wid, actor, "study", study_version_id=vid):
        fail("CONSENT_REQUIRED", "Published study consent required.", 403)
    row = session.scalar(
        select(CollectionSession).where(
            CollectionSession.workspace_id == wid,
            CollectionSession.subject_id == actor,
            CollectionSession.version_id == vid,
            CollectionSession.diary_occurrence_id.is_(None),
        )
    )
    if not row or row.state in {"withdrawn", "erased"}:
        fail("NOT_FOUND", "Participation not found.", 404)
    return row


def slot_json(row, private=False):
    result = {
        k: getattr(row, k)
        for k in (
            "id",
            "workspace_id",
            "version_id",
            "starts_at",
            "ends_at",
            "timezone",
            "capacity",
        )
    }
    if private:
        result["join_url"] = row.join_url
    return result


def create_slot(session, wid, actor, body):
    lock_workspace(session, wid)
    staff_version(session, wid, actor, body.version_id)
    start, end = local_utc(body.starts, body.timezone), local_utc(body.ends, body.timezone)
    if (
        start <= utcnow()
        or end - start < timedelta(minutes=5)
        or end - start > timedelta(minutes=240)
    ):
        fail("INVALID_SLOT", "Slot must be future and between 5 and 240 minutes.", 422)
    if session.scalar(
        select(ScheduleSlot.id)
        .where(
            ScheduleSlot.workspace_id == wid,
            ScheduleSlot.host_id == actor,
            ScheduleSlot.starts_at < end,
            ScheduleSlot.ends_at > start,
        )
        .limit(1)
    ):
        fail("HOST_OVERLAP")
    row = ScheduleSlot(
        workspace_id=wid,
        version_id=body.version_id,
        host_id=actor,
        starts_at=start,
        ends_at=end,
        timezone=body.timezone,
        capacity=body.capacity,
        join_url=body.join_url,
    )
    session.add(row)
    session.flush()
    return slot_json(row, True)


def list_slots(session, wid, actor, vid, staff=False):
    if staff:
        staff_version(session, wid, actor, vid, "read")
    else:
        participant_version(session, wid, actor, vid)
    return [
        slot_json(s, staff)
        for s in session.scalars(
            select(ScheduleSlot)
            .where(
                ScheduleSlot.workspace_id == wid,
                ScheduleSlot.version_id == vid,
                ScheduleSlot.starts_at > utcnow(),
            )
            .order_by(ScheduleSlot.starts_at, ScheduleSlot.id)
            .limit(200)
        )
    ]


def booking_json(session, row):
    slot = session.get(ScheduleSlot, row.slot_id)
    private = row.state == "booked" and consent_granted(
        session, row.workspace_id, row.subject_id, "study", study_version_id=slot.version_id
    )
    if private:
        try:
            participant_version(session, row.workspace_id, row.subject_id, slot.version_id)
            staff_version(session, row.workspace_id, slot.host_id, slot.version_id, "edit")
        except DomainError:
            private = False
    return {
        "id": row.id,
        "slot": slot_json(slot, private),
        "state": row.state,
        "revision": row.revision,
        "attendance": row.attendance,
    }


def capacity(session, slot, actor, exclude=None):
    if slot.starts_at <= utcnow():
        fail("SLOT_CLOSED")
    count = session.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.slot_id == slot.id, Booking.state == "booked", Booking.id != exclude)
    )
    if count >= slot.capacity:
        fail("SLOT_FULL")
    overlap = (
        select(Booking.id)
        .join(ScheduleSlot, ScheduleSlot.id == Booking.slot_id)
        .where(
            Booking.subject_id == actor,
            Booking.state == "booked",
            Booking.id != exclude,
            ScheduleSlot.starts_at < slot.ends_at,
            ScheduleSlot.ends_at > slot.starts_at,
        )
    )
    if session.scalar(overlap.limit(1)):
        fail("PARTICIPANT_OVERLAP")


def remind(session, row, requester):
    from app.jobs.service import enqueue

    slot = session.get(ScheduleSlot, row.slot_id)
    note = Notification(
        workspace_id=row.workspace_id, booking_id=row.id, booking_revision=row.revision
    )
    session.add(note)
    session.flush()
    job = enqueue(
        session,
        workspace_id=row.workspace_id,
        requester_id=requester,
        command_key=f"reminder:{row.id}:{row.revision}",
        kind="longitudinal.reminder",
        target_id=note.id,
        run_after=max(utcnow(), slot.starts_at - timedelta(hours=24)),
        internal=True,
    )
    note.job_id = job.id


def lock_participant_booking(session, actor):
    # Global participant namespace BEFORE workspace locks; never acquire user row
    # locks here (other commands acquire workspace then user locks).
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": "longitudinal.booking:" + str(actor)},
    )


def book(session, actor, body):
    lock_participant_booking(session, actor)
    hint = session.get(ScheduleSlot, body.slot_id)
    if not hint:
        fail("NOT_FOUND", "Slot not found.", 404)
    lock_workspace(session, hint.workspace_id)
    slot = session.get(ScheduleSlot, body.slot_id)
    participant_version(session, slot.workspace_id, actor, slot.version_id)
    prior = session.scalar(
        select(Booking).where(Booking.subject_id == actor, Booking.request_key == body.request_key)
    )
    if prior:
        if prior.slot_id != slot.id:
            fail("IDEMPOTENCY_CONFLICT")
        return booking_json(session, prior)
    capacity(session, slot, actor)
    row = Booking(
        workspace_id=slot.workspace_id,
        slot_id=slot.id,
        subject_id=actor,
        request_key=body.request_key,
    )
    session.add(row)
    session.flush()
    remind(session, row, actor)
    return booking_json(session, row)


def owned_booking(session, actor, bid):
    lock_participant_booking(session, actor)
    row = session.get(Booking, bid)
    if not row or row.subject_id != actor:
        fail("NOT_FOUND", "Booking not found.", 404)
    lock_workspace(session, row.workspace_id)
    session.refresh(row)
    slot = session.get(ScheduleSlot, row.slot_id)
    participant_version(session, row.workspace_id, actor, slot.version_id)
    return row


def change_booking(session, actor, bid, body, cancel=False):
    row = owned_booking(session, actor, bid)
    if row.revision != body.expected_revision:
        fail("REVISION_CONFLICT")
    old = session.get(ScheduleSlot, row.slot_id)
    if row.state != "booked" or old.starts_at <= utcnow():
        fail("BOOKING_CLOSED")
    if cancel:
        row.state = "cancelled"
    else:
        slot = get_scoped(session, ScheduleSlot, row.workspace_id, body.slot_id)
        if slot.version_id != old.version_id:
            fail("VERSION_MISMATCH")
        capacity(session, slot, actor, row.id)
        row.slot_id = slot.id
    row.revision += 1
    session.flush()
    if not cancel:
        remind(session, row, actor)
    return booking_json(session, row)


def attendance(session, wid, actor, bid, body):
    lock_workspace(session, wid)
    row = get_scoped(session, Booking, wid, bid)
    slot = session.get(ScheduleSlot, row.slot_id)
    staff_version(session, wid, actor, slot.version_id)
    if row.revision != body.expected_revision:
        fail("REVISION_CONFLICT")
    if row.state != "booked" or slot.starts_at > utcnow():
        fail("ATTENDANCE_NOT_AVAILABLE")
    row.attendance = body.attendance
    row.attendance_note = body.note
    row.attendance_actor_id = actor
    row.attendance_at = utcnow()
    row.revision += 1
    session.flush()
    return booking_json(session, row)


def reminder_job_allowed(session, job):
    from app.auth.models import User

    workspace = lock_workspace(session, job.workspace_id)
    from app.collaboration.service import notification_allowed

    if not notification_allowed(session, job.workspace_id, job.requester_id, "reminder"):
        return False
    if workspace.status != "active" or workspace.privacy_epoch != job.privacy_epoch:
        return False
    note = session.get(Notification, job.target_id)
    if note:
        session.refresh(note)
    if not note or note.workspace_id != job.workspace_id or note.delivered_at:
        return False
    row = session.get(Booking, note.booking_id)
    if row:
        session.refresh(row)
    if row and row.subject_id != job.requester_id:
        return False
    if not row or row.state != "booked" or row.revision != note.booking_revision:
        return False
    slot = session.get(ScheduleSlot, row.slot_id)
    if slot.starts_at <= utcnow():
        return False
    try:
        for uid in (row.subject_id, slot.host_id):
            user = session.get(User, uid)
            if not user or user.status != "active" or not user.verified_at:
                return False
        staff_version(session, slot.workspace_id, slot.host_id, slot.version_id, "edit")
        participant_version(session, row.workspace_id, row.subject_id, slot.version_id)
    except DomainError:
        return False
    return True


def finish_reminder(session, job):
    if not reminder_job_allowed(session, job):
        fail("REMINDER_REVOKED")
    session.get(Notification, job.target_id).delivered_at = utcnow()


def create_diary(session, wid, actor, body):
    lock_workspace(session, wid)
    base = get_scoped(session, CollectionSession, wid, body.base_session_id)
    version = staff_version(session, wid, actor, base.version_id)
    if any(
        b["type"] not in {"survey.single", "survey.multi", "survey.rating", "survey.text"}
        for b in version.blocks_json
    ):
        fail("DIARY_PROMPTS_UNSUPPORTED", "Diary v1 supports only core survey prompts.", 422)
    from app.reviews.models import ReviewCase

    if session.scalar(
        select(ReviewCase.id).where(
            ReviewCase.session_id == base.id, ReviewCase.state == "accepted"
        )
    ):
        fail("DIARY_TERMS_FROZEN")
    if base.diary_occurrence_id or base.state in {"withdrawn", "erased"}:
        fail("INVALID_BASE_SESSION")
    windows = [
        (
            local_utc(w.opens, body.timezone),
            local_utc(w.due, body.timezone),
            local_utc(w.grace, body.timezone),
        )
        for w in body.windows
    ]
    dates = [w.opens.local.date() for w in body.windows]
    if len(set(dates)) != len(dates) or (max(dates) - min(dates)).days >= 90:
        fail("INVALID_DIARY_DATES", "Use unique dates within 90 days.", 422)
    for i, (opens, due, grace) in enumerate(windows):
        if (
            not opens < due <= grace
            or not timedelta(minutes=1) <= due - opens <= timedelta(days=1)
            or grace - due > timedelta(days=1)
            or (i and opens < windows[i - 1][2])
        ):
            fail(
                "INVALID_DIARY_WINDOW", "Windows must be ordered, nonoverlapping and bounded.", 422
            )
    existing = list(
        session.scalars(
            select(DiaryOccurrence)
            .where(DiaryOccurrence.base_session_id == base.id)
            .order_by(DiaryOccurrence.ordinal)
        )
    )
    if existing:
        if [(r.opens_at, r.due_at, r.grace_at) for r in existing] != windows or existing[
            0
        ].timezone != body.timezone:
            fail("DIARY_IMMUTABLE")
        return [occurrence_json(session, r) for r in existing]
    rows = []
    dates = [w.opens.local.date() for w in body.windows]
    if len(set(dates)) != len(dates) or (max(dates) - min(dates)).days >= 90:
        fail("INVALID_DIARY_DATES", "Use unique dates within 90 days.", 422)
    for i, (opens, due, grace) in enumerate(windows):
        row = DiaryOccurrence(
            workspace_id=wid,
            base_session_id=base.id,
            ordinal=i,
            opens_at=opens,
            due_at=due,
            grace_at=grace,
            timezone=body.timezone,
        )
        session.add(row)
        rows.append(row)
    session.flush()
    return [occurrence_json(session, r) for r in rows]


def occurrence_json(session, row):
    child = session.scalar(
        select(CollectionSession).where(CollectionSession.diary_occurrence_id == row.id)
    )
    now = utcnow()
    state = (
        "submitted"
        if child and child.state == "submitted"
        else "early"
        if now < row.opens_at
        else "missed"
        if now >= row.grace_at
        else "grace"
        if now >= row.due_at
        else "open"
    )
    return {
        "id": row.id,
        "base_session_id": row.base_session_id,
        "ordinal": row.ordinal,
        "opens_at": row.opens_at,
        "due_at": row.due_at,
        "grace_at": row.grace_at,
        "timezone": row.timezone,
        "state": state,
        "session_id": child.id if child else None,
        "late": bool(child and child.submitted_at and child.submitted_at >= row.due_at),
    }


def start_diary(session, actor, oid, body):
    from app.collection.service import authorize as authorize_session
    from app.collection.service import resume, server_event

    occurrence = session.get(DiaryOccurrence, oid)
    if not occurrence:
        fail("NOT_FOUND", "Occurrence not found.", 404)
    lock_workspace(session, occurrence.workspace_id)
    base = session.get(CollectionSession, occurrence.base_session_id)
    if base.subject_id != actor:
        fail("NOT_FOUND", "Occurrence not found.", 404)
    participant_version(session, base.workspace_id, actor, base.version_id)
    child = session.scalar(
        select(CollectionSession).where(CollectionSession.diary_occurrence_id == oid)
    )
    if child:
        return resume(session, authorize_session(session, child.id, body.capability))
    if not occurrence.opens_at <= utcnow() < occurrence.grace_at:
        fail("DIARY_WINDOW_CLOSED")
    if base.state != "submitted":
        fail("BASE_SESSION_REQUIRED", "Complete initial participation first.")
    child = CollectionSession(
        workspace_id=base.workspace_id,
        candidate_id=base.candidate_id,
        subject_id=actor,
        version_id=base.version_id,
        launch_id=base.launch_id,
        consent_receipt_id=base.consent_receipt_id,
        capability_hash=digest(body.capability),
        start_hash=digest({"occurrence": str(oid), "capability": body.capability}),
        locale=base.locale,
        expires_at=occurrence.grace_at,
        assignments=base.assignments.copy(),
        diary_occurrence_id=oid,
    )
    session.add(child)
    session.flush()
    from app.billing.service import reserve_response

    reserve_response(session, child.workspace_id, child.id)
    server_event(session, child, "session.started")
    return resume(session, child)


def diary_reward_source(session, row):
    """One series reward identity, only once every required occurrence is submitted."""
    if row.diary_occurrence_id:
        occurrence = session.get(DiaryOccurrence, row.diary_occurrence_id)
        base_id = occurrence.base_session_id
    else:
        base_id = row.id
    occurrences = list(
        session.scalars(
            select(DiaryOccurrence)
            .where(DiaryOccurrence.base_session_id == base_id)
            .order_by(DiaryOccurrence.ordinal)
        )
    )
    if not occurrences:
        return str(row.id)
    from app.reviews.models import ReviewCase

    if not session.scalar(
        select(ReviewCase.id).where(
            ReviewCase.session_id == base_id, ReviewCase.state == "accepted"
        )
    ):
        return None
    for occurrence in occurrences:
        child = session.scalar(
            select(CollectionSession).where(CollectionSession.diary_occurrence_id == occurrence.id)
        )
        if (
            not child
            or child.state != "submitted"
            or not session.scalar(
                select(ReviewCase.id).where(
                    ReviewCase.session_id == child.id, ReviewCase.state == "accepted"
                )
            )
        ):
            return None
    return str(base_id)


def reward_allowed(session, row):
    return diary_reward_source(session, row) is not None


def recording_allowed(session, asset):
    recording = session.scalar(select(Recording).where(Recording.asset_id == asset.id))
    if recording is None:
        return True  # Existing unbound staff upload lifecycle.
    return bool(
        recording
        and not recording.revoked
        and consent_granted(session, asset.workspace_id, asset.owner_id, "recording")
        and consent_granted(
            session,
            asset.workspace_id,
            recording.subject_id,
            "recording",
            study_version_id=recording.version_id,
        )
        and consent_granted(
            session,
            asset.workspace_id,
            recording.subject_id,
            "study",
            study_version_id=recording.version_id,
        )
    )


def create_recording(session, wid, actor, body):
    from app.auth.service import require_workspace

    lock_workspace(session, wid)
    staff_version(session, wid, actor, body.version_id)
    participant_version(session, wid, body.subject_id, body.version_id)
    asset = get_scoped(session, Asset, wid, body.asset_id)
    member = require_workspace(session, actor, wid, "workspace.read")
    if asset.owner_id != actor and member.role not in {"owner", "admin"}:
        fail("NOT_FOUND", "Asset not found.", 404)
    if (
        asset.purpose != "recording"
        or asset.state != "ready"
        or asset.retention_until <= utcnow()
        or not asset.duration_ms
    ):
        fail("RECORDING_ASSET_REQUIRED")
    receipt = get_scoped(session, ConsentReceipt, wid, body.consent_receipt_id)
    doc = session.get(ConsentDocument, receipt.document_id)
    if (
        receipt.subject_id != body.subject_id
        or receipt.study_version_id != body.version_id
        or receipt.decision != "granted"
        or doc.purpose != "recording"
    ):
        fail("RECORDING_CONSENT_REQUIRED")
    if not consent_granted(
        session, wid, body.subject_id, "recording", study_version_id=body.version_id
    ) or not consent_granted(session, wid, asset.owner_id, "recording"):
        fail("RECORDING_CONSENT_REQUIRED")
    prior = session.scalar(select(Recording).where(Recording.asset_id == asset.id))
    if prior:
        if (
            prior.subject_id != body.subject_id
            or prior.version_id != body.version_id
            or prior.consent_receipt_id != receipt.id
        ):
            fail("RECORDING_IMMUTABLE")
        return recording_json(session, prior)
    row = Recording(
        workspace_id=wid,
        asset_id=asset.id,
        version_id=body.version_id,
        subject_id=body.subject_id,
        consent_receipt_id=receipt.id,
        duration_ms=asset.duration_ms,
    )
    session.add(row)
    session.flush()
    return recording_json(session, row)


def recording_json(session, row):
    asset = session.get(Asset, row.asset_id)
    if not recording_allowed(session, asset):
        fail("RECORDING_REVOKED", "Recording permission unavailable.", 403)
    segments = list(
        session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.recording_id == row.id)
            .order_by(TranscriptSegment.ordinal)
        )
    )
    return {
        "id": row.id,
        "asset_id": row.asset_id,
        "version_id": row.version_id,
        "subject_id": row.subject_id,
        "duration_ms": row.duration_ms,
        "transcript_hash": row.transcript_hash,
        "segments": [
            {
                "ordinal": s.ordinal,
                "start_ms": s.start_ms,
                "end_ms": s.end_ms,
                "speaker": s.speaker,
                "text": s.text,
            }
            for s in segments
        ],
    }


def get_recording(session, wid, actor, rid):
    row = get_scoped(session, Recording, wid, rid)
    staff_version(session, wid, actor, row.version_id, "raw")
    return recording_json(session, row)


def import_transcript(session, wid, actor, rid, body):
    lock_workspace(session, wid)
    row = get_scoped(session, Recording, wid, rid)
    staff_version(session, wid, actor, row.version_id, "raw")
    recording_json(session, row)
    payload = body.model_dump(mode="json")
    checksum = digest(payload)
    if row.transcript_hash:
        if row.transcript_hash != checksum:
            fail("TRANSCRIPT_IMMUTABLE")
        return recording_json(session, row)
    segments = (
        [s.model_dump() for s in body.segments]
        if body.segments
        else [{"start_ms": 0, "end_ms": row.duration_ms, "speaker": "unknown", "text": body.text}]
    )
    end = 0
    for segment in segments:
        if not end <= segment["start_ms"] < segment["end_ms"] <= row.duration_ms:
            fail(
                "INVALID_TRANSCRIPT_SPAN",
                "Segments must be ordered, nonoverlapping and within the recording.",
                422,
            )
        end = segment["end_ms"]
    for i, s in enumerate(segments):
        session.add(TranscriptSegment(workspace_id=wid, recording_id=row.id, ordinal=i, **s))
    row.transcript_hash = checksum
    session.flush()
    return recording_json(session, row)


def recording_assets(session, wid, subject):
    return list(
        session.scalars(
            select(Asset)
            .join(Recording, Recording.asset_id == Asset.id)
            .where(Recording.workspace_id == wid, Recording.subject_id == subject)
        )
    )


def recording_revoke(session, wid, subject, version):
    query = select(Recording).where(Recording.workspace_id == wid, Recording.subject_id == subject)
    if version is not None:
        query = query.where(Recording.version_id == version)
    for row in session.scalars(query):
        row.revoked = True
        from app.privacy_ops.service import held

        if not held(session, wid, subject):
            session.execute(
                delete(TranscriptSegment).where(TranscriptSegment.recording_id == row.id)
            )
        asset = session.get(Asset, row.asset_id)
        if asset.state not in {"purged", "purging"}:
            asset.state = "blocked"
        for link in session.scalars(select(AssetLink).where(AssetLink.asset_id == asset.id)):
            link.revoked_at = utcnow()


def purge_sessions(session, wid, ids):
    # Subject erasure retains minimal immutable schedule shells. Owner deletion
    # cascades base -> occurrences -> child sessions after collection facts purge.
    return None


def purge_subject(session, wid, subject):
    recording_revoke(session, wid, subject, None)
    session.execute(
        delete(Recording).where(Recording.workspace_id == wid, Recording.subject_id == subject)
    )
    bids = session.scalars(
        select(Booking.id).where(Booking.workspace_id == wid, Booking.subject_id == subject)
    ).all()
    session.execute(delete(Notification).where(Notification.booking_id.in_(bids)))
    session.execute(delete(Booking).where(Booking.id.in_(bids)))


def purge_studies(session, wid, study_ids):
    vids = session.scalars(
        select(StudyVersion.id).where(
            StudyVersion.workspace_id == wid, StudyVersion.study_id.in_(study_ids)
        )
    ).all()
    for row in session.scalars(
        select(Recording).where(Recording.workspace_id == wid, Recording.version_id.in_(vids))
    ):
        recording_revoke(session, wid, row.subject_id, row.version_id)
    session.execute(
        delete(Recording).where(Recording.workspace_id == wid, Recording.version_id.in_(vids))
    )
    slots = session.scalars(
        select(ScheduleSlot.id).where(
            ScheduleSlot.workspace_id == wid, ScheduleSlot.version_id.in_(vids)
        )
    ).all()
    bids = session.scalars(select(Booking.id).where(Booking.slot_id.in_(slots))).all()
    session.execute(delete(Notification).where(Notification.booking_id.in_(bids)))
    session.execute(delete(Booking).where(Booking.id.in_(bids)))
    session.execute(delete(ScheduleSlot).where(ScheduleSlot.id.in_(slots)))
    ids = session.scalars(
        select(CollectionSession.id).where(
            CollectionSession.workspace_id == wid, CollectionSession.version_id.in_(vids)
        )
    ).all()
    purge_sessions(session, wid, ids)


def subject_data(session, wid, subject, limit=100, offset=0):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    bookings = session.scalars(
        select(Booking)
        .where(Booking.workspace_id == wid, Booking.subject_id == subject)
        .order_by(Booking.id)
        .limit(limit)
        .offset(offset)
    )
    recordings = session.scalars(
        select(Recording)
        .where(Recording.workspace_id == wid, Recording.subject_id == subject)
        .order_by(Recording.id)
        .limit(limit)
        .offset(offset)
    )
    return {
        "bookings": [booking_json(session, b) for b in bookings],
        "recordings": [
            {"id": r.id, "version_id": r.version_id, "asset_id": r.asset_id, "revoked": r.revoked}
            for r in recordings
        ],
    }


def export_summary(session, wid, subject):
    return subject_data(session, wid, subject)


def metrics(session, wid, actor, vid):
    """Descriptive version-bound denominators, never inferred attendance."""
    staff_version(session, wid, actor, vid, "raw")
    now = utcnow()
    booking_rows = session.execute(
        select(Booking.attendance, func.count())
        .join(ScheduleSlot, ScheduleSlot.id == Booking.slot_id)
        .where(
            Booking.workspace_id == wid,
            ScheduleSlot.version_id == vid,
            Booking.state == "booked",
            ScheduleSlot.ends_at <= now,
        )
        .group_by(Booking.attendance)
    ).all()
    attendance = dict(booking_rows)
    due_query = (
        select(DiaryOccurrence.id)
        .join(CollectionSession, CollectionSession.id == DiaryOccurrence.base_session_id)
        .where(
            DiaryOccurrence.workspace_id == wid,
            CollectionSession.version_id == vid,
            CollectionSession.state.notin_(["withdrawn", "erased"]),
            DiaryOccurrence.due_at <= now,
        )
    )
    due_ids = due_query.subquery()
    due = session.scalar(select(func.count()).select_from(due_ids))
    submitted = session.scalar(
        select(func.count())
        .select_from(CollectionSession)
        .where(
            CollectionSession.diary_occurrence_id.in_(select(due_ids.c.id)),
            CollectionSession.state == "submitted",
        )
    )
    late = session.scalar(
        select(func.count())
        .select_from(CollectionSession)
        .join(DiaryOccurrence, DiaryOccurrence.id == CollectionSession.diary_occurrence_id)
        .where(
            DiaryOccurrence.id.in_(select(due_ids.c.id)),
            CollectionSession.state == "submitted",
            CollectionSession.submitted_at >= DiaryOccurrence.due_at,
        )
    )
    participants = session.scalar(
        select(func.count(func.distinct(DiaryOccurrence.base_session_id))).where(
            DiaryOccurrence.id.in_(select(due_ids.c.id))
        )
    )
    retained = session.scalar(
        select(func.count(func.distinct(DiaryOccurrence.base_session_id)))
        .join(CollectionSession, CollectionSession.diary_occurrence_id == DiaryOccurrence.id)
        .where(DiaryOccurrence.id.in_(select(due_ids.c.id)), CollectionSession.state == "submitted")
    )
    return {
        "version_id": vid,
        "as_of": now,
        "provenance": "server submitted_at; attributed staff attendance; no inference from join-link access",
        "interviews": {
            "ended_noncancelled": sum(attendance.values()),
            "attended": attendance.get("attended", 0),
            "absent": attendance.get("absent", 0),
            "unknown": attendance.get("unknown", 0),
        },
        "diary": {
            "due_occurrences": due,
            "submitted": submitted,
            "on_time": submitted - late,
            "late": late,
            "participants_with_due_occurrences": participants,
            "participants_with_any_submitted_due_occurrence": retained,
            "retention_definition": "at least one due occurrence submitted; participant denominator, not response count",
        },
    }
