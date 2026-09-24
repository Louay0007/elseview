"""Privacy hooks: research details erase; earned obligations never disappear."""

from datetime import timedelta

from sqlalchemy import delete, func, select, text

from app.auth.security import utcnow
from app.collection.models import CollectionSession
from app.reviews.models import FinancialRetentionPolicy, ReviewCase, RewardRecord


def purge_sessions(session, workspace_id, session_ids):
    # Cascading deletion removes flags, rationales, assignments and appeals.
    result = session.execute(
        delete(ReviewCase).where(
            ReviewCase.workspace_id == workspace_id, ReviewCase.session_id.in_(session_ids)
        )
    )
    return result.rowcount


def purge_subject(session, workspace_id, subject_id):
    ids = session.scalars(
        select(CollectionSession.id).where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.subject_id == subject_id,
        )
    ).all()
    count = purge_sessions(session, workspace_id, ids)
    minimize_financial(session, workspace_id, subject_id)
    return count


def minimize_financial(session, workspace_id, subject_id=None, limit=100):
    """Only unlink identity after full settlement AND reviewed policy interval.

    No implied legal duration. Outstanding/reversed obligations retain their
    beneficiary identifier to allow reconciliation and participant access.
    Journal and non-sensitive amounts remain immutable.
    """
    from app.common.privacy import lock_workspace
    from app.privacy_ops.service import held

    lock_workspace(session, workspace_id)
    query = (
        select(RewardRecord)
        .join(
            FinancialRetentionPolicy,
            FinancialRetentionPolicy.id == RewardRecord.retention_policy_id,
        )
        .where(
            RewardRecord.workspace_id == workspace_id,
            RewardRecord.state == "paid",
            RewardRecord.subject_id.is_not(None),
            RewardRecord.settled_at
            + FinancialRetentionPolicy.settled_days * text("interval '1 day'")
            <= func.now(),
        )
    )
    if subject_id is not None:
        query = query.where(RewardRecord.subject_id == subject_id)
    count = 0
    for reward in session.scalars(
        query.order_by(RewardRecord.id)
        .limit(min(100, max(1, limit)))
        .with_for_update(of=RewardRecord)
    ):
        if held(session, workspace_id, reward.subject_id):
            continue
        policy = session.get(FinancialRetentionPolicy, reward.retention_policy_id)
        if (
            reward.settled_at
            and reward.settled_at + timedelta(days=policy.settled_days) <= utcnow()
        ):
            reward.subject_id = None
            count += 1
    session.flush()
    return count


def subject_financial_data(session, workspace_id, subject_id, limit=100, offset=0):
    """Minimal own access intentionally does not require live study consent."""
    return [
        {
            "id": str(r.id),
            "amount_millimes": r.amount_millimes,
            "currency": r.currency,
            "state": r.state,
            "settled_at": r.settled_at,
        }
        for r in session.scalars(
            select(RewardRecord)
            .where(RewardRecord.workspace_id == workspace_id, RewardRecord.subject_id == subject_id)
            .order_by(RewardRecord.id)
            .offset(max(0, offset))
            .limit(min(100, max(1, limit)))
        )
    ]
