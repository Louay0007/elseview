"""PostgreSQL targeting regressions; run only via the dedicated guarded DB runner."""

import json
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from research_support import document
from sqlalchemy import func, select
from test_recruiting import configure, invite
from test_recruiting import recruitment as recruitment

from app.auth.models import User
from app.auth.security import utcnow
from app.recruiting import service
from app.recruiting.models import (
    Candidate,
    PanelConsent,
    ParticipantProfile,
    PrivateContact,
    QuotaCell,
    RecruitmentConfig,
    ReservationCell,
)

pytestmark = pytest.mark.db
EXPERIENCE = {"version": "1", "categories": {"software": "advanced", "research": "beginner"}}
TARGETING = {"country_id": "TN", "city_id": "geonames:2464470", "experience": EXPERIENCE}


def targeting_optin(client, headers, attributes=None):
    doc = client.get("/api/v1/panel/consent?version=2").json()
    body = {
        "decision": "granted",
        "document_version": doc["version"],
        "presented_digest": doc["digest"],
        "receipt_key": uuid4().hex,
        "attributes": TARGETING if attributes is None else attributes,
    }
    response = client.put("/api/v1/panel/profile", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json(), body


def import_body(client, base, headers, rows):
    doc = document(client, base, headers, purpose="private_panel")
    return {
        "rows": rows,
        "mapping": {
            "email": "mail",
            "country_id": "nation",
            "city_id": "city",
            "experience": "work",
        },
        "source": "synthetic targeting permission",
        "document_id": doc["id"],
        "consent_confirmed": True,
        "retention_until": (utcnow() + timedelta(days=30)).isoformat(),
        "targeting_consent": {
            "version": "1",
            "purpose": "private_panel_targeting",
            "confirmed": True,
            "presented_digest": service.PRIVATE_TARGETING_DIGEST,
            "document_digest": doc["digest"],
        },
    }


def targeting_row(email):
    return {
        "mail": email,
        "nation": "TN",
        "city": "geonames:2464470",
        "work": json.dumps(EXPERIENCE),
    }


def test_targeting_public_consent_replay_clear_and_persisted_provenance(recruitment):
    client, app, actor, h, user, *_ = recruitment
    legacy = client.get("/api/v1/panel/consent").json()
    denied = client.put(
        "/api/v1/panel/profile",
        headers=h,
        json={
            "decision": "granted",
            "document_version": "1",
            "presented_digest": legacy["digest"],
            "receipt_key": uuid4().hex,
            "attributes": TARGETING,
        },
    )
    assert denied.status_code == 422
    output, body = targeting_optin(client, h)
    assert output["attributes"]["experience"] == EXPERIENCE
    assert output["targeting_provenance"]["source"] == "self_reported"
    assert client.put("/api/v1/panel/profile", headers=h, json=body).json() == output
    assert client.get("/api/v1/panel/profile", headers=h).json() == output
    assert (
        client.put(
            "/api/v1/panel/profile", headers=h, json=body | {"attributes": {"country_id": "FR"}}
        ).status_code
        == 409
    )
    with app.state.database.sessions() as session:
        receipt = session.scalar(
            select(PanelConsent).where(PanelConsent.profile_id == UUID(output["id"]))
        )
        assert receipt.document_version == "2"
        assert receipt.document_digest == service.PANEL_TARGETING_DIGEST
    cleared, _ = targeting_optin(client, h, {})
    assert all(cleared["attributes"][key] is None for key in service.TARGETING_FIELDS)
    assert cleared["targeting_provenance"] is None


def test_targeting_legacy_persisted_receipt_replays_without_new_defaults(recruitment):
    client, app, actor, h, user, *_ = recruitment
    body = {
        "decision": "granted",
        "document_version": "1",
        "presented_digest": service.PANEL_DIGEST,
        "receipt_key": uuid4().hex,
        "attributes": {"age": 30, "devices": [], "languages": []},
    }
    with app.state.database.sessions.begin() as session:
        profile = ParticipantProfile(
            user_id=user, status="active", attributes_json=body["attributes"]
        )
        session.add(profile)
        session.flush()
        session.add(
            PanelConsent(
                profile_id=profile.id,
                decision="granted",
                document_version="1",
                document_digest=service.PANEL_DIGEST,
                request_digest=service.digest(body),
                receipt_key=body["receipt_key"],
            )
        )
    result = client.put("/api/v1/panel/profile", headers=h, json=body)
    assert result.status_code == 200, result.text
    assert result.json()["attributes"] == body["attributes"]
    assert result.json()["targeting_provenance"] is None


def test_targeting_private_import_preview_consent_scope_and_no_panel_merge(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    other_h, _, other_w = actor()
    other_base = f"/api/v1/workspaces/{other_w}"
    email = f"targeting-{uuid4().hex}@example.test"
    bodies = [
        import_body(client, b, headers, [targeting_row(email)])
        for b, headers in [(base, h), (other_base, other_h)]
    ]
    endpoint = base + "/recruiting/contacts/import"
    with app.state.database.sessions() as session:
        profiles_before = session.scalar(select(func.count()).select_from(ParticipantProfile))
    for preview in [True, False]:
        assert (
            client.post(
                endpoint,
                headers=h,
                json=bodies[0] | {"preview": preview, "targeting_consent": None},
            ).status_code
            == 422
        )
        invalid = bodies[0]["targeting_consent"] | {"document_digest": "0" * 64}
        assert (
            client.post(
                endpoint,
                headers=h,
                json=bodies[0] | {"preview": preview, "targeting_consent": invalid},
            ).status_code
            == 409
        )
    preview = client.post(endpoint, headers=h, json=bodies[0])
    assert preview.status_code == 200, preview.text
    assert preview.json()["contact_ids"] == []
    assert preview.json()["targeting_summary"]["experience"] == {"known": 1, "unknown": 0}
    with app.state.database.sessions() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(PrivateContact)
                .where(PrivateContact.workspace_id == w)
            )
            == 0
        )
    ids = []
    for b, headers, body in [(base, h, bodies[0]), (other_base, other_h, bodies[1])]:
        result = client.post(
            b + "/recruiting/contacts/import", headers=headers, json=body | {"preview": False}
        )
        assert result.status_code == 200, result.text
        ids.append(UUID(result.json()["contact_ids"][0]))
    with app.state.database.sessions() as session:
        contacts = [session.get(PrivateContact, contact_id) for contact_id in ids]
        assert contacts[0].contact_lookup_hash != contacts[1].contact_lookup_hash
        assert {
            contact.attributes_json["_targeting_provenance"]["workspace_id"] for contact in contacts
        } == {str(w), str(other_w)}
        assert (
            session.scalar(select(func.count()).select_from(ParticipantProfile)) == profiles_before
        )
    configure(client, h, root, filters=TARGETING)
    assert (
        client.post(
            root + "/invitations",
            headers=h,
            json={"source_kind": "private", "source_id": str(ids[1])},
        ).status_code
        == 404
    )


def test_targeting_estimates_and_unknown_imports_share_matcher(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    rows = [targeting_row(f"targeting-{uuid4().hex}@example.test") for _ in range(5)]
    rows.append({"mail": f"unknown-{uuid4().hex}@example.test"})
    body = import_body(client, base, h, rows)
    created = client.post(
        base + "/recruiting/contacts/import", headers=h, json=body | {"preview": False}
    )
    assert created.status_code == 200, created.text
    assert created.json()["targeting_summary"]["country_id"] == {"known": 5, "unknown": 1}
    endpoint = base + "/recruiting/estimate"
    assert client.post(endpoint, headers=h, json={}).json()["count"] == 6
    assert client.post(endpoint, headers=h, json=TARGETING).json()["count"] == 5
    suppressed = client.post(endpoint, headers=h, json={"country_id": "FR"}).json()
    assert suppressed["count"] is None and suppressed["suppressed"]
    assert (
        client.post(
            endpoint,
            headers=h,
            json={"experience": {"version": "2", "categories": {"software": "advanced"}}},
        ).status_code
        == 422
    )


def test_targeting_public_recruitment_screeners_frozen_snapshot_and_overlapping_quotas(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    # An isolated city keeps the public candidate window independent of other fixtures.
    targeting = TARGETING | {"city_id": f"geonames:{int(uuid4().hex[:7], 16) + 1}"}
    configure(
        client,
        h,
        root,
        capacity=10,
        budget_millimes=1000,
        filters=targeting,
        quotas=[
            {"capacity": 1, "filters": {"country_id": "TN"}},
            {"capacity": 1, "filters": {"experience": EXPERIENCE}},
        ],
        screeners={
            "q": {
                "prompt": "Self-reported software familiarity?",
                "options": ["yes", "no"],
                "eligible_options": ["yes"],
            }
        },
    )
    actors = []
    for _ in range(5):
        ph, pu, _ = actor()
        output, _ = targeting_optin(client, ph, targeting)
        actors.append((ph, pu, output["id"]))
    estimate = client.post(
        base + "/recruiting/estimate?source_kind=public", headers=h, json=targeting
    )
    assert estimate.json()["count"] == 5
    recruited = client.post(
        root + "/recruit-public", headers=h, json={"count": 2, "filters": targeting}
    )
    assert recruited.status_code == 201, recruited.text
    assert recruited.json()["issued"] == 2
    with app.state.database.sessions() as session:
        config = session.scalar(
            select(RecruitmentConfig).where(RecruitmentConfig.launch_id == launch)
        )
        assert config.filters_json["experience"] == EXPERIENCE
        assert (
            len(list(session.scalars(select(QuotaCell).where(QuotaCell.launch_id == launch)))) == 2
        )
        subjects = {
            item["candidate_id"]: session.get(Candidate, UUID(item["candidate_id"])).subject_id
            for item in recruited.json()["items"]
        }
    holds = []
    for item in recruited.json()["items"]:
        ph = next(headers for headers, uid, _ in actors if uid == subjects[item["candidate_id"]])
        targeting_optin(client, ph, {"country_id": "FR"})
        token = {"X-Invitation-Token": item["invitation_token"]}
        assert client.post(
            "/api/v1/recruiting/screen", headers=ph | token, json={"answers": {"q": "yes"}}
        ).json()["eligible"]
        holds.append(client.post("/api/v1/recruiting/reserve", headers=ph | token))
        with app.state.database.sessions() as session:
            candidate = session.get(Candidate, UUID(item["candidate_id"]))
            assert candidate.attributes_json["experience"] == EXPERIENCE
            assert candidate.attributes_json["country_id"] == "TN"
            assert candidate.attributes_json["_targeting_provenance"]["source"] == "self_reported"
    assert [response.status_code for response in holds] == [200, 409]
    assert holds[1].json()["error"]["code"] == "QUOTA_FULL"
    with app.state.database.sessions() as session:
        reservation_id = UUID(holds[0].json()["reservation_id"])
        assert (
            session.scalar(
                select(func.count())
                .select_from(ReservationCell)
                .where(ReservationCell.reservation_id == reservation_id)
            )
            == 2
        )


def test_targeting_private_binding_preserves_private_snapshot_not_public_profile(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(
        client,
        h,
        root,
        filters=TARGETING,
        quotas=[{"capacity": 1, "filters": {"experience": EXPERIENCE}}],
    )
    ph, pu, _ = actor()
    profile, _ = targeting_optin(client, ph, {"country_id": "FR"})
    with app.state.database.sessions() as session:
        email = session.get(User, pu).email
    body = import_body(client, base, h, [targeting_row(email)])
    response = client.post(
        base + "/recruiting/contacts/import", headers=h, json=body | {"preview": False}
    )
    contact_id = response.json()["contact_ids"][0]
    invitation = invite(client, h, root, contact_id, "private")
    with app.state.database.sessions.begin() as session:
        contact = session.get(PrivateContact, UUID(contact_id))
        contact.attributes_json = {"country_id": "FR"}
    token = {"X-Invitation-Token": invitation["invitation_token"]}
    hold = client.post("/api/v1/recruiting/reserve", headers=ph | token)
    assert hold.status_code == 200, hold.text
    with app.state.database.sessions() as session:
        candidate = session.get(Candidate, UUID(invitation["candidate_id"]))
        assert candidate.subject_id == pu and candidate.source_kind == "private"
        assert candidate.attributes_json["country_id"] == "TN"
        assert candidate.attributes_json["experience"] == EXPERIENCE
        assert candidate.attributes_json["_targeting_provenance"]["source"] == "workspace_import"
        assert (
            session.get(ParticipantProfile, UUID(profile["id"])).attributes_json["country_id"]
            == "FR"
        )
