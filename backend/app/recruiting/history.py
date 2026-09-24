"""Own-subject, workspace-scoped history; no cross-client quality score."""

from types import SimpleNamespace

from sqlalchemy import select

from app.collection.models import CollectionSession
from app.collection.quality import quality_job_allowed
from app.common.errors import DomainError
from app.common.privacy import lock_workspace, require_unrestricted
from app.longitudinal.models import Booking, ScheduleSlot
from app.longitudinal.service import participant_version
from app.recruiting.history_schemas import (
    AttendanceHistory,
    HistoryPage,
    HistoryWorkspace,
    PaymentHistory,
    ResponseHistory,
    RewardHistory,
)
from app.recruiting.models import Candidate
from app.recruiting.service import validate_source
from app.reviews.models import Appeal, PayoutRecord, ReviewCase, RewardRecord


def _scopes(subject_id):
    return (
        select(CollectionSession.workspace_id)
        .where(CollectionSession.subject_id == subject_id)
        .union(
            select(RewardRecord.workspace_id).where(RewardRecord.subject_id == subject_id),
            select(Booking.workspace_id).where(Booking.subject_id == subject_id),
        )
        .subquery()
    )


def _scope(session, workspace_id, subject_id, *, financial=False):
    scopes = _scopes(subject_id)
    if (
        session.scalar(select(scopes.c.workspace_id).where(scopes.c.workspace_id == workspace_id))
        is None
    ):
        raise DomainError("NOT_FOUND", "Participation history not found.", 404)
    workspace = lock_workspace(session, workspace_id)
    if not financial:
        require_unrestricted(session, workspace_id, subject_id)
        if workspace.status != "active":
            raise DomainError("NOT_FOUND", "Participation history not found.", 404)
    return workspace


def _rows(session, statement, offset, limit):
    rows = session.execute(statement.offset(offset).limit(limit + 1)).all()
    next_offset = offset + limit if len(rows) > limit and offset + limit <= 100_000 else None
    return rows[:limit], next_offset


def workspaces(session, subject_id, offset, limit):
    scopes = _scopes(subject_id)
    rows, next_offset = _rows(
        session, select(scopes.c.workspace_id).order_by(scopes.c.workspace_id), offset, limit
    )
    return HistoryPage[HistoryWorkspace](
        items=[HistoryWorkspace(workspace_id=row.workspace_id) for row in rows],
        next_offset=next_offset,
    )


def responses(session, workspace_id, subject_id, offset, limit):
    workspace = _scope(session, workspace_id, subject_id)
    rows, next_offset = _rows(
        session,
        select(CollectionSession, ReviewCase, Appeal)
        .outerjoin(ReviewCase, ReviewCase.session_id == CollectionSession.id)
        .outerjoin(Appeal, Appeal.case_id == ReviewCase.id)
        .where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.subject_id == subject_id,
            CollectionSession.state == "submitted",
        )
        .order_by(CollectionSession.created_at.desc(), CollectionSession.id),
        offset,
        limit,
    )
    items = []
    for row, case, appeal in rows:
        if not quality_job_allowed(
            session,
            SimpleNamespace(
                workspace_id=workspace_id,
                target_id=row.id,
                requester_id=subject_id,
                privacy_epoch=workspace.privacy_epoch,
            ),
        ):
            continue
        items.append(
            ResponseHistory(
                session_id=row.id,
                version_id=row.version_id,
                occurrence_id=row.diary_occurrence_id,
                locale=row.locale,
                submitted_at=row.submitted_at,
                review_state=case.state if case else "pending",
                appeal_state=appeal.state if appeal else None,
            )
        )
    return HistoryPage[ResponseHistory](items=items, next_offset=next_offset)


def rewards(session, workspace_id, subject_id, offset, limit):
    _scope(session, workspace_id, subject_id, financial=True)
    rows, next_offset = _rows(
        session,
        select(RewardRecord)
        .where(RewardRecord.workspace_id == workspace_id, RewardRecord.subject_id == subject_id)
        .order_by(RewardRecord.created_at.desc(), RewardRecord.id),
        offset,
        limit,
    )
    return HistoryPage[RewardHistory](
        items=[RewardHistory.model_validate(row) for (row,) in rows], next_offset=next_offset
    )


def payments(session, workspace_id, subject_id, reward_id, offset, limit):
    _scope(session, workspace_id, subject_id, financial=True)
    reward = session.scalar(
        select(RewardRecord).where(
            RewardRecord.workspace_id == workspace_id,
            RewardRecord.subject_id == subject_id,
            RewardRecord.id == reward_id,
        )
    )
    if reward is None:
        raise DomainError("NOT_FOUND", "Reward not found.", 404)
    rows, next_offset = _rows(
        session,
        select(PayoutRecord)
        .where(PayoutRecord.workspace_id == workspace_id, PayoutRecord.reward_id == reward_id)
        .order_by(PayoutRecord.created_at.desc(), PayoutRecord.id),
        offset,
        limit,
    )
    return HistoryPage[PaymentHistory](
        items=[PaymentHistory.model_validate(row) for (row,) in rows], next_offset=next_offset
    )


def attendance(session, workspace_id, subject_id, offset, limit):
    _scope(session, workspace_id, subject_id)
    rows, next_offset = _rows(
        session,
        select(Booking, ScheduleSlot)
        .join(ScheduleSlot, ScheduleSlot.id == Booking.slot_id)
        .where(Booking.workspace_id == workspace_id, Booking.subject_id == subject_id)
        .order_by(ScheduleSlot.starts_at.desc(), Booking.id),
        offset,
        limit,
    )
    items = []
    allowed_versions = {}
    for booking, slot in rows:
        if slot.version_id not in allowed_versions:
            try:
                participation = participant_version(
                    session, workspace_id, subject_id, slot.version_id
                )
                candidate = session.get(Candidate, participation.candidate_id)
                if candidate is None:
                    raise DomainError("NOT_FOUND", "Participation not found.", 404)
                validate_source(session, candidate)
                allowed_versions[slot.version_id] = True
            except DomainError:
                allowed_versions[slot.version_id] = False
        if not allowed_versions[slot.version_id]:
            continue
        items.append(
            AttendanceHistory(
                id=booking.id,
                version_id=slot.version_id,
                state=booking.state,
                attendance=booking.attendance,
                attendance_at=booking.attendance_at,
                starts_at=slot.starts_at,
                ends_at=slot.ends_at,
                timezone=slot.timezone,
            )
        )
    return HistoryPage[AttendanceHistory](items=items, next_offset=next_offset)
