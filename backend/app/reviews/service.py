"""Serialized review commands and accounting; callers own the transaction."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.auth.security import utcnow
from app.auth.service import require_workspace
from app.collection.models import CollectionSession
from app.common.errors import DomainError
from app.common.privacy import lock_workspace, require_unrestricted
from app.recruiting.models import Reservation
from app.reviews.models import (
    Appeal,
    FinancialRetentionPolicy,
    LedgerAccount,
    LedgerEntry,
    LedgerTransaction,
    PayoutRecord,
    QualityFlag,
    ReviewAssignment,
    ReviewCase,
    ReviewDecision,
    RewardRecord,
)
from app.studies.models import StudyVersion
from app.studies.service import authorize

MAX_MONEY = 1_000_000_000_000


def fail(code="REVIEW_CONFLICT", status=409):
    raise DomainError(code, "Review or financial command is unavailable.", status)


def money(amount, currency="TND"):
    if type(amount) is not int or not 0 < amount <= MAX_MONEY or currency != "TND":
        fail("INVALID_MONEY", 422)


def row_for(session, workspace_id, session_id, actor_id=None, capability="review"):
    lock_workspace(session, workspace_id)
    row = session.scalar(
        select(CollectionSession)
        .where(CollectionSession.workspace_id == workspace_id, CollectionSession.id == session_id)
        .with_for_update()
    )
    if not row or row.state != "submitted":
        fail("NOT_FOUND", 404)
    require_unrestricted(session, workspace_id, row.subject_id)
    # Reuse the same live source/consent check as P07 (not merely session state).
    from types import SimpleNamespace

    from app.auth.models import Workspace
    from app.collection.quality import quality_job_allowed

    if not quality_job_allowed(
        session,
        SimpleNamespace(
            workspace_id=workspace_id,
            target_id=row.id,
            requester_id=row.subject_id,
            privacy_epoch=session.get(Workspace, workspace_id).privacy_epoch,
        ),
    ):
        fail("NOT_FOUND", 404)
    version = session.get(StudyVersion, row.version_id)
    if actor_id is not None:
        authorize(session, workspace_id, actor_id, version.study_id, capability)
    return row


def sync_quality(session, row):
    """Idempotent P07 quality_summary import; never decides or denies rewards."""
    if row.state != "submitted":
        return None
    session.execute(
        insert(ReviewCase)
        .values(workspace_id=row.workspace_id, session_id=row.id)
        .on_conflict_do_nothing(index_elements=["session_id"])
    )
    case = session.scalar(select(ReviewCase).where(ReviewCase.session_id == row.id))
    summary = row.quality_summary or {}
    for flag in summary.get("flags", []):
        session.execute(
            insert(QualityFlag)
            .values(
                workspace_id=row.workspace_id,
                case_id=case.id,
                policy=summary.get("policy", "p07_deterministic_v1"),
                block_key=flag["block_key"],
                code=flag["code"],
            )
            .on_conflict_do_nothing()
        )
    return case


def accepted_decision_snapshot(session, workspace_id, session_id):
    case = session.scalar(
        select(ReviewCase)
        .where(ReviewCase.workspace_id == workspace_id, ReviewCase.session_id == session_id)
        .execution_options(populate_existing=True)
    )
    row = session.get(CollectionSession, session_id)
    if not case or case.state != "accepted" or not row or row.state != "submitted":
        return None
    return {
        "decision_id": str(case.final_decision_id),
        "accepted_at": case.accepted_at,
        "version": case.generation,
    }


def accepted_state(session, workspace_id, session_ids):
    return dict(
        session.execute(
            select(ReviewCase.session_id, ReviewCase.generation).where(
                ReviewCase.workspace_id == workspace_id,
                ReviewCase.session_id.in_(session_ids),
                ReviewCase.state == "accepted",
            )
        ).all()
    )


def assign(session, workspace_id, actor_id, session_id, reviewer_id, kind):
    row = row_for(session, workspace_id, session_id, actor_id, "grants")
    version = session.get(StudyVersion, row.version_id)
    authorize(session, workspace_id, reviewer_id, version.study_id, "review")
    if reviewer_id == row.subject_id:
        fail("SELF_REVIEW", 403)
    case = sync_quality(session, row)
    assignments = session.scalars(
        select(ReviewAssignment).where(ReviewAssignment.case_id == case.id)
    ).all()
    for previous in assignments:
        if previous.reviewer_id == reviewer_id:
            if previous.kind == kind:
                return previous
            fail("INDEPENDENT_REVIEW_REQUIRED")
    valid = (
        (kind == "independent" and case.state == "pending" and len(assignments) < 2)
        or (kind == "adjudication" and case.state == "disputed")
        or (kind == "appeal" and case.state == "appealed")
    )
    if not valid or any(a.kind == kind for a in assignments) and kind != "independent":
        fail()
    assignment = ReviewAssignment(
        workspace_id=workspace_id,
        case_id=case.id,
        reviewer_id=reviewer_id,
        round=len(assignments) + 1,
        kind=kind,
    )
    session.add(assignment)
    session.flush()
    return assignment


def decide(session, workspace_id, actor_id, assignment_id, body):
    lock_workspace(session, workspace_id)
    assignment = session.scalar(
        select(ReviewAssignment).where(
            ReviewAssignment.workspace_id == workspace_id, ReviewAssignment.id == assignment_id
        )
    )
    if not assignment or assignment.reviewer_id != actor_id:
        fail("NOT_FOUND", 404)
    case = session.get(ReviewCase, assignment.case_id)
    row = row_for(session, workspace_id, case.session_id, actor_id)
    if actor_id == row.subject_id:
        fail("SELF_REVIEW", 403)
    previous = session.scalar(
        select(ReviewDecision).where(ReviewDecision.assignment_id == assignment.id)
    )
    if previous:
        if (previous.command_key, previous.verdict, previous.rationale, previous.evidence) != (
            body.command_key,
            body.verdict,
            body.rationale,
            body.evidence,
        ):
            fail("IDEMPOTENCY_CONFLICT")
        return case
    expected = {"independent": "pending", "adjudication": "disputed", "appeal": "appealed"}[
        assignment.kind
    ]
    if case.state != expected:
        fail()
    if not body.rationale.strip() or body.verdict == "rejected" and not body.evidence:
        fail("EVIDENCE_REQUIRED", 422)
    if body.verdict == "rejected":
        # Evidence names a pinned submitted block, not an ungrounded fraud label.
        keys = set((row.submitted_snapshot or {}).keys())
        if any(item.split(":", 1)[0] not in keys for item in body.evidence):
            fail("INVALID_EVIDENCE_REFERENCE", 422)
    decision = ReviewDecision(
        workspace_id=workspace_id, assignment_id=assignment.id, **body.model_dump()
    )
    session.add(decision)
    session.flush()
    if assignment.kind == "independent":
        decisions = session.scalars(
            select(ReviewDecision)
            .join(ReviewAssignment, ReviewDecision.assignment_id == ReviewAssignment.id)
            .where(ReviewAssignment.case_id == case.id, ReviewAssignment.kind == "independent")
        ).all()
        if len(decisions) < 2:
            case.generation += 1
            return case
        case.state = body.verdict if len({d.verdict for d in decisions}) == 1 else "disputed"
    else:
        if assignment.kind == "appeal":
            appeal = session.scalar(select(Appeal).where(Appeal.case_id == case.id))
            appeal.state = "overturned" if body.verdict == "accepted" else "upheld"
        case.state = body.verdict
    case.generation += 1
    case.final_decision_id = decision.id
    if case.state == "accepted":
        case.accepted_at = utcnow()
        earn(session, row)
    session.flush()
    return case


def appeal(session, workspace_id, subject_id, session_id, body):
    row = row_for(session, workspace_id, session_id)
    if row.subject_id != subject_id:
        fail("NOT_FOUND", 404)
    case = session.scalar(select(ReviewCase).where(ReviewCase.session_id == session_id))
    if not case:
        fail("NOT_FOUND", 404)
    old = session.scalar(select(Appeal).where(Appeal.case_id == case.id))
    if old:
        if old.command_key == body.command_key and old.reason == body.reason:
            return old
        fail("APPEAL_ALREADY_EXISTS")
    if case.state != "rejected":
        fail()
    result = Appeal(workspace_id=workspace_id, case_id=case.id, **body.model_dump())
    session.add(result)
    case.state = "appealed"
    case.generation += 1
    session.flush()
    return result


def admin(session, workspace_id, actor_id):
    lock_workspace(session, workspace_id)
    member = require_workspace(session, actor_id, workspace_id, "workspace.read")
    require_unrestricted(session, workspace_id, actor_id)
    if member.role not in {"owner", "admin"}:
        fail("FORBIDDEN", 403)


def retention_policy(session, workspace_id, actor_id, body):
    admin(session, workspace_id, actor_id)
    policy = FinancialRetentionPolicy(
        workspace_id=workspace_id, reviewed_by=actor_id, **body.model_dump()
    )
    session.add(policy)
    session.flush()
    return policy


def post(session, workspace_id, command_key, postings, reversal_of=None):
    lock_workspace(session, workspace_id)
    if (
        len(postings) < 2
        or sum(v for _, v in postings) != 0
        or any(type(v) is not int or not 0 < abs(v) <= MAX_MONEY for _, v in postings)
    ):
        fail("UNBALANCED_JOURNAL", 422)
    old = session.scalar(
        select(LedgerTransaction).where(
            LedgerTransaction.workspace_id == workspace_id,
            LedgerTransaction.command_key == command_key,
        )
    )
    if old:
        existing = session.execute(
            select(LedgerAccount.code, LedgerEntry.amount_millimes)
            .join(LedgerEntry, LedgerEntry.account_id == LedgerAccount.id)
            .where(LedgerEntry.transaction_id == old.id)
        ).all()
        if sorted(existing) != sorted(postings) or old.reversal_of != reversal_of:
            fail("IDEMPOTENCY_CONFLICT")
        return old
    transaction = LedgerTransaction(
        workspace_id=workspace_id, command_key=command_key, reversal_of=reversal_of
    )
    session.add(transaction)
    session.flush()
    for code, amount in postings:
        session.execute(
            insert(LedgerAccount)
            .values(workspace_id=workspace_id, code=code)
            .on_conflict_do_nothing()
        )
        account = session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.workspace_id == workspace_id, LedgerAccount.code == code
            )
        )
        session.add(
            LedgerEntry(
                workspace_id=workspace_id,
                transaction_id=transaction.id,
                account_id=account.id,
                amount_millimes=amount,
            )
        )
    session.flush()
    return transaction


def earn(session, row):
    from app.longitudinal.service import diary_reward_source

    source = diary_reward_source(session, row)
    if source is None:
        return None
    source_key = "accepted_v1:" + source
    old = session.scalar(
        select(RewardRecord).where(
            RewardRecord.workspace_id == row.workspace_id, RewardRecord.source_key == source_key
        )
    )
    if old:
        return old
    reservation = session.scalar(
        select(Reservation).where(
            Reservation.workspace_id == row.workspace_id,
            Reservation.candidate_id == row.candidate_id,
        )
    )
    if not reservation or not reservation.reward_millimes:
        return None
    money(reservation.reward_millimes)
    policy = session.scalar(
        select(FinancialRetentionPolicy)
        .where(FinancialRetentionPolicy.workspace_id == row.workspace_id)
        .order_by(FinancialRetentionPolicy.created_at.desc(), FinancialRetentionPolicy.id)
        .limit(1)
    )
    if not policy:
        fail("REVIEWED_FINANCIAL_RETENTION_REQUIRED")
    reward = RewardRecord(
        workspace_id=row.workspace_id,
        source_key=source_key,
        subject_id=row.subject_id,
        amount_millimes=reservation.reward_millimes,
        retention_policy_id=policy.id,
    )
    session.add(reward)
    session.flush()
    post(
        session,
        row.workspace_id,
        "earn:" + str(reward.id),
        [("expense", reward.amount_millimes), ("payable", -reward.amount_millimes)],
    )
    return reward


def payout(session, workspace_id, actor_id, reward_id, body):
    admin(session, workspace_id, actor_id)
    reward = session.scalar(
        select(RewardRecord)
        .where(RewardRecord.workspace_id == workspace_id, RewardRecord.id == reward_id)
        .with_for_update()
    )
    if not reward:
        fail("NOT_FOUND", 404)
    money(body.amount_millimes, body.currency)
    if body.amount_millimes != reward.amount_millimes:
        fail("PARTIAL_SETTLEMENT_UNSUPPORTED", 422)
    old = session.scalar(
        select(PayoutRecord).where(
            PayoutRecord.workspace_id == workspace_id, PayoutRecord.command_key == body.command_key
        )
    )
    if old:
        if (old.reward_id, old.external_reference, old.evidence, old.state == "failed") != (
            reward_id,
            body.external_reference,
            body.evidence,
            body.failed,
        ):
            fail("IDEMPOTENCY_CONFLICT")
        return old
    if reward.state != "earned":
        fail("ALREADY_SETTLED")
    if session.scalar(
        select(PayoutRecord.id).where(
            PayoutRecord.workspace_id == workspace_id,
            PayoutRecord.external_reference == body.external_reference,
        )
    ):
        fail("DUPLICATE_EXTERNAL_REFERENCE")
    tx = None
    if not body.failed:
        tx = post(
            session,
            workspace_id,
            "pay:" + str(body.command_key),
            [("payable", reward.amount_millimes), ("manual_cash", -reward.amount_millimes)],
        )
        reward.state = "paid"
        reward.settled_at = utcnow()
    result = PayoutRecord(
        workspace_id=workspace_id,
        reward_id=reward.id,
        command_key=body.command_key,
        external_reference=body.external_reference,
        evidence=body.evidence,
        state="failed" if body.failed else "recorded",
        transaction_id=tx.id if tx else None,
    )
    session.add(result)
    session.flush()
    return result


def reverse_payout(session, workspace_id, actor_id, payout_id):
    admin(session, workspace_id, actor_id)
    payout = session.scalar(
        select(PayoutRecord)
        .where(PayoutRecord.workspace_id == workspace_id, PayoutRecord.id == payout_id)
        .with_for_update()
    )
    if not payout:
        fail("NOT_FOUND", 404)
    if payout.state == "reversed":
        return payout
    if payout.state != "recorded":
        fail("FAILED_PAYMENT_HAS_NO_POSTING")
    reward = session.get(RewardRecord, payout.reward_id)
    if reward.subject_id is None:
        fail("BENEFICIARY_MINIMIZED_REVERSAL_UNAVAILABLE")
    post(
        session,
        workspace_id,
        "reverse:" + str(payout.id),
        [("payable", -reward.amount_millimes), ("manual_cash", reward.amount_millimes)],
        payout.transaction_id,
    )
    payout.state = "reversed"
    reward.state = "earned"
    reward.settled_at = None
    session.flush()
    return payout
