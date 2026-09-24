"""P08 adversarial service/SQL and full human appeal accounting lifecycle."""

import secrets
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from study_fixtures import blocks, ready_study
from test_collection_db import put

from app.auth.models import Membership, User
from app.auth.security import token_hash, utcnow
from app.collection.models import CollectionSession
from app.common.errors import DomainError
from app.common.privacy_models import ConsentDocument
from app.recruiting.models import (
    Candidate,
    Invitation,
    PanelConsent,
    ParticipantProfile,
    RecruitmentConfig,
    Reservation,
)
from app.reviews import service
from app.reviews.models import (
    LedgerAccount,
    LedgerEntry,
    LedgerTransaction,
    QualityFlag,
    ReviewAssignment,
    ReviewCase,
    ReviewDecision,
    RewardRecord,
)
from app.reviews.schemas import AppealBody, DecisionBody, PayoutBody, RetentionBody
from app.studies.models import Launch, Study, StudyGrant, StudyVersion

pytestmark = pytest.mark.db


@pytest.fixture
def collected(research_app, db_engine, request):
    client, app, actor = research_app
    owner_headers, _, workspace_id = actor()
    selected = [blocks(str(uuid4()))[0], blocks(str(uuid4()))[3]]
    selected[0]["branches"] = [
        {"source": "single", "operator": "eq", "value": "no", "target": None}
    ]
    if getattr(request, "param", None) == "methods":
        selected = None
    fixture = ready_study(client, f"/api/v1/workspaces/{workspace_id}", owner_headers, selected)
    response = client.post(
        fixture["endpoint"] + "/publish", headers=owner_headers, json={"expected_revision": 2}
    )
    assert response.status_code == 200, response.text
    raw = secrets.token_urlsafe(32)
    with Session(db_engine) as session, session.begin():
        user = User(
            email=f"participant-{uuid4().hex}@example.test",
            password_hash="synthetic",
            verified_at=utcnow(),
        )
        session.add(user)
        session.flush()
        participant_headers = {
            "Authorization": "Bearer " + app.state.auth._new_login(session, user)["access_token"]
        }
        profile = ParticipantProfile(user_id=user.id)
        session.add(profile)
        session.flush()
        session.add(
            PanelConsent(
                profile_id=profile.id,
                decision="granted",
                document_version="1",
                document_digest="a" * 64,
                request_digest="a" * 64,
                receipt_key=uuid4().hex,
            )
        )
        launch = session.scalar(
            select(Launch).where(Launch.version_id == UUID(fixture["version_id"]))
        )
        session.add(
            RecruitmentConfig(
                workspace_id=workspace_id,
                launch_id=launch.id,
                capacity=5,
                budget_millimes=10000,
                reward_millimes=1000,
            )
        )
        candidate = Candidate(
            workspace_id=workspace_id,
            launch_id=launch.id,
            subject_id=user.id,
            source_kind="public",
            source_id=profile.id,
            status="eligible",
            attributes_json={},
        )
        session.add(candidate)
        session.flush()
        session.add(
            Invitation(
                workspace_id=workspace_id,
                candidate_id=candidate.id,
                token_hash=token_hash(raw),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        document = session.get(ConsentDocument, UUID(fixture["body"]["consent_documents"]["fr"]))
        body = {
            "invitation_token": raw,
            "capability": secrets.token_urlsafe(32),
            "locale": "fr",
            "document_id": str(document.id),
            "presented_digest": document.digest,
            "consent": "granted",
        }
    response = client.post("/api/v1/collection/sessions", headers=participant_headers, json=body)
    assert response.status_code == 201, response.text
    result = response.json()
    return (
        client,
        "/api/v1/collection/sessions/" + result["session_id"],
        {"X-Session-Token": body["capability"]},
        result,
        participant_headers,
        body,
    )


@pytest.fixture
def reviewed(collected, db_engine):  # noqa: F811
    client, url, headers, result, auth, start = collected
    assert put(client, url, headers, "no")[0].status_code == 200
    response = client.post(
        url + "/submit",
        headers=headers,
        json={"version_id": result["version_id"], "expected_revision": 1},
    )
    assert response.status_code == 200, response.text
    sid = UUID(result["session_id"])
    with Session(db_engine) as s, s.begin():
        row = s.get(CollectionSession, sid)
        version = s.get(StudyVersion, row.version_id)
        study = s.get(Study, version.study_id)
        owner = s.get(Membership, study.owner_membership_id).user_id
        wid = row.workspace_id
        reviewers = []
        for _ in range(4):
            user = User(
                email=f"reviewer-{uuid4()}@example.test",
                password_hash="synthetic",
                verified_at=utcnow(),
            )
            s.add(user)
            s.flush()
            member = Membership(workspace_id=wid, user_id=user.id, role="reviewer", status="active")
            s.add(member)
            s.flush()
            s.add(
                StudyGrant(
                    workspace_id=wid,
                    study_id=study.id,
                    membership_id=member.id,
                    capabilities=["read", "review"],
                )
            )
            reviewers.append(user.id)
        reservation = s.scalar(
            select(Reservation).where(Reservation.candidate_id == row.candidate_id)
        )
        assert reservation.reward_millimes == 1000
        service.retention_policy(
            s,
            wid,
            owner,
            RetentionBody(settled_days=0, rationale="Synthetic reviewed minimization policy"),
        )
        row.quality_summary = {
            "policy": "p07_deterministic_v1",
            "flags": [{"block_key": "single", "code": "attention_mismatch"}],
        }
        service.sync_quality(s, row)
        subject = row.subject_id
    return wid, sid, owner, reviewers, subject


def vote(verdict="accepted", key=None):
    return DecisionBody(
        command_key=key or uuid4(),
        verdict=verdict,
        rationale="Human checked submitted evidence",
        evidence=["single: final answer"],
    )


def decisions(s, wid, sid, owner, reviewers, verdicts=("accepted", "accepted")):
    assignments = [service.assign(s, wid, owner, sid, r, "independent") for r in reviewers[:2]]
    for a, v in zip(assignments, verdicts, strict=True):
        service.decide(s, wid, a.reviewer_id, a.id, vote(v))
    return assignments


def payment(failed=False, amount=1000, key=None, ref=None):
    return PayoutBody(
        command_key=key or uuid4(),
        amount_millimes=amount,
        external_reference=ref or "receipt-" + uuid4().hex,
        evidence="Manual confirmation checked",
        failed=failed,
    )


def test_consensus_reward_retry_payment_failure_reversal(reviewed, db_engine):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        assignments = [service.assign(s, wid, owner, sid, r, "independent") for r in reviewers[:2]]
        first = vote()
        second = vote()
        assert service.decide(s, wid, reviewers[0], assignments[0].id, first).state == "pending"
        assert service.accepted_decision_snapshot(s, wid, sid) is None
        assert service.decide(s, wid, reviewers[1], assignments[1].id, second).state == "accepted"
        snapshot = service.accepted_decision_snapshot(s, wid, sid)
        service.decide(s, wid, reviewers[1], assignments[1].id, second)
        assert service.accepted_decision_snapshot(s, wid, sid) == snapshot
        reward = s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject))
        rid = reward.id
        assert reward.amount_millimes == 1000
        failure = service.payout(s, wid, owner, rid, payment(True))
        assert failure.transaction_id is None and reward.state == "earned"
        body = payment()
        paid = service.payout(s, wid, owner, rid, body)
        assert service.payout(s, wid, owner, rid, body).id == paid.id
        assert reward.state == "paid"
        service.reverse_payout(s, wid, owner, paid.id)
        service.reverse_payout(s, wid, owner, paid.id)
        assert reward.state == "earned"
        service.payout(s, wid, owner, rid, payment())
        assert (
            s.scalar(
                select(func.count())
                .select_from(RewardRecord)
                .where(RewardRecord.subject_id == subject)
            )
            == 1
        )
    with Session(db_engine) as s:
        totals = s.execute(
            select(LedgerEntry.transaction_id, func.sum(LedgerEntry.amount_millimes))
            .where(LedgerEntry.workspace_id == wid)
            .group_by(LedgerEntry.transaction_id)
        ).all()
        assert len(totals) == 4 and all(total == 0 for _, total in totals)


def test_disagreement_adjudication_appeal_and_no_reopen(reviewed, db_engine):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        decisions(s, wid, sid, owner, reviewers, ("accepted", "rejected"))
        case = s.scalar(select(ReviewCase).where(ReviewCase.session_id == sid))
        assert case.state == "disputed"
        assignment = service.assign(s, wid, owner, sid, reviewers[2], "adjudication")
        service.decide(s, wid, reviewers[2], assignment.id, vote("rejected"))
        body = AppealBody(command_key=uuid4(), reason="Please reconsider the task evidence")
        appeal = service.appeal(s, wid, subject, sid, body)
        assert service.appeal(s, wid, subject, sid, body).id == appeal.id
        a = service.assign(s, wid, owner, sid, reviewers[3], "appeal")
        service.decide(s, wid, reviewers[3], a.id, vote("rejected"))
        assert appeal.state == "upheld" and case.state == "rejected"
        with pytest.raises(DomainError):
            service.appeal(s, wid, subject, sid, AppealBody(command_key=uuid4(), reason="Again"))
        assert s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject)) is None


def test_appeal_overturn_earns_once(reviewed, db_engine):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        decisions(s, wid, sid, owner, reviewers, ("rejected", "rejected"))
        appeal = service.appeal(
            s, wid, subject, sid, AppealBody(command_key=uuid4(), reason="Technical failure")
        )
        a = service.assign(s, wid, owner, sid, reviewers[2], "appeal")
        assert service.decide(s, wid, reviewers[2], a.id, vote()).state == "accepted"
        assert appeal.state == "overturned"
        assert service.earn(s, s.get(CollectionSession, sid)).amount_millimes == 1000


@pytest.mark.parametrize(
    "scenario",
    [
        "self",
        "cross_workspace",
        "unassigned",
        "duplicate_reviewer",
        "conflicting_retry",
        "third_round",
        "partial",
        "currency",
        "duplicate_reference",
        "double_payment",
        "failed_reverse",
    ],
)
def test_forbidden_and_conflicting_commands(reviewed, db_engine, scenario):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        if scenario == "self":
            with pytest.raises(DomainError):
                service.assign(s, wid, owner, sid, subject, "independent")
        elif scenario == "cross_workspace":
            with pytest.raises(DomainError):
                service.assign(s, uuid4(), owner, sid, reviewers[0], "independent")
        else:
            assignments = decisions(s, wid, sid, owner, reviewers)
            reward = s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject))
            with pytest.raises(DomainError):
                if scenario == "unassigned":
                    service.decide(s, wid, reviewers[2], assignments[0].id, vote())
                elif scenario == "duplicate_reviewer":
                    service.assign(s, wid, owner, sid, reviewers[0], "adjudication")
                elif scenario == "conflicting_retry":
                    service.decide(s, wid, reviewers[0], assignments[0].id, vote("rejected"))
                elif scenario == "third_round":
                    service.assign(s, wid, owner, sid, reviewers[2], "independent")
                elif scenario == "partial":
                    service.payout(s, wid, owner, reward.id, payment(amount=500))
                elif scenario == "currency":
                    service.money(1000, "USD")
                elif scenario == "duplicate_reference":
                    service.payout(s, wid, owner, reward.id, payment(True, ref="duplicate"))
                    service.payout(s, wid, owner, reward.id, payment(ref="duplicate"))
                elif scenario == "double_payment":
                    service.payout(s, wid, owner, reward.id, payment())
                    service.payout(s, wid, owner, reward.id, payment())
                elif scenario == "failed_reverse":
                    failed = service.payout(s, wid, owner, reward.id, payment(True))
                    service.reverse_payout(s, wid, owner, failed.id)


def test_quality_import_idempotent_privacy_preserves_obligation(reviewed, db_engine):
    from app.reviews.privacy import purge_subject, subject_financial_data

    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        row = s.get(CollectionSession, sid)
        case = service.sync_quality(s, row)
        service.sync_quality(s, row)
        assert (
            s.scalar(
                select(func.count()).select_from(QualityFlag).where(QualityFlag.case_id == case.id)
            )
            == 1
        )
        decisions(s, wid, sid, owner, reviewers)
        purge_subject(s, wid, subject)
        assert service.accepted_decision_snapshot(s, wid, sid) is None
        data = subject_financial_data(s, wid, subject)
        assert len(data) == 1 and data[0]["state"] == "earned"
        assert set(data[0]) == {"id", "amount_millimes", "currency", "state", "settled_at"}


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ledger_entries SET amount_millimes=1 WHERE workspace_id=:wid",
        "DELETE FROM ledger_transactions WHERE workspace_id=:wid",
        "UPDATE ledger_accounts SET currency='USD' WHERE workspace_id=:wid",
        "DELETE FROM reward_records WHERE workspace_id=:wid",
        "UPDATE reward_records SET amount_millimes=2000 WHERE workspace_id=:wid",
        "UPDATE reward_records SET subject_id=NULL WHERE workspace_id=:wid",
        "UPDATE review_decisions SET rationale='rewritten' WHERE workspace_id=:wid",
        "UPDATE review_assignments SET round=99 WHERE workspace_id=:wid",
        "UPDATE financial_retention_policies SET settled_days=1 WHERE workspace_id=:wid",
    ],
)
def test_database_immutable_guards(reviewed, db_engine, sql):
    wid, sid, owner, reviewers, _ = reviewed
    with Session(db_engine) as s, s.begin():
        decisions(s, wid, sid, owner, reviewers)
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        s.execute(text(sql), {"wid": wid})


@pytest.mark.parametrize(
    "kind", ["unbalanced", "empty", "late_append", "fake_paid", "self_assignment"]
)
def test_database_structural_guards(reviewed, db_engine, kind):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        decisions(s, wid, sid, owner, reviewers)
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        if kind in {"empty", "unbalanced"}:
            tx = LedgerTransaction(workspace_id=wid, command_key="bad:" + uuid4().hex)
            s.add(tx)
            s.flush()
            if kind == "unbalanced":
                account = s.scalar(
                    select(LedgerAccount).where(LedgerAccount.workspace_id == wid).limit(1)
                )
                s.add(
                    LedgerEntry(
                        workspace_id=wid,
                        transaction_id=tx.id,
                        account_id=account.id,
                        amount_millimes=100,
                    )
                )
        elif kind == "late_append":
            entry = s.scalar(select(LedgerEntry).where(LedgerEntry.workspace_id == wid).limit(1))
            s.add(
                LedgerEntry(
                    workspace_id=wid,
                    transaction_id=entry.transaction_id,
                    account_id=entry.account_id,
                    amount_millimes=100,
                )
            )
        elif kind == "fake_paid":
            s.execute(
                text(
                    "UPDATE reward_records SET state='paid',settled_at=now() WHERE workspace_id=:wid"
                ),
                {"wid": wid},
            )
        else:
            case = s.scalar(select(ReviewCase).where(ReviewCase.session_id == sid))
            s.add(
                ReviewAssignment(
                    workspace_id=wid,
                    case_id=case.id,
                    reviewer_id=subject,
                    round=99,
                    kind="adjudication",
                )
            )


def test_assigned_api_blind_evidence_and_revoked_grant(reviewed, db_engine, research_app):
    wid, sid, owner, reviewers, subject = reviewed
    client, app, _ = research_app
    with Session(db_engine) as s, s.begin():
        assignment = service.assign(s, wid, owner, sid, reviewers[0], "independent")
        assert service.assign(s, wid, owner, sid, reviewers[0], "independent").id == assignment.id
        aid = assignment.id
        user = s.get(User, reviewers[0])
        auth = {"Authorization": "Bearer " + app.state.auth._new_login(s, user)["access_token"]}
        stranger = s.get(User, reviewers[1])
        other_auth = {
            "Authorization": "Bearer " + app.state.auth._new_login(s, stranger)["access_token"]
        }
    url = f"/api/v1/workspaces/{wid}/reviews/assignments/{aid}"
    response = client.get(url, headers=auth)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "prior_decisions" not in body and "subject_id" not in body
    assert body["answers"][0]["block_key"] == "single"
    assert "no-store" in response.headers["cache-control"]
    assert client.get(url, headers=other_auth).status_code == 404
    with Session(db_engine) as s, s.begin():
        member = s.scalar(
            select(Membership).where(
                Membership.user_id == reviewers[0], Membership.workspace_id == wid
            )
        )
        grant = s.scalar(select(StudyGrant).where(StudyGrant.membership_id == member.id))
        grant.revoked_at = utcnow()
    assert client.get(url, headers=auth).status_code == 404


def test_retention_minimization_never_reopens_or_loses_obligation(reviewed, db_engine):
    from app.reviews.privacy import minimize_financial, subject_financial_data

    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        decisions(s, wid, sid, owner, reviewers)
        reward = s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject))
        rid = reward.id
        assert minimize_financial(s, wid, subject) == 0
        paid = service.payout(s, wid, owner, rid, payment())
        pid = paid.id
    # PostgreSQL transaction time and Python wall clock align after a separate commit.
    with Session(db_engine) as s, s.begin():
        assert minimize_financial(s, wid, subject) == 1
        assert subject_financial_data(s, wid, subject) == []
        with pytest.raises(DomainError):
            service.reverse_payout(s, wid, owner, pid)
        assert s.get(RewardRecord, rid).state == "paid"


def test_rejection_fake_evidence_and_posting_retry_conflict(reviewed, db_engine):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        assignment = service.assign(s, wid, owner, sid, reviewers[0], "independent")
        body = vote("rejected").model_copy(update={"evidence": ["nonexistent: flag"]})
        with pytest.raises(DomainError):
            service.decide(s, wid, reviewers[0], assignment.id, body)
        assert (
            s.scalar(select(ReviewDecision).where(ReviewDecision.assignment_id == assignment.id))
            is None
        )
        tx = service.post(s, wid, "synthetic-correction", [("expense", 500), ("payable", -500)])
        assert (
            service.post(s, wid, "synthetic-correction", [("expense", 500), ("payable", -500)]).id
            == tx.id
        )
        with pytest.raises(DomainError):
            service.post(s, wid, "synthetic-correction", [("expense", 600), ("payable", -600)])


def test_discovery_status_and_manual_reconciliation_api(reviewed, db_engine, research_app):
    wid, sid, owner, reviewers, subject = reviewed
    client, app, _ = research_app
    with Session(db_engine) as s, s.begin():

        def auth(uid):
            return {
                "Authorization": "Bearer "
                + app.state.auth._new_login(s, s.get(User, uid))["access_token"]
            }

        owner_auth = auth(owner)
        reviewer_auth = auth(reviewers[0])
        subject_auth = auth(subject)
        version = s.get(StudyVersion, s.get(CollectionSession, sid).version_id)
        study_id = version.study_id
        assignments = decisions(s, wid, sid, owner, reviewers)
        first_assignment_id = assignments[0].id
        reward = s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject))
        rid = reward.id
        service.payout(s, wid, owner, rid, payment())
    root = f"/api/v1/workspaces/{wid}/reviews"
    queue = client.get(root + f"/studies/{study_id}/cases", headers=owner_auth)
    assert queue.status_code == 200, queue.text
    assert queue.json()["items"][0]["state"] == "accepted"
    inbox = client.get(root + "/my-assignments", headers=reviewer_auth)
    assert inbox.status_code == 200 and inbox.json()["items"][0]["id"] == str(first_assignment_id)
    status = client.get(root + f"/sessions/{sid}/status", headers=subject_auth)
    assert status.status_code == 200 and status.json()["disagreement_count"] == 0
    assert "reviewer_id" not in str(status.json())
    assert client.get(root + f"/sessions/{sid}/status", headers=reviewer_auth).status_code == 403
    rewards = client.get(root + "/rewards", headers=owner_auth)
    assert rewards.status_code == 200 and rewards.json()["items"][0]["id"] == str(rid)
    assert client.get(root + "/rewards", headers=reviewer_auth).status_code == 403
    payments = client.get(root + f"/rewards/{rid}/payments", headers=owner_auth)
    assert payments.status_code == 200 and payments.json()["items"][0]["manual_record_only"]
    journal = client.get(root + "/journal", headers=owner_auth)
    assert journal.status_code == 200
    assert len(journal.json()["items"]) == 2
    assert all(
        sum(e["amount_millimes"] for e in t["entries"]) == 0 for t in journal.json()["items"]
    )


def test_concurrent_acceptance_and_full_settlement_exactly_once(reviewed, db_engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        assignments = [
            service.assign(s, wid, owner, sid, r, "independent").id for r in reviewers[:2]
        ]
    barrier = Barrier(2)

    def decide_one(index):
        barrier.wait(timeout=10)
        with Session(db_engine) as s, s.begin():
            return service.decide(s, wid, reviewers[index], assignments[index], vote()).state

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(decide_one, [0, 1])) == ["accepted", "pending"]
    with Session(db_engine) as s:
        rewards = s.scalars(select(RewardRecord).where(RewardRecord.subject_id == subject)).all()
        assert len(rewards) == 1
        rid = rewards[0].id
    barrier = Barrier(2)
    body = payment()

    def pay_one(_):
        barrier.wait(timeout=10)
        with Session(db_engine) as s, s.begin():
            return service.payout(s, wid, owner, rid, body).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(pay_one, [0, 1]))
    assert ids[0] == ids[1]
    with Session(db_engine) as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(LedgerTransaction)
                .where(LedgerTransaction.workspace_id == wid)
            )
            == 2
        )


def test_quality_materializes_all_pinned_evidence_without_deciding(reviewed, db_engine):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        row = s.get(CollectionSession, sid)
        row.quality_summary = {
            "policy": "p07_deterministic_v1",
            "flags": [
                {"block_key": "text", "code": "short_text"},
                {"block_key": "task", "code": "fast_task"},
            ],
        }
        case = service.sync_quality(s, row)
        service.sync_quality(s, row)
        flags = s.scalars(select(QualityFlag).where(QualityFlag.case_id == case.id)).all()
        assert {f.code for f in flags} == {"short_text", "fast_task", "attention_mismatch"}
        assert case.state == "pending"
        assert s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject)) is None


@pytest.mark.parametrize("source", ["payment", "earning"])
def test_direct_journal_reversal_cannot_desynchronize_obligations(reviewed, db_engine, source):
    wid, sid, owner, reviewers, subject = reviewed
    with Session(db_engine) as s, s.begin():
        decisions(s, wid, sid, owner, reviewers)
        reward = s.scalar(select(RewardRecord).where(RewardRecord.subject_id == subject))
        if source == "payment":
            original = service.payout(s, wid, owner, reward.id, payment()).transaction_id
            postings = [("payable", -1000), ("manual_cash", 1000)]
        else:
            original = s.scalar(
                select(LedgerTransaction.id).where(
                    LedgerTransaction.workspace_id == wid,
                    LedgerTransaction.command_key == "earn:" + str(reward.id),
                )
            )
            postings = [("expense", -1000), ("payable", 1000)]
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        service.post(s, wid, "unsupported-reversal", postings, original)


def test_http_review_appeal_payment_and_retention_pipeline(reviewed, db_engine, research_app):
    wid, sid, owner, reviewers, subject = reviewed
    client, app, _ = research_app
    with Session(db_engine) as s, s.begin():
        tokens = {
            uid: {
                "Authorization": "Bearer "
                + app.state.auth._new_login(s, s.get(User, uid))["access_token"]
            }
            for uid in [owner, subject, *reviewers]
        }
    root = f"/api/v1/workspaces/{wid}/reviews"
    for reviewer in reviewers[:2]:
        assigned = client.post(
            root + f"/sessions/{sid}/assignments",
            headers=tokens[owner],
            json={"reviewer_id": str(reviewer), "kind": "independent"},
        )
        assert assigned.status_code == 201, assigned.text
        command = vote("rejected").model_dump(mode="json")
        response = client.post(
            root + f"/assignments/{assigned.json()['id']}/decision",
            headers=tokens[reviewer],
            json=command,
        )
        assert response.status_code == 200, response.text
    appealed = client.post(
        root + f"/sessions/{sid}/appeal",
        headers=tokens[subject],
        json={"command_key": str(uuid4()), "reason": "Please inspect technical task evidence"},
    )
    assert appealed.status_code == 201, appealed.text
    assigned = client.post(
        root + f"/sessions/{sid}/assignments",
        headers=tokens[owner],
        json={"reviewer_id": str(reviewers[2]), "kind": "appeal"},
    )
    assert assigned.status_code == 201, assigned.text
    command = vote().model_dump(mode="json")
    url = root + f"/assignments/{assigned.json()['id']}/decision"
    accepted = client.post(url, headers=tokens[reviewers[2]], json=command)
    assert accepted.status_code == 200 and accepted.json()["state"] == "accepted", accepted.text
    assert client.post(url, headers=tokens[reviewers[2]], json=command).json() == accepted.json()
    rewards = client.get(root + "/rewards", headers=tokens[owner]).json()["items"]
    assert len(rewards) == 1
    rid = rewards[0]["id"]
    pay_url = root + f"/rewards/{rid}/payments"
    assert (
        client.post(root + "/financial-retention/sweep", headers=tokens[owner]).json()["minimized"]
        == 0
    )
    assert (
        client.post(root + "/financial-retention/sweep", headers=tokens[reviewers[0]]).status_code
        == 403
    )
    assert (
        client.post(
            pay_url, headers=tokens[owner], json=payment(amount=500).model_dump(mode="json")
        ).status_code
        == 422
    )
    failed = client.post(pay_url, headers=tokens[owner], json=payment(True).model_dump(mode="json"))
    assert failed.status_code == 201 and failed.json()["state"] == "failed"
    body = payment().model_dump(mode="json")
    paid = client.post(pay_url, headers=tokens[owner], json=body)
    assert paid.status_code == 201 and paid.json()["state"] == "recorded", paid.text
    assert client.post(pay_url, headers=tokens[owner], json=body).json() == paid.json()
    reversal = client.post(root + f"/payments/{paid.json()['id']}/reverse", headers=tokens[owner])
    assert reversal.status_code == 200 and reversal.json()["state"] == "reversed", reversal.text
    assert (
        client.post(
            pay_url, headers=tokens[owner], json=payment().model_dump(mode="json")
        ).status_code
        == 201
    )
    swept = client.post(root + "/financial-retention/sweep", headers=tokens[owner])
    assert swept.status_code == 200 and swept.json()["minimized"] == 1, swept.text
    assert client.get(root + "/my-rewards", headers=tokens[subject]).json()["items"] == []
