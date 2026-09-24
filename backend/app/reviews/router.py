from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.reviews import service
from app.reviews.models import QualityFlag, ReviewAssignment, ReviewCase, ReviewDecision
from app.reviews.privacy import subject_financial_data
from app.reviews.schemas import AppealBody, AssignmentBody, DecisionBody, PayoutBody, RetentionBody


def request_guard(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    rate_limit(request, "reviews", request.client.host if request.client else "unknown", 120)


router = APIRouter(prefix="/api/v1", tags=["reviews"], dependencies=[Depends(request_guard)])
Actor = Annotated[User, Depends(current_user)]
ROOT = "/workspaces/{workspace_id}/reviews"


def case_result(case):
    return {"id": str(case.id), "state": case.state, "generation": case.generation}


def payout_result(row):
    return {"id": str(row.id), "state": row.state, "manual_record_only": True}


@router.post(ROOT + "/sessions/{session_id}/assignments", status_code=201)
def assignment(
    workspace_id: UUID, session_id: UUID, body: AssignmentBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        row = service.assign(
            session, workspace_id, user.id, session_id, body.reviewer_id, body.kind
        )
        return {"id": str(row.id), "round": row.round, "kind": row.kind}


@router.get(ROOT + "/assignments/{assignment_id}")
def assigned_view(
    workspace_id: UUID, assignment_id: UUID, request: Request, response: Response, user: Actor
):
    response.headers["Cache-Control"] = "no-store"
    with request.app.state.database.sessions.begin() as session:
        assignment = session.scalar(
            select(ReviewAssignment).where(
                ReviewAssignment.workspace_id == workspace_id,
                ReviewAssignment.id == assignment_id,
                ReviewAssignment.reviewer_id == user.id,
            )
        )
        if not assignment:
            service.fail("NOT_FOUND", 404)
        case = session.get(ReviewCase, assignment.case_id)
        row = service.row_for(session, workspace_id, case.session_id, user.id)
        from app.collection.models import Answer, AnswerRevision

        answers = []
        for answer, revision in session.execute(
            select(Answer, AnswerRevision)
            .join(
                AnswerRevision,
                (AnswerRevision.answer_id == Answer.id)
                & (AnswerRevision.revision == Answer.final_revision),
            )
            .where(Answer.session_id == row.id, Answer.active.is_(True))
            .limit(1000)
        ):
            answers.append({"block_key": answer.block_key, "payload": revision.payload})
        result = {
            "assignment_id": str(assignment.id),
            "round": assignment.round,
            "kind": assignment.kind,
            "answers": answers,
            "flags": [
                {"code": f.code, "block_key": f.block_key, "policy": f.policy}
                for f in session.scalars(select(QualityFlag).where(QualityFlag.case_id == case.id))
            ],
        }
        # Independent reviewers cannot see prior votes, rationale or participant identity.
        if assignment.kind != "independent":
            result["prior_decisions"] = [
                {"verdict": d.verdict, "rationale": d.rationale, "evidence": d.evidence}
                for d in session.scalars(
                    select(ReviewDecision)
                    .join(ReviewAssignment, ReviewAssignment.id == ReviewDecision.assignment_id)
                    .where(ReviewAssignment.case_id == case.id)
                )
            ]
        return result


@router.post(ROOT + "/assignments/{assignment_id}/decision")
def decision(
    workspace_id: UUID, assignment_id: UUID, body: DecisionBody, request: Request, user: Actor
):
    with request.app.state.database.sessions.begin() as session:
        return case_result(service.decide(session, workspace_id, user.id, assignment_id, body))


@router.post(ROOT + "/sessions/{session_id}/appeal", status_code=201)
def appeal(workspace_id: UUID, session_id: UUID, body: AppealBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        row = service.appeal(session, workspace_id, user.id, session_id, body)
        return {"id": str(row.id), "state": row.state}


@router.post(ROOT + "/financial-retention", status_code=201)
def retention(workspace_id: UUID, body: RetentionBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        row = service.retention_policy(session, workspace_id, user.id, body)
        return {
            "id": str(row.id),
            "settled_days": row.settled_days,
            "reviewed_policy_not_legal_advice": True,
        }


@router.post(ROOT + "/rewards/{reward_id}/payments", status_code=201)
def payment(workspace_id: UUID, reward_id: UUID, body: PayoutBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return payout_result(service.payout(session, workspace_id, user.id, reward_id, body))


@router.post(ROOT + "/payments/{payout_id}/reverse")
def reversal(workspace_id: UUID, payout_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as session:
        return payout_result(service.reverse_payout(session, workspace_id, user.id, payout_id))


@router.get(ROOT + "/my-rewards")
def my_rewards(
    workspace_id: UUID, request: Request, response: Response, user: Actor, offset: int = 0
):
    response.headers["Cache-Control"] = "no-store"
    with request.app.state.database.sessions() as session:
        return {
            "items": subject_financial_data(session, workspace_id, user.id, offset=offset),
            "limit": 100,
            "offset": max(0, offset),
        }


@router.get(ROOT + "/studies/{study_id}/cases")
def case_queue(workspace_id: UUID, study_id: UUID, request: Request, user: Actor, offset: int = 0):
    from app.collection.models import CollectionSession
    from app.studies.models import StudyVersion
    from app.studies.service import authorize

    with request.app.state.database.sessions.begin() as session:
        service.lock_workspace(session, workspace_id)
        authorize(session, workspace_id, user.id, study_id, "grants")
        rows = session.scalars(
            select(CollectionSession)
            .join(StudyVersion, StudyVersion.id == CollectionSession.version_id)
            .where(
                CollectionSession.workspace_id == workspace_id,
                StudyVersion.study_id == study_id,
                CollectionSession.state == "submitted",
            )
            .order_by(CollectionSession.id)
            .offset(max(0, offset))
            .limit(100)
        ).all()
        items = []
        from app.common.errors import DomainError

        for row in rows:
            try:
                service.row_for(session, workspace_id, row.id, user.id, "grants")
            except DomainError:
                continue
            case = service.sync_quality(session, row)
            items.append(case_result(case) | {"session_id": str(row.id)})
        return {"items": items, "limit": 100, "offset": max(0, offset)}


@router.get(ROOT + "/my-assignments")
def my_assignments(workspace_id: UUID, request: Request, user: Actor, offset: int = 0):
    from app.common.errors import DomainError

    with request.app.state.database.sessions.begin() as session:
        service.lock_workspace(session, workspace_id)
        service.require_workspace(session, user.id, workspace_id, "workspace.read")
        items = []
        rows = session.scalars(
            select(ReviewAssignment)
            .where(
                ReviewAssignment.workspace_id == workspace_id,
                ReviewAssignment.reviewer_id == user.id,
            )
            .order_by(ReviewAssignment.id)
            .offset(max(0, offset))
            .limit(100)
        ).all()
        for assignment in rows:
            case = session.get(ReviewCase, assignment.case_id)
            try:
                service.row_for(session, workspace_id, case.session_id, user.id)
            except DomainError:
                continue
            own = session.scalar(
                select(ReviewDecision).where(ReviewDecision.assignment_id == assignment.id)
            )
            items.append(
                {
                    "id": str(assignment.id),
                    "round": assignment.round,
                    "kind": assignment.kind,
                    "decided": own is not None,
                }
            )
        return {"items": items, "limit": 100, "offset": max(0, offset)}


@router.get(ROOT + "/sessions/{session_id}/status")
def review_status(workspace_id: UUID, session_id: UUID, request: Request, user: Actor):
    from app.reviews.models import Appeal

    with request.app.state.database.sessions.begin() as session:
        row = service.row_for(session, workspace_id, session_id)
        if row.subject_id != user.id:
            service.row_for(session, workspace_id, session_id, user.id, "grants")
        case = session.scalar(select(ReviewCase).where(ReviewCase.session_id == session_id))
        if not case:
            return {
                "state": "pending",
                "generation": 0,
                "decisions": [],
                "disagreement_count": 0,
                "appeal": None,
            }
        decisions = session.scalars(
            select(ReviewDecision)
            .join(ReviewAssignment, ReviewAssignment.id == ReviewDecision.assignment_id)
            .where(ReviewAssignment.case_id == case.id)
            .order_by(ReviewAssignment.round)
        ).all()
        appeal = session.scalar(select(Appeal).where(Appeal.case_id == case.id))
        return case_result(case) | {
            "decisions": [
                {"verdict": d.verdict, "rationale": d.rationale, "evidence": d.evidence}
                for d in decisions
            ],
            "disagreement_count": int(len({d.verdict for d in decisions[:2]}) > 1),
            "appeal": {"state": appeal.state, "reason": appeal.reason} if appeal else None,
        }


@router.get(ROOT + "/rewards")
def reward_queue(workspace_id: UUID, request: Request, user: Actor, offset: int = 0):
    from app.reviews.models import RewardRecord

    with request.app.state.database.sessions.begin() as session:
        service.admin(session, workspace_id, user.id)
        rows = session.scalars(
            select(RewardRecord)
            .where(RewardRecord.workspace_id == workspace_id)
            .order_by(RewardRecord.id)
            .offset(max(0, offset))
            .limit(100)
        )
        return {
            "items": [
                {
                    "id": str(r.id),
                    "amount_millimes": r.amount_millimes,
                    "currency": r.currency,
                    "state": r.state,
                    "beneficiary_available": r.subject_id is not None,
                    "settled_at": r.settled_at,
                }
                for r in rows
            ],
            "limit": 100,
            "offset": max(0, offset),
        }


@router.get(ROOT + "/rewards/{reward_id}/payments")
def payment_history(
    workspace_id: UUID, reward_id: UUID, request: Request, user: Actor, offset: int = 0
):
    from app.reviews.models import PayoutRecord, RewardRecord

    with request.app.state.database.sessions.begin() as session:
        service.admin(session, workspace_id, user.id)
        reward = session.scalar(
            select(RewardRecord).where(
                RewardRecord.workspace_id == workspace_id, RewardRecord.id == reward_id
            )
        )
        if not reward:
            service.fail("NOT_FOUND", 404)
        rows = session.scalars(
            select(PayoutRecord)
            .where(PayoutRecord.workspace_id == workspace_id, PayoutRecord.reward_id == reward_id)
            .order_by(PayoutRecord.created_at, PayoutRecord.id)
            .offset(max(0, offset))
            .limit(100)
        )
        return {
            "items": [
                payout_result(p)
                | {
                    "external_reference": p.external_reference,
                    "evidence": p.evidence,
                    "transaction_id": str(p.transaction_id) if p.transaction_id else None,
                }
                for p in rows
            ],
            "limit": 100,
            "offset": max(0, offset),
        }


@router.get(ROOT + "/journal")
def journal(workspace_id: UUID, request: Request, user: Actor, offset: int = 0):
    from app.reviews.models import LedgerAccount, LedgerEntry, LedgerTransaction

    with request.app.state.database.sessions.begin() as session:
        service.admin(session, workspace_id, user.id)
        rows = session.scalars(
            select(LedgerTransaction)
            .where(LedgerTransaction.workspace_id == workspace_id)
            .order_by(LedgerTransaction.created_at, LedgerTransaction.id)
            .offset(max(0, offset))
            .limit(100)
        ).all()
        return {
            "items": [
                {
                    "id": str(t.id),
                    "currency": t.currency,
                    "reversal_of": str(t.reversal_of) if t.reversal_of else None,
                    "entries": [
                        {"account": code, "amount_millimes": amount}
                        for code, amount in session.execute(
                            select(LedgerAccount.code, LedgerEntry.amount_millimes)
                            .join(LedgerEntry, LedgerEntry.account_id == LedgerAccount.id)
                            .where(LedgerEntry.transaction_id == t.id)
                        )
                    ],
                }
                for t in rows
            ],
            "limit": 100,
            "offset": max(0, offset),
        }


@router.post(ROOT + "/financial-retention/sweep")
def retention_sweep(workspace_id: UUID, request: Request, user: Actor):
    """Bounded operational sweep at server time under the reviewed policy."""
    from app.reviews.privacy import minimize_financial

    with request.app.state.database.sessions.begin() as session:
        service.admin(session, workspace_id, user.id)
        return {"minimized": minimize_financial(session, workspace_id, limit=100), "limit": 100}
