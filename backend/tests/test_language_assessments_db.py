"""Synthetic database validation does not claim real content or human approval."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from test_language_assessments import content
from test_recruiting import configure, invite, optin
from test_recruiting import recruitment as recruitment

from app.auth.security import utcnow
from app.recruiting import assessments, service
from app.recruiting.models import (
    Candidate,
    Qualification,
)
from app.recruiting.models import (
    LanguageAssessmentAttempt as Attempt,
)
from app.recruiting.models import (
    LanguageAssessmentDecision as Decision,
)

pytestmark = pytest.mark.db
API = "/api/v1"
ATTEMPTS = API + "/panel/language-assessment-attempts"


def ok(response, code=200):
    assert response.status_code == code, response.text
    return response.json()


@pytest.fixture
def assessment(research_app):
    client, app, actor = research_app
    author_h, author_id, wid = actor()
    reviewer_h, reviewer_id, _ = actor(wid, "reviewer")
    appeal_h, appeal_id, _ = actor(wid, "reviewer")
    ph, pid, _ = actor()
    profile, _ = optin(client, ph, languages=["french"])
    app.state.settings = app.state.settings.model_copy(
        update={
            "language_assessment_authority_workspace_id": wid,
            "language_assessment_reviewers": {
                reviewer_id: assessments.LANGUAGES,
                appeal_id: assessments.LANGUAGES,
            },
        }
    )
    root = API + f"/workspaces/{wid}/language-assessments"
    grant = ok(
        client.put(
            API + "/panel/language-assessment-consent",
            headers=ph,
            json=dict(
                decision="granted",
                document_version="1",
                presented_digest=assessments.CONSENT_DIGEST,
                receipt_key=uuid4().hex,
            ),
        )
    )
    return dict(
        client=client,
        app=app,
        actor=actor,
        ah=author_h,
        aid=author_id,
        rh=reviewer_h,
        rid=reviewer_id,
        appeal_h=appeal_h,
        appeal_id=appeal_id,
        ph=ph,
        pid=pid,
        profile=profile,
        wid=wid,
        root=root,
        grant=grant,
    )


def publish(ctx, **kwargs):
    c, root = ctx["client"], ctx["root"]
    body = content(key=uuid4().hex, **kwargs)
    version = ok(c.post(root + "/versions", headers=ctx["ah"], json=body), 201)
    ok(
        c.post(
            root + f"/versions/{version['id']}/approve",
            headers=ctx["rh"],
            json=dict(
                content_digest=version["content_digest"],
                review_reference="synthetic-test-review",
                content_validity_confirmed=True,
            ),
        )
    )
    return version


def begin(ctx, version, command=None):
    return ctx["client"].post(
        ATTEMPTS,
        headers=ctx["ph"],
        json=dict(
            version_id=version["id"],
            consent_grant_id=ctx["grant"]["id"],
            command_key=command or uuid4().hex,
        ),
    )


def submit(ctx, attempt, command="submit"):
    return ctx["client"].post(
        ATTEMPTS + f"/{attempt['id']}/submit",
        headers=ctx["ph"],
        json=dict(
            command_key=command, responses={"choice": "b", "text": "RESPONSE_CANARY_synthetic"}
        ),
    )


def decide(ctx, attempt, verdict="qualified", round=1, headers=None):
    return ctx["client"].post(
        ctx["root"] + f"/attempts/{attempt['id']}/decisions",
        headers=headers or ctx["rh"],
        json=dict(
            command_key=f"decision-{round}",
            round=round,
            verdict=verdict,
            findings={"choice": {"accuracy": "met"}, "text": {"clarity": "met"}},
            rationale="Synthetic reviewer decision; not real approval.",
        ),
    )


def test_synthetic_human_lifecycle_and_private_projections(assessment):
    x = assessment
    c = x["client"]
    version = publish(x)
    catalogue = ok(c.get(API + "/panel/language-assessments", headers=x["ph"]))
    assert catalogue["items"]
    assert "tasks" not in catalogue["items"][0]
    attempt = ok(begin(x, version, "start"), 201)
    assert ok(begin(x, version, "start"), 201)["id"] == attempt["id"]
    submitted = ok(submit(x, attempt))
    assert submitted["state"] == "submitted" and submitted["decisions"] == []
    assert ok(submit(x, attempt))["id"] == attempt["id"]
    assert submit(x, attempt, "different").status_code == 409
    assert ok(c.get(API + "/panel/language-qualifications", headers=x["ph"]))["current"] == []
    queue = ok(c.get(x["root"] + "/queue?language=french", headers=x["rh"]))
    assert any(i["id"] == attempt["id"] for i in queue["items"])
    assert "RESPONSE_CANARY" not in str(queue)
    adjudicated = ok(decide(x, attempt))
    assert adjudicated["state"] == "adjudicated"
    assert ok(decide(x, attempt))["decisions"] == adjudicated["decisions"]
    assert ok(c.get(API + "/panel/language-qualifications", headers=x["ph"]))["current"] == []
    for projection in [catalogue, attempt, submitted, queue, adjudicated]:
        assert "KEY_CANARY" not in str(projection) and "RUBRIC_CANARY" not in str(projection)
    private = ok(c.get(x["root"] + f"/versions/{version['id']}/private-material", headers=x["rh"]))
    assert "KEY_CANARY" in str(private)
    assert (
        c.get(
            x["root"] + f"/versions/{version['id']}/private-material", headers=x["ah"]
        ).status_code
        == 403
    )
    other_h, _, other_w = x["actor"]()
    assert c.get(ATTEMPTS + f"/{attempt['id']}", headers=other_h).status_code == 404
    assert c.get(x["root"] + f"/attempts/{attempt['id']}", headers=other_h).status_code in {
        403,
        404,
    }
    assert (
        c.get(
            API + f"/workspaces/{other_w}/language-assessments/attempts/{attempt['id']}",
            headers=other_h,
        ).status_code
        == 404
    )
    with x["app"].state.database.sessions() as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(Qualification)
                .where(Qualification.profile_id == UUID(x["profile"]))
            )
            == 0
        )


def test_independent_approval_digest_retirement_and_no_edit(assessment):
    x = assessment
    c = x["client"]
    v = ok(c.post(x["root"] + "/versions", headers=x["ah"], json=content(key=uuid4().hex)), 201)
    reviewer_copy = ok(c.get(x["root"] + f"/versions/{v['id']}", headers=x["rh"]))
    assert reviewer_copy["content_digest"] == v["content_digest"]
    assert reviewer_copy["tasks"] == v["tasks"] and "material" not in reviewer_copy
    url = x["root"] + f"/versions/{v['id']}/approve"
    body = dict(
        content_digest=v["content_digest"],
        review_reference="synthetic-review",
        content_validity_confirmed=True,
    )
    x["app"].state.settings.language_assessment_reviewers[x["aid"]] = ["french"]
    assert c.post(url, headers=x["ah"], json=body).status_code == 403
    assert c.post(url, headers=x["rh"], json=body | {"content_digest": "0" * 64}).status_code == 409
    ok(c.post(url, headers=x["rh"], json=body))
    attempt = ok(begin(x, v), 201)
    ok(
        c.post(
            x["root"] + f"/versions/{v['id']}/retire",
            headers=x["rh"],
            json={"content_digest": v["content_digest"]},
        )
    )
    assert begin(x, v).status_code == 409
    assert c.patch(x["root"] + f"/versions/{v['id']}", headers=x["ah"], json={}).status_code == 405
    ok(submit(x, attempt))
    ok(decide(x, attempt))


def test_limits_cross_version_concurrent_starts_and_late_submit(assessment, monkeypatch):
    x = assessment
    a, b = publish(x), publish(x)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: begin(x, a, "parallel"), range(2)))
    assert [r.status_code for r in replies] == [201, 201]
    attempt = replies[0].json()
    assert replies[1].json()["id"] == attempt["id"]
    assert begin(x, b).status_code == 409
    now = utcnow()
    with x["app"].state.database.sessions.begin() as s:
        row = s.get(Attempt, UUID(attempt["id"]))
        row.deadline_at = now - timedelta(seconds=1)
    assert submit(x, attempt).status_code == 409
    assert begin(x, b).json()["error"]["code"] == "ASSESSMENT_COOLDOWN"
    with x["app"].state.database.sessions.begin() as s:
        row = s.get(Attempt, UUID(attempt["id"]))
        row.started_at = now - timedelta(hours=24)
    monkeypatch.setattr(assessments, "utcnow", lambda: now)
    second = ok(begin(x, b), 201)
    with x["app"].state.database.sessions() as s:
        assert s.get(Attempt, UUID(attempt["id"])).state == "abandoned"
    assert second["sequence"] == 2


def test_concurrent_submissions_and_decisions_are_single_durable_actions(assessment):
    x = assessment
    attempt = ok(begin(x, publish(x)), 201)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r.status_code == 200 for r in pool.map(lambda _: submit(x, attempt), range(2)))
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(r.status_code == 200 for r in pool.map(lambda _: decide(x, attempt), range(2)))
    with x["app"].state.database.sessions() as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(Decision)
                .where(Decision.attempt_id == UUID(attempt["id"]))
            )
            == 1
        )


def test_withdrawal_exact_grant_fences_regrant_and_review(assessment):
    x = assessment
    c = x["client"]
    attempt = ok(begin(x, publish(x, synthetic=False)), 201)
    ok(submit(x, attempt))
    ok(decide(x, attempt))
    assert len(ok(c.get(API + "/panel/language-qualifications", headers=x["ph"]))["current"]) == 1
    body = dict(
        decision="withdrawn",
        document_version="1",
        presented_digest=assessments.CONSENT_DIGEST,
        receipt_key="withdraw",
        grant_id=x["grant"]["id"],
    )
    receipt = ok(c.put(API + "/panel/language-assessment-consent", headers=x["ph"], json=body))
    assert (
        ok(c.put(API + "/panel/language-assessment-consent", headers=x["ph"], json=body))["id"]
        == receipt["id"]
    )
    ok(
        c.put(
            API + "/panel/language-assessment-consent",
            headers=x["ph"],
            json=body | {"decision": "granted", "grant_id": None, "receipt_key": "regrant"},
        )
    )
    assert ok(c.get(API + "/panel/language-qualifications", headers=x["ph"]))["current"] == []
    assert submit(x, attempt).status_code == 403
    assert decide(x, attempt).status_code == 403
    assert ok(c.get(ATTEMPTS + f"/{attempt['id']}", headers=x["ph"]))["responses"] is not None


def test_appeal_independent_reviewer_latest_reassessment_and_expiry(assessment, monkeypatch):
    x = assessment
    c = x["client"]
    version = publish(x, synthetic=False)
    attempt = ok(begin(x, version), 201)
    ok(submit(x, attempt))
    decision = ok(decide(x, attempt))["decisions"][0]
    ok(
        c.post(
            ATTEMPTS + f"/{attempt['id']}/appeal",
            headers=x["ph"],
            json=dict(command_key="appeal", reason="Synthetic disagreement"),
        )
    )
    assert decide(x, attempt, round=2).status_code == 403
    result = ok(decide(x, attempt, "not_qualified", round=2, headers=x["appeal_h"]))
    assert len(result["decisions"]) == 2
    assert result["decisions"][0]["id"] == decision["id"]
    assert ok(c.get(API + "/panel/language-qualifications", headers=x["ph"]))["current"] == []
    now = utcnow() + timedelta(days=2)
    monkeypatch.setattr(assessments, "utcnow", lambda: now)
    second = ok(begin(x, version), 201)
    ok(submit(x, second))
    result = ok(decide(x, second))
    from datetime import datetime

    expiry = datetime.fromisoformat(result["decisions"][0]["expires_at"].replace("Z", "+00:00"))
    monkeypatch.setattr(assessments, "utcnow", lambda: expiry)
    assert ok(c.get(API + "/panel/language-qualifications", headers=x["ph"]))["current"] == []


def test_frozen_snapshot_expiry_and_grant_revocation(assessment, recruitment, monkeypatch):
    x = assessment
    c = x["client"]
    # Both fixtures share this test's app; authority configuration remains global.
    _, app, _, h, _, wid, _, root, _ = recruitment
    attempt = ok(begin(x, publish(x, synthetic=False)), 201)
    ok(submit(x, attempt))
    result = ok(decide(x, attempt))
    configure(c, h, root, filters={"reviewed_language": "french"})
    invitation = invite(c, h, root, x["profile"])
    headers = x["ph"] | {"X-Invitation-Token": invitation["invitation_token"]}
    with app.state.database.sessions() as s:
        frozen = s.get(Candidate, UUID(invitation["candidate_id"])).attributes_json
    assert frozen["reviewed_languages"] == ["french"]
    assert "rationale" not in str(frozen) and "RESPONSE_CANARY" not in str(frozen)
    from datetime import datetime

    expiry = datetime.fromisoformat(result["decisions"][0]["expires_at"].replace("Z", "+00:00"))
    monkeypatch.setattr(assessments, "utcnow", lambda: expiry)
    ok(c.post(API + "/recruiting/reserve", headers=headers))
    with app.state.database.sessions() as s:
        assert (
            service.source_attributes(s, wid, "public", UUID(x["profile"]))[0]["reviewed_languages"]
            == []
        )
        assert s.get(Candidate, UUID(invitation["candidate_id"])).attributes_json == frozen
    ok(
        c.put(
            API + "/panel/language-assessment-consent",
            headers=x["ph"],
            json=dict(
                decision="withdrawn",
                document_version="1",
                presented_digest=assessments.CONSENT_DIGEST,
                receipt_key="revoke-frozen",
                grant_id=x["grant"]["id"],
            ),
        )
    )
    assert c.post(API + "/recruiting/reserve", headers=headers).status_code == 403


def test_rolling_limit_counts_abandoned_starts_and_resets_at_boundary(assessment, monkeypatch):
    x = assessment
    version = publish(x)
    base = utcnow()
    for day in (0, 1, 2):
        monkeypatch.setattr(assessments, "utcnow", lambda day=day: base + timedelta(days=day))
        ok(begin(x, version), 201)
    monkeypatch.setattr(assessments, "utcnow", lambda: base + timedelta(days=3))
    assert begin(x, publish(x)).json()["error"]["code"] == "ASSESSMENT_ATTEMPT_LIMIT"
    monkeypatch.setattr(assessments, "utcnow", lambda: base + timedelta(days=30))
    assert ok(begin(x, version), 201)["sequence"] == 4


def test_different_concurrent_start_keys_and_invalid_responses(assessment):
    x = assessment
    version = publish(x)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda key: begin(x, version, key), ["one", "two"]))
    assert sorted(r.status_code for r in replies) == [201, 409]
    attempt = next(r.json() for r in replies if r.status_code == 201)
    for responses in (
        {"choice": "wrong", "text": "t"},
        {"choice": "b", "extra": "t"},
        {"choice": "b"},
    ):
        response = x["client"].post(
            ATTEMPTS + f"/{attempt['id']}/submit",
            headers=x["ph"],
            json=dict(command_key="submit", responses=responses),
        )
        assert response.status_code == 422
    ok(submit(x, attempt))


def test_later_negative_reassessment_does_not_resurrect_older_pass(assessment, monkeypatch):
    x = assessment
    v = publish(x, synthetic=False)
    first = ok(begin(x, v), 201)
    ok(submit(x, first))
    ok(decide(x, first))
    later = utcnow() + timedelta(days=2)
    monkeypatch.setattr(assessments, "utcnow", lambda: later)
    second = ok(begin(x, v), 201)
    ok(submit(x, second))
    ok(decide(x, second, "not_qualified"))
    history = ok(x["client"].get(API + "/panel/language-qualifications", headers=x["ph"]))
    assert history["current"] == []
    assert len(history["attempts"]) == 2
    assert history["attempts"][1]["decisions"][0]["verdict"] == "qualified"


@pytest.mark.parametrize("operation", ["submit", "decide"])
def test_withdrawal_serializes_with_evidence_mutations(assessment, operation):
    x = assessment
    attempt = ok(begin(x, publish(x, synthetic=False)), 201)
    if operation == "decide":
        ok(submit(x, attempt))

    def withdraw():
        return x["client"].put(
            API + "/panel/language-assessment-consent",
            headers=x["ph"],
            json=dict(
                decision="withdrawn",
                document_version="1",
                presented_digest=assessments.CONSENT_DIGEST,
                receipt_key="race",
                grant_id=x["grant"]["id"],
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        withdrawal = pool.submit(withdraw)
        mutation = pool.submit(submit if operation == "submit" else decide, x, attempt)
        assert withdrawal.result().status_code == 200
        assert mutation.result().status_code in {200, 403}
    with x["app"].state.database.sessions() as session:
        assert session.get(Attempt, UUID(attempt["id"])).state == "withdrawn"
        assert assessments.current_qualifications(session, UUID(x["profile"])) == []


def test_language_scoped_reviewer_and_self_adjudication_denied(assessment):
    from app.auth.models import Membership

    x = assessment
    version = publish(x)
    attempt = ok(begin(x, version), 201)
    ok(submit(x, attempt))
    x["app"].state.settings.language_assessment_reviewers[x["rid"]] = ["arabizi"]
    assert decide(x, attempt).status_code == 403
    assert (
        x["client"]
        .get(x["root"] + f"/versions/{version['id']}/private-material", headers=x["rh"])
        .status_code
        == 403
    )
    with x["app"].state.database.sessions.begin() as session:
        session.add(Membership(workspace_id=x["wid"], user_id=x["pid"], role="reviewer"))
    x["app"].state.settings.language_assessment_reviewers[x["pid"]] = ["french"]
    assert decide(x, attempt, headers=x["ph"]).status_code == 403


def test_key_tampering_and_invalid_findings_fail_closed(assessment):
    from app.recruiting.models import LanguageAssessmentKey as Key

    x = assessment
    version = publish(x, synthetic=False)
    attempt = ok(begin(x, version), 201)
    ok(submit(x, attempt))
    body = dict(
        command_key="invalid",
        round=1,
        verdict="qualified",
        findings={"choice": {"accuracy": "met"}, "text": {"clarity": "not_met"}},
        rationale="Synthetic findings",
    )
    route = x["root"] + f"/attempts/{attempt['id']}/decisions"
    assert x["client"].post(route, headers=x["rh"], json=body).status_code == 422
    body["findings"]["text"] = {"unknown": "met"}
    assert x["client"].post(route, headers=x["rh"], json=body).status_code == 422
    with x["app"].state.database.sessions.begin() as session:
        key = session.get(Key, UUID(version["id"]))
        key.material_json = key.material_json | {"answer_keys": {"choice": "a"}}
    assert decide(x, attempt).json()["error"]["code"] == "ASSESSMENT_CONTENT_CHANGED"
    with x["app"].state.database.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Decision)
                .where(Decision.attempt_id == UUID(attempt["id"]))
            )
            == 0
        )


def test_default_disabled_and_legacy_production_disabled(assessment):
    x = assessment
    x["app"].state.settings = x["app"].state.settings.model_copy(
        update={"language_assessment_authority_workspace_id": None}
    )
    assert begin(x, {"id": str(uuid4())}).status_code == 409
    assert ok(x["client"].get(API + "/panel/language-assessments", headers=x["ph"]))["items"] == []
    x["app"].state.settings.app_env = "production"
    response = x["client"].post(
        API + "/panel/qualifications",
        headers=x["ph"],
        json=dict(
            language="fr", assessment_version="development-basic-v1", answers=["chevaux", "sommes"]
        ),
    )
    assert response.status_code == 403
