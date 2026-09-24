"""Offline erasure protocol tests; deliberately no database connections."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.auth.security import token_hash
from app.common.errors import DomainError
from app.privacy_ops import account
from app.privacy_ops.account_router import AccountErasureBody, StatusBody


def body(**overrides):
    values = dict(
        request_key=uuid4(),
        current_password="current password",
        confirmation="ERASE MY ACCOUNT",
        status_capability="ab" * 32,
    )
    values.update(overrides)
    return values


def test_self_service_schema_rejects_subject_override_and_weak_receipts():
    assert AccountErasureBody(**body()).status_capability == "ab" * 32
    for extra in (
        {"subject_id": str(uuid4())},
        {"confirmation": "yes"},
        {"status_capability": "short"},
        {"request_key": "free-text-email@example.com"},
    ):
        with pytest.raises(ValidationError):
            AccountErasureBody(**body(**extra))
    with pytest.raises(ValidationError):
        StatusBody(request_key=uuid4(), status_capability="ab" * 32, subject_id=uuid4())


def test_status_capability_is_hashed_and_not_a_uuid_only_receipt():
    row = SimpleNamespace(capability_hash=token_hash("ab" * 32))
    session = SimpleNamespace(scalar=lambda query: row)
    assert account.status_receipt(session, uuid4(), "ab" * 32) is row
    with pytest.raises(DomainError) as exc:
        account.status_receipt(session, uuid4(), "cd" * 32)
    assert exc.value.status == 404
    session.scalar = lambda query: None
    with pytest.raises(DomainError) as exc:
        account.status_receipt(session, uuid4(), "ab" * 32)
    assert exc.value.status == 404


def test_workspace_locks_are_sorted(monkeypatch):
    ids = [uuid4() for _ in range(4)]
    calls = []
    monkeypatch.setattr(account.privacy, "lock_workspace", lambda session, wid: calls.append(wid))
    account._lock_scopes(object(), ids)
    assert calls == sorted(ids, key=str)


def test_hold_and_unsettled_rewards_are_explicit_denials(monkeypatch):
    monkeypatch.setattr(account, "workspace_held", lambda session, wid: True)
    with pytest.raises(DomainError) as exc:
        account._check_obligations(None, uuid4(), [uuid4()])
    assert exc.value.code == "ACCOUNT_ERASURE_HELD"
    monkeypatch.setattr(account, "workspace_held", lambda session, wid: False)
    with pytest.raises(DomainError) as exc:
        account._check_obligations(SimpleNamespace(scalar=lambda query: uuid4()), uuid4(), [])
    assert exc.value.code == "ACCOUNT_ERASURE_FINANCIAL_PENDING"


def test_last_owner_requires_another_active_owner():
    session = SimpleNamespace(scalars=lambda query: [uuid4()], scalar=lambda query: None)
    with pytest.raises(DomainError) as exc:
        account._check_last_owner(session, uuid4())
    assert exc.value.status == 409
    assert exc.value.code == "LAST_OWNER"
    session.scalar = lambda query: uuid4()
    account._check_last_owner(session, uuid4())


def test_global_identity_minimized_and_replay_idempotent():
    user = SimpleNamespace(
        id=uuid4(),
        status="active",
        auth_version=3,
        email="private@example.com",
        display_name="Private",
        password_hash="private",
        verified_at=object(),
    )
    profile = SimpleNamespace(id=uuid4(), attributes_json={"private": "value"}, status="active")
    statements = []
    session = SimpleNamespace(
        scalar=lambda query: user,
        scalars=lambda query: [profile],
        execute=statements.append,
        flush=lambda: None,
    )
    account.apply_account_restriction(session, user.id)
    assert user.status == "disabled" and user.auth_version == 4
    assert user.email == f"erased-{user.id}@invalid.example"
    assert user.display_name == "" and user.password_hash == "!account-erased"
    assert user.verified_at is None
    assert profile.attributes_json == {} and profile.status == "withdrawn"
    sql = " ".join(str(statement) for statement in statements)
    assert "DELETE FROM qualifications" in sql
    assert "DELETE FROM one_time_tokens" in sql
    assert "UPDATE refresh_tokens" in sql
    assert "panel_consents" not in sql
    account.apply_account_restriction(session, user.id)
    assert user.auth_version == 4


def test_incomplete_workspace_job_never_reports_global_completion(monkeypatch):
    row = SimpleNamespace(
        id=uuid4(),
        workspace_ids=[str(uuid4())],
        subject_id=uuid4(),
        request_key=uuid4(),
        state="pending",
    )
    results = iter([row, None])
    session = SimpleNamespace(get=lambda *args: row, scalar=lambda query: next(results))
    monkeypatch.setattr(account, "_lock_scopes", lambda *args: None)
    monkeypatch.setattr(account, "_check_obligations", lambda *args: None)
    monkeypatch.setattr(account, "affected_workspaces", lambda *args: [])
    assert account.process_account(session, row.id).state == "pending"


@pytest.mark.db
def test_account_erasure_real_api_and_workspace_completion(research_app):
    from datetime import timedelta

    from sqlalchemy import select

    from app.auth.models import User, WorkspaceInvite
    from app.auth.security import password_hasher, utcnow
    from app.common import privacy
    from app.common.privacy_models import PrivacyRequest
    from app.recruiting.models import ParticipantProfile, Qualification

    client, app, actor = research_app
    headers, uid, wid = actor()
    _, other, _ = actor(wid, role="owner")
    with app.state.database.sessions.begin() as session:
        user = session.get(User, uid)
        user.password_hash = password_hasher.hash("current password")
        profile = ParticipantProfile(user_id=uid, attributes_json={"age": 37, "private": "erase"})
        session.add(profile)
        session.flush()
        session.add(
            Qualification(
                profile_id=profile.id,
                language="fr",
                assessment_version="v1",
                passed=True,
                expires_at=utcnow() + timedelta(days=1),
            )
        )
        invite = WorkspaceInvite(
            workspace_id=wid,
            invited_by=other,
            email=user.email,
            role="viewer",
            token_hash=token_hash(str(uuid4())),
            expires_at=utcnow() + timedelta(days=1),
        )
        session.add(invite)
        session.flush()
        invite_id = invite.id
    payload = body()
    payload["request_key"] = str(payload["request_key"])
    root = "/api/v1/account/erasure"
    wrong = client.post(root, headers=headers, json=payload | {"current_password": "wrong"})
    assert wrong.status_code == 401, wrong.text
    response = client.post(root, headers=headers, json=payload)
    assert response.status_code == 202, response.text
    assert response.json()["state"] == "pending"
    receipt = {key: payload[key] for key in ("request_key", "status_capability")}
    assert (
        client.post(root + "/status", json=receipt | {"status_capability": "cd" * 32}).status_code
        == 404
    )
    assert client.post(root + "/status", json=receipt).json()["state"] == "pending"
    assert client.post(root, headers=headers, json=payload).status_code == 401
    with app.state.database.sessions() as session:
        user = session.get(User, uid)
        assert user.status == "disabled" and user.display_name == ""
        assert user.email == f"erased-{uid}@invalid.example"
        assert session.get(WorkspaceInvite, invite_id).email == user.email
        assert session.get(WorkspaceInvite, invite_id).revoked_at is not None
        assert (
            session.scalar(
                select(ParticipantProfile).where(ParticipantProfile.user_id == uid)
            ).attributes_json
            == {}
        )
        assert (
            session.scalar(
                select(Qualification.id)
                .join(ParticipantProfile)
                .where(ParticipantProfile.user_id == uid)
            )
            is None
        )
        requests = [
            (row.workspace_id, row.id)
            for row in session.scalars(
                select(PrivacyRequest).where(
                    PrivacyRequest.subject_id == uid,
                    PrivacyRequest.request_key == f"account-{payload['request_key']}",
                )
            )
        ]
    assert requests
    for workspace_id, request_id in requests:
        task = SimpleNamespace(workspace_id=workspace_id, target_id=request_id)
        privacy.erase_files(app.state.database, app.state.settings, task)
        with app.state.database.sessions.begin() as session:
            privacy.lock_workspace(session, workspace_id)
            privacy.finish_erasure(session, task)
    completed = client.post(root + "/status", json=receipt)
    assert completed.status_code == 200, completed.text
    assert completed.json()["state"] == "completed"
    assert client.post(root + "/status", json=receipt).json() == completed.json()


@pytest.mark.db
def test_account_last_owner_and_hold_denials_are_atomic(research_app):
    from datetime import timedelta

    from sqlalchemy import select

    from app.auth.models import User
    from app.auth.security import password_hasher, utcnow
    from app.privacy_ops.account_models import AccountErasure
    from app.privacy_ops.models import LegalHold

    client, app, actor = research_app
    headers, uid, wid = actor()
    with app.state.database.sessions.begin() as session:
        user = session.get(User, uid)
        user.password_hash = password_hasher.hash("current password")
        email = user.email
    payload = body()
    payload["request_key"] = str(payload["request_key"])
    root = "/api/v1/account/erasure"
    denied = client.post(root, headers=headers, json=payload)
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "LAST_OWNER"
    _, reviewer, _ = actor(wid, role="owner")
    with app.state.database.sessions.begin() as session:
        session.add(
            LegalHold(
                workspace_id=wid,
                subject_id=uid,
                reviewed_by=reviewer,
                reason="Synthetic evidence hold",
                review_deadline=utcnow() + timedelta(days=1),
            )
        )
    denied = client.post(root, headers=headers, json=payload)
    assert denied.status_code == 409 and denied.json()["error"]["code"] == "ACCOUNT_ERASURE_HELD"
    with app.state.database.sessions() as session:
        user = session.get(User, uid)
        assert user.status == "active" and user.email == email
        assert (
            session.scalar(select(AccountErasure.id).where(AccountErasure.subject_id == uid))
            is None
        )
