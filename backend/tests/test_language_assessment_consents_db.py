"""Own consent enumeration remains independent of attempts, catalogue and authority."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_language_assessments_db import API, ok, publish
from test_language_assessments_db import assessment as assessment
from test_recruiting import optin

from app.recruiting import assessment_privacy, assessments
from app.recruiting.models import LanguageAssessmentConsent as Consent
from app.recruiting.models import ParticipantProfile

pytestmark = pytest.mark.db
LIST = API + "/panel/language-assessment-consents"
WRITE = API + "/panel/language-assessment-consent"
FIELDS = {"id", "document_version", "created_at", "withdrawn_at"}


def update(x, decision="granted", grant_id=None, headers=None):
    body = dict(
        decision=decision,
        document_version="1",
        presented_digest=assessments.CONSENT_DIGEST,
        receipt_key="PRIVATE_RECEIPT_CANARY_" + uuid4().hex,
    )
    if grant_id:
        body["grant_id"] = grant_id
    return x["client"].put(WRITE, headers=headers or x["ph"], json=body)


def test_unused_grant_survives_retired_catalogue_and_can_be_withdrawn(assessment):
    x = assessment
    version = publish(x)
    ok(
        x["client"].post(
            x["root"] + f"/versions/{version['id']}/retire",
            headers=x["rh"],
            json={"content_digest": version["content_digest"]},
        )
    )
    x["app"].state.settings.language_assessment_authority_workspace_id = None
    rows = ok(x["client"].get(LIST, headers=x["ph"]))
    assert len(rows["items"]) == 1 and rows["next_offset"] is None
    grant = rows["items"][0]
    assert set(grant) == FIELDS
    assert grant["id"] == x["grant"]["id"] and grant["withdrawn_at"] is None
    assert ok(x["client"].get(API + "/panel/language-qualifications", headers=x["ph"]))[
        "attempts"
    ] == []
    receipt = ok(update(x, "withdrawn", grant["id"]))
    rows = ok(x["client"].get(LIST, headers=x["ph"]))
    assert rows["items"][0]["withdrawn_at"] == receipt["created_at"]
    # Further withdrawals do not erase or shift the first revocation timestamp.
    ok(update(x, "withdrawn", grant["id"]))
    assert ok(x["client"].get(LIST, headers=x["ph"])) == rows


def test_enumeration_is_owner_only_and_never_projects_private_keys(assessment):
    x = assessment
    own = ok(update(x))
    other_h, _, _ = x["actor"]()
    assert ok(x["client"].get(LIST, headers=other_h)) == {"items": [], "next_offset": None}
    optin(x["client"], other_h, languages=["french"])
    foreign = ok(update(x, headers=other_h))
    rows = ok(x["client"].get(LIST, headers=x["ph"]))
    assert {row["id"] for row in rows["items"]} == {own["id"], x["grant"]["id"]}
    assert all(set(row) == FIELDS for row in rows["items"])
    assert foreign["id"] not in str(rows)
    assert "PRIVATE_RECEIPT_CANARY" not in str(rows)
    assert "profile_id" not in str(rows) and "digest" not in str(rows)
    assert update(x, "withdrawn", foreign["id"]).status_code == 404
    assert x["client"].get(LIST).status_code == 401
    # Even authority reviewers receive only their own grants, not global evidence.
    assert ok(x["client"].get(LIST, headers=x["rh"])) == {"items": [], "next_offset": None}


def test_consent_enumeration_pagination_is_bounded_and_stable(assessment):
    x = assessment
    expected = {x["grant"]["id"], ok(update(x))["id"], ok(update(x))["id"]}
    seen = []
    offset = 0
    while offset is not None:
        page = ok(x["client"].get(LIST, headers=x["ph"], params={"offset": offset, "limit": 1}))
        assert len(page["items"]) == 1
        seen.extend(row["id"] for row in page["items"])
        offset = page["next_offset"]
    assert len(seen) == len(set(seen)) == 3 and set(seen) == expected
    assert ok(x["client"].get(LIST + "?offset=100000&limit=100", headers=x["ph"])) == {
        "items": [], "next_offset": None
    }
    for query in ["limit=0", "limit=101", "offset=-1", "offset=100001"]:
        assert x["client"].get(LIST + "?" + query, headers=x["ph"]).status_code == 422


def test_panel_withdrawal_still_allows_own_assessment_consent_management(assessment):
    x = assessment
    with x["app"].state.database.sessions.begin() as session:
        session.get(ParticipantProfile, UUID(x["profile"])).status = "withdrawn"
    grant = ok(x["client"].get(LIST, headers=x["ph"]))["items"][0]
    assert grant["id"] == x["grant"]["id"]
    ok(update(x, "withdrawn", grant["id"]))
    assert ok(x["client"].get(LIST, headers=x["ph"]))["items"][0]["withdrawn_at"]


def test_restored_unused_grant_revocation_is_visible_but_erased_account_is_denied(assessment):
    from app.privacy_ops.account import apply_account_restriction

    x = assessment
    with x["app"].state.database.sessions.begin() as session:
        assessment_privacy.replay_revocations(
            session, [{"profile_id": x["profile"], "grant_id": x["grant"]["id"]}]
        )
        assert session.scalar(select(Consent).where(Consent.grant_id == UUID(x["grant"]["id"])))
    rows = ok(x["client"].get(LIST, headers=x["ph"]))
    assert rows["items"][0]["withdrawn_at"]
    assert "restore:" not in str(rows)
    with x["app"].state.database.sessions.begin() as session:
        apply_account_restriction(session, x["pid"])
    response = x["client"].get(LIST, headers=x["ph"])
    assert response.status_code in {401, 403}
    assert x["grant"]["id"] not in response.text
