"""Scoped privacy integration. Caller holds the workspace privacy lock."""

from sqlalchemy import delete, select

from app.auth.security import utcnow
from app.collection.models import (
    Answer,
    AnswerRevision,
    CollectionSession,
    InteractionAttempt,
    ResponseEvent,
)
from app.common.privacy_models import ConsentReceipt


def _rows(session, workspace_id, subject_id):
    return session.scalars(
        select(CollectionSession)
        .where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.subject_id == subject_id,
        )
        .order_by(CollectionSession.id)
        .with_for_update()
    ).all()


def withdraw_session(session, row):
    """A session capability revokes only its own participation."""
    if row.state in {"withdrawn", "erased"}:
        return False
    workspace_id, subject_id = row.workspace_id, row.subject_id
    original = session.get(ConsentReceipt, row.consent_receipt_id)
    session.add(
        ConsentReceipt(
            workspace_id=workspace_id,
            subject_id=subject_id,
            document_id=original.document_id,
            study_version_id=row.version_id,
            receipt_key="collection.withdraw:" + str(row.id),
            decision="withdrawn",
            presented_digest=original.presented_digest,
            created_at=utcnow(),
        )
    )
    from app.privacy_ops.events import record_event

    record_event(session, workspace_id, "session_withdraw", row.id)
    row.state = "withdrawn"
    from app.privacy_ops.service import held

    if not held(session, workspace_id, subject_id):
        row.quality_summary = None
    from app.billing.service import release_response

    release_response(session, workspace_id, row.id)
    from app.ai.service import invalidate_sessions
    from app.analytics.service import invalidate_session

    invalidate_sessions(session, workspace_id, [row.id])
    invalidate_session(session, workspace_id, row.id)
    from app.recruiting.models import Reservation

    reservation = session.scalar(
        select(Reservation).where(Reservation.candidate_id == row.candidate_id)
    )
    if reservation and reservation.state == "held":
        reservation.state = "released"
    session.flush()
    return True


def withdraw_subject(session, workspace_id, subject_id):
    rows = _rows(session, workspace_id, subject_id)
    for row in rows:
        withdraw_session(session, row)
    return len(rows)


def purge_subject(session, workspace_id, subject_id):
    withdraw_subject(session, workspace_id, subject_id)
    rows = _rows(session, workspace_id, subject_id)
    from app.analytics.service import purge_sessions as purge_analytics
    from app.reviews.privacy import purge_sessions as purge_reviews

    session_ids = [row.id for row in rows]
    from app.ai.service import invalidate_sessions

    invalidate_sessions(session, workspace_id, session_ids)
    purge_analytics(session, workspace_id, session_ids)
    purge_reviews(session, workspace_id, session_ids)
    for row in rows:
        row.state = "erased"
    session.flush()
    for row in rows:
        for model in (AnswerRevision, ResponseEvent, InteractionAttempt, Answer):
            session.execute(delete(model).where(model.session_id == row.id))
        row.state, row.assignments, row.submitted_snapshot = "erased", {}, None
        row.consent_receipt_id = None
        row.quality_summary = None
    session.flush()
    return len(rows)


def purge_launches(session, workspace_id, launch_ids):
    rows = session.scalars(
        select(CollectionSession)
        .where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.launch_id.in_(launch_ids),
        )
        .with_for_update()
    ).all()
    from app.analytics.service import purge_sessions as purge_analytics
    from app.reviews.privacy import purge_sessions as purge_reviews

    session_ids = [row.id for row in rows]
    from app.ai.service import invalidate_sessions

    invalidate_sessions(session, workspace_id, session_ids)
    purge_analytics(session, workspace_id, session_ids)
    purge_reviews(session, workspace_id, session_ids)
    for row in rows:
        row.state = "erased"
    session.flush()
    for row in rows:
        for model in (AnswerRevision, ResponseEvent, InteractionAttempt, Answer):
            session.execute(delete(model).where(model.session_id == row.id))
    # Diary base deletion cascades to occurrences and their child sessions. Remove
    # every dependent response first, then delete children before their base.
    for row in sorted(rows, key=lambda item: item.diary_occurrence_id is None):
        session.delete(row)
        session.flush()
    session.flush()


def subject_data(session, workspace_id, subject_id, limit=100, offset=0, detail_offset=0):
    from app.collection.service import resume

    rows = session.scalars(
        select(CollectionSession)
        .where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.subject_id == subject_id,
        )
        .order_by(CollectionSession.id)
        .limit(min(limit, 100))
        .offset(offset)
    ).all()
    return [
        {
            "session": resume(session, row),
            "revisions": [
                {
                    "block_key": answer.block_key,
                    "revision": revision.revision,
                    "answer": revision.payload,
                }
                for revision, answer in session.execute(
                    select(AnswerRevision, Answer)
                    .join(Answer, Answer.id == AnswerRevision.answer_id)
                    .where(Answer.session_id == row.id)
                    .order_by(Answer.block_key, AnswerRevision.revision)
                    .limit(1000)
                    .offset(max(0, detail_offset))
                )
            ],
            "events": [
                {
                    "block_key": event.block_key,
                    "kind": event.kind,
                    "payload": event.payload,
                    "provenance": event.provenance,
                    "received_at": event.received_at.isoformat(),
                }
                for event in session.scalars(
                    select(ResponseEvent)
                    .where(ResponseEvent.session_id == row.id)
                    .order_by(ResponseEvent.received_at)
                    .limit(1000)
                    .offset(max(0, detail_offset))
                )
            ],
            "detail_limit": 1000,
            "detail_offset": max(0, detail_offset),
        }
        for row in rows
    ]
