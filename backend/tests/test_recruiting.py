from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from study_fixtures import ready_study

from app.auth.models import User
from app.auth.security import utcnow
from app.common.errors import DomainError
from app.recruiting import service
from app.recruiting.models import Candidate, Invitation, PrivateContact, Reservation
from app.recruiting.schemas import Filters
from app.studies.models import Launch


@pytest.mark.parametrize(
    "attrs,filters,expected",
    [
        ({}, {"min_age": 18}, False),
        ({"age": 30}, {"max_age": 25}, False),
        ({"age": 30}, {"min_age": 18, "max_age": 40}, True),
        ({"devices": ["mobile"]}, {"device": "desktop"}, False),
        ({"languages": ["fr"]}, {"verified_language": "fr"}, False),
        ({"verified_languages": ["fr"]}, {"verified_language": "fr"}, True),
        ({}, {}, True),
    ],
)
def test_filters(attrs, filters, expected):
    assert service.matches(attrs, filters) == expected


def test_invalid_filter_ranges():
    with pytest.raises(ValueError):
        Filters(min_age=50, max_age=20)


def test_private_lookup_scope_and_normalization():
    w1, w2 = uuid4(), uuid4()
    assert service.contact_hash("secret", w1, " HELLO@example.test ") == service.contact_hash(
        "secret", w1, "hello@example.test"
    )
    assert service.contact_hash("secret", w1, "hello@example.test") != service.contact_hash(
        "secret", w2, "hello@example.test"
    )


@pytest.fixture
def recruitment(research_app):
    client, app, actor = research_app
    headers, user, workspace = actor()
    base = f"/api/v1/workspaces/{workspace}"
    study = ready_study(client, base, headers)
    pub = client.post(
        study["endpoint"] + "/publish", headers=headers, json={"expected_revision": 2}
    )
    assert pub.status_code == 200, pub.text
    with app.state.database.sessions() as session:
        launch = session.scalar(
            select(Launch).where(Launch.version_id == UUID(study["version_id"]))
        ).id
    root = base + f"/recruiting/launches/{launch}"
    return client, app, actor, headers, user, workspace, base, root, launch


def optin(client, headers, **attrs):
    doc = client.get("/api/v1/panel/consent").json()
    body = {
        "decision": "granted",
        "attributes": attrs,
        "receipt_key": uuid4().hex,
        "document_version": doc["version"],
        "presented_digest": doc["digest"],
    }
    response = client.put("/api/v1/panel/profile", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"], body


def configure(client, headers, root, **overrides):
    body = {"capacity": 1, "budget_millimes": 100, "reward_millimes": 100} | overrides
    result = client.post(root + "/config", headers=headers, json=body)
    assert result.status_code == 201, result.text


def invite(client, headers, root, profile, kind="public"):
    response = client.post(
        root + "/invitations", headers=headers, json={"source_kind": kind, "source_id": profile}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.db
def test_panel_consent_replay_and_qualification(recruitment):
    client, app, actor, h, *_ = recruitment
    profile, body = optin(client, h, languages=["fr"])
    assert client.put("/api/v1/panel/profile", headers=h, json=body).status_code == 200
    assert (
        client.put(
            "/api/v1/panel/profile", headers=h, json=body | {"attributes": {"age": 30}}
        ).status_code
        == 409
    )
    assert (
        client.put(
            "/api/v1/panel/profile", headers=h, json=body | {"presented_digest": "0" * 64}
        ).status_code
        == 409
    )
    assert (
        client.put(
            "/api/v1/panel/profile",
            headers=h,
            json=body | {"attributes": {"verified_languages": ["fr"]}},
        ).status_code
        == 422
    )
    q = client.post(
        "/api/v1/panel/qualifications",
        headers=h,
        json={
            "language": "fr",
            "assessment_version": "development-basic-v1",
            "answers": ["chevaux", "sommes"],
        },
    )
    assert q.status_code == 201, q.text
    assert q.json()["passed"]
    assert client.get("/api/v1/panel/qualifications", headers=h).json()["items"][0]["passed"]


@pytest.mark.db
def test_screeners_token_replay_capacity_and_budget(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(
        client,
        h,
        root,
        screeners={"q": {"prompt": "Choose", "options": ["a", "b"], "eligible_options": ["a"]}},
    )
    ph, pu, _ = actor()
    profile, _ = optin(client, ph, age=25)
    inv = invite(client, h, root, profile)
    token = {"X-Invitation-Token": inv["invitation_token"]}
    info = client.get("/api/v1/recruiting/invitation", headers=token)
    assert "eligible_options" not in info.text
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 409
    assert (
        client.post(
            "/api/v1/recruiting/screen", headers=ph | token, json={"answers": {"q": "forged"}}
        ).status_code
        == 422
    )
    for _ in range(2):
        assert client.post(
            "/api/v1/recruiting/screen", headers=ph | token, json={"answers": {"q": "a"}}
        ).json()["eligible"]
    assert (
        client.post(
            "/api/v1/recruiting/screen", headers=ph | token, json={"answers": {"q": "b"}}
        ).status_code
        == 409
    )
    hold = client.post("/api/v1/recruiting/reserve", headers=ph | token)
    assert hold.status_code == 200, hold.text
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).json() == hold.json()
    assert (
        client.post(
            root + "/invitations", headers=h, json={"source_kind": "public", "source_id": profile}
        ).status_code
        == 409
    )
    with app.state.database.sessions.begin() as s:
        service.resolve_invitation(s, inv["invitation_token"], redeem=True)
    with app.state.database.sessions.begin() as s, pytest.raises(DomainError):
        service.resolve_invitation(s, inv["invitation_token"], redeem=True)
    with app.state.database.sessions.begin() as s:
        service.consume_reservation(s, w, UUID(inv["candidate_id"]))
        assert service.consume_reservation(s, w, UUID(inv["candidate_id"])).state == "consumed"


@pytest.mark.db
def test_private_import_binding_suppression_tenant_boundary(recruitment):
    from research_support import document

    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    with app.state.database.sessions() as s:
        email = s.get(User, pu).email
    doc = document(client, base, h, purpose="private_panel")
    body = {
        "rows": [{"mail": email}, {"mail": email.upper()}],
        "mapping": {"email": "mail"},
        "source": "synthetic opt-in",
        "document_id": doc["id"],
        "consent_confirmed": True,
        "retention_until": (utcnow() + timedelta(days=30)).isoformat(),
    }
    preview = client.post(base + "/recruiting/contacts/import", headers=h, json=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()["accepted"] == 1 and preview.json()["duplicates"] == 1
    created = client.post(
        base + "/recruiting/contacts/import", headers=h, json=body | {"preview": False}
    )
    contact = created.json()["contact_ids"][0]
    assert email not in created.text
    assert (
        client.post(
            base + "/recruiting/contacts/import",
            headers=h,
            json=body | {"preview": False, "duplicate_policy": "reject"},
        ).status_code
        == 409
    )
    inv = invite(client, h, root, contact, "private")
    token = {"X-Invitation-Token": inv["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=h | token).status_code == 403
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 200
    foreign_h, _, foreign_w = actor()
    assert (
        client.post(
            f"/api/v1/workspaces/{foreign_w}/recruiting/contacts/{contact}/suppress",
            headers=foreign_h,
        ).status_code
        == 404
    )
    assert (
        client.post(base + f"/recruiting/contacts/{contact}/suppress", headers=h).status_code == 200
    )
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 403
    with app.state.database.sessions() as s:
        c = s.get(PrivateContact, UUID(contact))
        assert "email" not in c.attributes_json
        assert s.get(Candidate, UUID(inv["candidate_id"])).subject_id == pu


@pytest.mark.db
@pytest.mark.parametrize("failure", ["capacity", "budget", "quota"])
def test_last_slot_concurrent_and_overlap(recruitment, failure):
    client, app, actor, h, user, w, base, root, launch = recruitment
    overrides = {"capacity": 1} if failure == "capacity" else {"capacity": 10}
    if failure == "quota":
        overrides |= {
            "budget_millimes": 1000,
            "quotas": [
                {"capacity": 1, "filters": {"min_age": 18}},
                {"capacity": 1, "filters": {"device": "mobile"}},
            ],
        }
    configure(client, h, root, **overrides)
    candidates = []
    for _ in range(2):
        ph, pu, _ = actor()
        profile, _ = optin(client, ph, age=30, devices=["mobile"])
        inv = invite(client, h, root, profile)
        with app.state.database.sessions.begin() as s:
            service.bind_invitation(s, app.state.settings, inv["invitation_token"], pu)
        candidates.append(UUID(inv["candidate_id"]))

    def reserve(cid):
        try:
            with app.state.database.sessions.begin() as s:
                service.reserve_candidate(s, cid, w)
            return "ok"
        except DomainError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, candidates))
    assert results.count("ok") == 1, results
    assert {"capacity": "CAPACITY_FULL", "budget": "BUDGET_EXHAUSTED", "quota": "QUOTA_FULL"}[
        failure
    ] in results
    with app.state.database.sessions() as s:
        assert (
            s.scalar(
                select(func.count()).select_from(Reservation).where(Reservation.launch_id == launch)
            )
            == 1
        )


@pytest.mark.db
@pytest.mark.parametrize("change", ["expiry", "pause", "withdraw"])
def test_live_revocation_and_expiry(recruitment, change):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    profile, body = optin(client, ph)
    inv = invite(client, h, root, profile)
    token = {"X-Invitation-Token": inv["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 200
    if change == "withdraw":
        assert (
            client.put(
                "/api/v1/panel/profile",
                headers=ph,
                json=body | {"receipt_key": uuid4().hex, "decision": "withdrawn"},
            ).status_code
            == 200
        )
    else:
        with app.state.database.sessions.begin() as s:
            if change == "pause":
                s.get(Launch, launch).state = "paused"
            else:
                s.scalar(select(Reservation).where(Reservation.launch_id == launch)).expires_at = (
                    utcnow() - timedelta(seconds=1)
                )
    with app.state.database.sessions.begin() as s, pytest.raises(DomainError):
        service.consume_reservation(s, w, UUID(inv["candidate_id"]))


@pytest.mark.db
def test_erasure_keeps_capacity_but_removes_snapshot(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    profile, _ = optin(client, ph, age=30)
    inv = invite(client, h, root, profile)
    token = {"X-Invitation-Token": inv["invitation_token"]}
    client.post("/api/v1/recruiting/reserve", headers=ph | token)
    with app.state.database.sessions.begin() as s:
        assert "attributes" not in str(service.access_summary(s, w, pu))
        service.erase_subject(s, w, pu)
    with app.state.database.sessions() as s:
        candidate = s.get(Candidate, UUID(inv["candidate_id"]))
        assert candidate.attributes_json == {} and candidate.source_id is None
        assert (
            s.scalar(select(Reservation).where(Reservation.launch_id == launch)).state == "released"
        )
        assert (
            s.scalar(
                select(Invitation).where(Invitation.candidate_id == UUID(inv["candidate_id"]))
            ).revoked_at
            is not None
        )


@pytest.mark.db
def test_cross_source_identity_deduplication(recruitment):
    from research_support import document

    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root, capacity=5, budget_millimes=500)
    ph, pu, _ = actor()
    profile, _ = optin(client, ph)
    public = invite(client, h, root, profile)
    with app.state.database.sessions() as s:
        email = s.get(User, pu).email
    doc = document(client, base, h, purpose="private_panel")
    body = {
        "rows": [{"email": email}],
        "mapping": {"email": "email"},
        "source": "synthetic consent",
        "document_id": doc["id"],
        "consent_confirmed": True,
        "retention_until": (utcnow() + timedelta(days=30)).isoformat(),
        "preview": False,
    }
    imported = client.post(base + "/recruiting/contacts/import", headers=h, json=body)
    private = invite(client, h, root, imported.json()["contact_ids"][0], "private")
    public_headers = ph | {"X-Invitation-Token": public["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=public_headers).status_code == 200
    private_headers = ph | {"X-Invitation-Token": private["invitation_token"]}
    response = client.post("/api/v1/recruiting/reserve", headers=private_headers)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "ALREADY_PARTICIPATING"


@pytest.mark.db
def test_expired_invite_wrong_identity_and_snapshot_frozen(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    profile, body = optin(client, ph, age=20)
    inv = invite(client, h, root, profile)
    token = {"X-Invitation-Token": inv["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=h | token).status_code == 403
    assert (
        client.put(
            "/api/v1/panel/profile",
            headers=ph,
            json=body | {"receipt_key": uuid4().hex, "attributes": {"age": 50}},
        ).status_code
        == 200
    )
    with app.state.database.sessions.begin() as s:
        assert s.get(Candidate, UUID(inv["candidate_id"])).attributes_json["age"] == 20
        s.get(Invitation, UUID(inv["invitation_id"])).expires_at = utcnow() - timedelta(seconds=1)
    assert client.get("/api/v1/recruiting/invitation", headers=token).status_code == 401
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 401


@pytest.mark.db
def test_expiry_against_submission_serializes(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    profile, _ = optin(client, ph)
    inv = invite(client, h, root, profile)
    token = {"X-Invitation-Token": inv["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 200
    cid = UUID(inv["candidate_id"])

    def settle(action):
        with app.state.database.sessions.begin() as s:
            if action == "submit":
                service.consume_reservation(s, w, cid)
            else:
                service.lock_launch(s, w, launch)
                service.expire_holds(s, w, launch)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(settle, ["submit", "expiry"]))
    with app.state.database.sessions() as s:
        assert (
            s.scalar(select(Reservation).where(Reservation.candidate_id == cid)).state == "consumed"
        )


@pytest.mark.db
def test_database_constraints_and_immutable_receipts(recruitment, db_engine):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    profile, _ = optin(client, h)
    with Session(db_engine) as s, pytest.raises(DBAPIError):
        s.execute(
            text("UPDATE panel_consents SET decision='withdrawn' WHERE profile_id=:id"),
            {"id": profile},
        )
    with Session(db_engine) as s, pytest.raises(DBAPIError):
        s.execute(
            text("UPDATE recruitment_configs SET capacity=99 WHERE launch_id=:id"), {"id": launch}
        )
    with Session(db_engine) as s, pytest.raises(DBAPIError):
        s.execute(
            text(
                "INSERT INTO reservations(id,workspace_id,launch_id,candidate_id,state,expires_at,reward_millimes) VALUES (:id,:w,:launch,:candidate,'held',now(),-1)"
            ),
            {"id": uuid4(), "w": w, "launch": launch, "candidate": uuid4()},
        )


@pytest.mark.db
def test_import_requires_explicit_consent_and_permission(recruitment):
    from research_support import document

    client, app, actor, h, user, w, base, root, launch = recruitment
    doc = document(client, base, h, purpose="private_panel")
    body = {
        "rows": [{"email": "synthetic@example.test"}],
        "mapping": {"email": "email"},
        "source": "synthetic optin",
        "document_id": doc["id"],
        "retention_until": (utcnow() + timedelta(days=1)).isoformat(),
    }
    assert (
        client.post(base + "/recruiting/contacts/import", headers=h, json=body).status_code == 422
    )
    rh, _, _ = actor(workspace_id=w, role="researcher")
    assert (
        client.post(
            base + "/recruiting/contacts/import",
            headers=rh,
            json=body | {"consent_confirmed": True},
        ).status_code
        == 403
    )
    assert client.post(base + "/recruiting/estimate", headers=h, json={}).json() == {
        "count": None,
        "suppressed": True,
        "availability_guaranteed": False,
    }


@pytest.mark.db
@pytest.mark.parametrize("change", ["restriction", "membership", "user", "study", "workspace"])
def test_launch_authority_revocation_denies_participant(recruitment, change):
    from app.auth.models import Membership, Workspace
    from app.common.privacy_models import PrivacyRestriction
    from app.studies.models import Study, StudyVersion

    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    profile, _ = optin(client, ph)
    inv = invite(client, h, root, profile)
    token = {"X-Invitation-Token": inv["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 200
    with app.state.database.sessions.begin() as s:
        if change == "restriction":
            s.add(PrivacyRestriction(workspace_id=w, subject_id=user))
        elif change == "membership":
            s.scalar(
                select(Membership).where(Membership.workspace_id == w, Membership.user_id == user)
            ).status = "revoked"
        elif change == "user":
            s.get(User, user).status = "disabled"
        elif change == "workspace":
            s.get(Workspace, w).status = "suspended"
        else:
            version = s.get(StudyVersion, s.get(Launch, launch).version_id)
            s.get(Study, version.study_id).status = "closed"
    assert client.get("/api/v1/recruiting/invitation", headers=token).status_code in (403, 409)
    with app.state.database.sessions.begin() as s, pytest.raises(DomainError):
        service.consume_reservation(s, w, UUID(inv["candidate_id"]))


@pytest.mark.db
def test_server_selected_recruitment_no_directory_and_deduplication(recruitment):
    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root, capacity=10, budget_millimes=1000)
    profile_ids = []
    user_ids = []
    for _ in range(2):
        ph, pu, _ = actor()
        profile, _ = optin(client, ph, age=119, devices=["tablet"])
        profile_ids.append(profile)
        user_ids.append(str(pu))
    body = {"count": 2, "filters": {"min_age": 119, "max_age": 119, "device": "tablet"}}
    estimate = client.post(
        base + "/recruiting/estimate?source_kind=public", headers=h, json=body["filters"]
    )
    assert estimate.json() == {"count": None, "suppressed": True, "availability_guaranteed": False}
    response = client.post(root + "/recruit-public", headers=h, json=body)
    assert response.status_code == 201, response.text
    assert response.json()["issued"] == 2
    for identifier in profile_ids + user_ids:
        assert identifier not in response.text
    assert "attributes" not in response.text and "email" not in response.text
    assert client.post(root + "/recruit-public", headers=h, json=body).json()["issued"] == 0
    with app.state.database.sessions() as s:
        assert (
            s.scalar(
                select(func.count()).select_from(Candidate).where(Candidate.launch_id == launch)
            )
            == 2
        )
    viewer_h, _, _ = actor(workspace_id=w, role="viewer")
    assert client.post(root + "/recruit-public", headers=viewer_h, json=body).status_code == 403


@pytest.mark.db
def test_private_bound_identity_disable_denies_capability(recruitment):
    from research_support import document

    client, app, actor, h, user, w, base, root, launch = recruitment
    configure(client, h, root)
    ph, pu, _ = actor()
    with app.state.database.sessions() as s:
        email = s.get(User, pu).email
    doc = document(client, base, h, purpose="private_panel")
    imported = client.post(
        base + "/recruiting/contacts/import",
        headers=h,
        json={
            "rows": [{"email": email}],
            "mapping": {"email": "email"},
            "source": "synthetic consent",
            "document_id": doc["id"],
            "consent_confirmed": True,
            "retention_until": (utcnow() + timedelta(days=1)).isoformat(),
            "preview": False,
        },
    )
    inv = invite(client, h, root, imported.json()["contact_ids"][0], "private")
    token = {"X-Invitation-Token": inv["invitation_token"]}
    assert client.post("/api/v1/recruiting/reserve", headers=ph | token).status_code == 200
    with app.state.database.sessions.begin() as s:
        s.get(User, pu).status = "disabled"
    assert client.get("/api/v1/recruiting/invitation", headers=token).status_code == 409
    with app.state.database.sessions.begin() as s, pytest.raises(DomainError):
        service.consume_reservation(s, w, UUID(inv["candidate_id"]))
