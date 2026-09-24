import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import AuditEvent, Membership, OneTimeToken, RefreshToken, User, Workspace
from app.auth.security import token_hash, utcnow
from app.auth.service import change_member, create_workspace, require_workspace
from app.common.errors import DomainError
from app.main import create_app

pytestmark = pytest.mark.db
PASSWORD = "Synthetic-passphrase-2026!"
ORIGIN = {"origin": "http://localhost:8080"}


class AllowLimiter:
    def check(self, *args, **kwargs):
        pass

    def close(self):
        pass


@pytest.fixture
def auth_app(settings, db_engine, monkeypatch):
    config = settings.model_copy(
        update={"database_url": SecretStr(db_engine.url.render_as_string(hide_password=False))}
    )
    app = create_app(config)
    app.state.rate_limiter.close()
    app.state.rate_limiter = AllowLimiter()
    delivered = []
    app.state.auth.deliver = lambda email, purpose, token: delivered.append((email, purpose, token))
    with TestClient(app) as client:
        yield client, delivered, config


def register(client, delivered, prefix="person"):
    email = f"{prefix}-{uuid4().hex}@example.test"
    result = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD, "display_name": "Utilisateur تجريبي"},
    )
    assert result.status_code == 202, result.text
    raw = next(t for e, p, t in reversed(delivered) if e == email and p == "verify")
    assert (
        client.post("/api/v1/auth/verify-email", headers=ORIGIN, json={"token": raw}).status_code
        == 200
    )
    result = client.post(
        "/api/v1/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD}
    )
    assert result.status_code == 200, result.text
    body = result.json()
    return email, {"authorization": "Bearer " + body["access_token"]}, body


def test_full_registration_and_no_plaintext_tokens(auth_app, db_engine):
    client, delivered, config = auth_app
    email, headers, login = register(client, delivered)
    assert "refresh_token" not in login
    assert client.get("/api/v1/me", headers=headers).json()["email"] == email
    with Session(db_engine) as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user.password_hash.startswith("$argon2") and PASSWORD not in user.password_hash
        raw = delivered[-1][2]
        assert session.scalar(
            select(OneTimeToken).where(OneTimeToken.user_id == user.id)
        ).token_hash == token_hash(raw)
        assert session.scalar(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        ).token_hash != client.cookies.get("elseview_refresh")
        assert not any(
            raw in json.dumps(a.details)
            for a in session.scalars(select(AuditEvent).where(AuditEvent.actor_id == user.id))
        )
    assert (
        client.post("/api/v1/auth/verify-email", headers=ORIGIN, json={"token": raw}).status_code
        == 400
    )
    before = len(delivered)
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": email.upper(), "password": PASSWORD},
        ).status_code
        == 202
    )
    assert len(delivered) == before


def test_unverified_bad_password_disabled_user(auth_app, db_engine):
    client, delivered, _ = auth_app
    email = f"unverified-{uuid4().hex}@example.test"
    client.post(
        "/api/v1/auth/register", headers=ORIGIN, json={"email": email, "password": PASSWORD}
    )
    for candidate, pwd in [(email, PASSWORD), (email, "wrong"), ("missing@example.test", PASSWORD)]:
        result = client.post(
            "/api/v1/auth/login", headers=ORIGIN, json={"email": candidate, "password": pwd}
        )
        assert result.status_code == 401
        assert "access_token" not in result.text
    email, headers, _ = register(client, delivered)
    with Session(db_engine) as session, session.begin():
        session.scalar(select(User).where(User.email == email)).status = "disabled"
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_refresh_rotation_csrf_and_replay_revokes_family(auth_app):
    client, delivered, _ = auth_app
    _, headers, first = register(client, delivered)
    old_cookie = client.cookies.get("elseview_refresh")
    assert client.post("/api/v1/auth/refresh", headers=ORIGIN).status_code == 403
    result = client.post(
        "/api/v1/auth/refresh", headers=ORIGIN | {"x-csrf-token": first["csrf_token"]}
    )
    assert result.status_code == 200
    assert result.json()["csrf_token"] != first["csrf_token"]
    assert client.cookies.get("elseview_refresh") != old_cookie
    second = {"authorization": "Bearer " + result.json()["access_token"]}
    # Explicit raw Cookie header simulates replay by a stolen old token holder.
    result = client.post(
        "/api/v1/auth/refresh",
        headers=ORIGIN
        | {"cookie": f"elseview_refresh={old_cookie}", "x-csrf-token": first["csrf_token"]},
    )
    assert result.status_code == 401
    assert client.get("/api/v1/me", headers=second).status_code == 401
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_reset_generic_response_expiry_and_all_sessions_revoked(auth_app, db_engine):
    client, delivered, _ = auth_app
    email, old, _ = register(client, delivered)
    known = client.post(
        "/api/v1/auth/password-reset/request", headers=ORIGIN, json={"email": email}
    )
    unknown = client.post(
        "/api/v1/auth/password-reset/request", headers=ORIGIN, json={"email": "nobody@example.test"}
    )
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    token = delivered[-1][2]
    with Session(db_engine) as session, session.begin():
        session.scalar(
            select(OneTimeToken).where(OneTimeToken.token_hash == token_hash(token))
        ).expires_at = utcnow() - timedelta(seconds=1)
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm",
            headers=ORIGIN,
            json={"token": token, "password": PASSWORD + "new"},
        ).status_code
        == 400
    )
    client.post("/api/v1/auth/password-reset/request", headers=ORIGIN, json={"email": email})
    token = delivered[-1][2]
    result = client.post(
        "/api/v1/auth/password-reset/confirm",
        headers=ORIGIN,
        json={"token": token, "password": PASSWORD + "new"},
    )
    assert result.status_code == 200
    assert client.get("/api/v1/me", headers=old).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm",
            headers=ORIGIN,
            json={"token": token, "password": PASSWORD},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": email, "password": PASSWORD + "new"},
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "change",
    [
        {"aud": "another"},
        {"iss": "another"},
        {"exp": 1},
        {"type": "refresh"},
        {"sub": "not-uuid"},
        {"ver": "0"},
        {"nbf": 9999999999},
    ],
)
def test_jwt_claims_rejected(auth_app, change):
    client, delivered, settings = auth_app
    _, _, login = register(client, delivered)
    claims = jwt.decode(login["access_token"], options={"verify_signature": False})
    claims.update(change)
    raw = jwt.encode(claims, settings.secret_key.get_secret_value(), algorithm="HS256")
    assert client.get("/api/v1/me", headers={"authorization": "Bearer " + raw}).status_code == 401


def test_logout_session_revoke_and_cookie_policy(auth_app):
    client, delivered, _ = auth_app
    _, headers, login = register(client, delivered)
    assert client.get("/api/v1/me/login-sessions", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers | ORIGIN).status_code == 403
    assert (
        client.post(
            "/api/v1/auth/logout", headers=headers | ORIGIN | {"x-csrf-token": login["csrf_token"]}
        ).status_code
        == 204
    )
    assert client.cookies.get("elseview_refresh") is None
    assert client.get("/api/v1/me", headers=headers).status_code == 401


def test_workspaces_invites_roles_and_cross_tenant(auth_app, db_engine):
    client, delivered, _ = auth_app
    owner_email, owner, _ = register(client, delivered, "owner")
    workspace = client.post("/api/v1/workspaces", headers=owner, json={"name": "Elseview A"}).json()
    wid = workspace["id"]
    assert workspace["country"] == "TN" and workspace["timezone"] == "Africa/Tunis"
    other_email, other, _ = register(client, delivered, "other")
    assert client.get(f"/api/v1/workspaces/{wid}", headers=other).status_code == 404
    assert client.get(f"/api/v1/workspaces/{wid}").status_code == 401
    response = client.post(
        f"/api/v1/workspaces/{wid}/invitations",
        headers=owner,
        json={"email": other_email, "role": "researcher"},
    )
    assert response.status_code == 202
    token = delivered[-1][2]
    accepted = client.post(
        "/api/v1/workspace-invitations/accept", headers=other, json={"token": token}
    )
    assert accepted.status_code == 200, accepted.text
    member = accepted.json()["id"]
    assert (
        client.post(
            "/api/v1/workspace-invitations/accept", headers=other, json={"token": token}
        ).json()["id"]
        == member
    )
    assert client.get(f"/api/v1/workspaces/{wid}", headers=other).status_code == 200
    assert client.get(f"/api/v1/workspaces/{wid}/members", headers=other).status_code == 403
    assert (
        client.patch(
            f"/api/v1/workspaces/{wid}/members/{member}", headers=other, json={"role": "owner"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/workspaces/{wid}/members/{member}", headers=owner, json={"role": "admin"}
        ).status_code
        == 200
    )
    # Admin cannot create another admin or promote itself to owner.
    assert (
        client.patch(
            f"/api/v1/workspaces/{wid}/members/{member}", headers=other, json={"role": "owner"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/workspaces/{wid}/invitations",
            headers=other,
            json={"email": "x@example.test", "role": "admin"},
        ).status_code
        == 403
    )
    members = client.get(f"/api/v1/workspaces/{wid}/members", headers=owner).json()["items"]
    owner_id = next(m["id"] for m in members if m["role"] == "owner")
    assert (
        client.delete(f"/api/v1/workspaces/{wid}/members/{owner_id}", headers=owner).status_code
        == 409
    )
    assert (
        client.delete(f"/api/v1/workspaces/{wid}/members/{member}", headers=owner).status_code
        == 204
    )
    assert client.get(f"/api/v1/workspaces/{wid}", headers=other).status_code == 404
    audit = client.get(f"/api/v1/workspaces/{wid}/audit", headers=owner)
    assert audit.status_code == 200 and token not in audit.text and owner_email not in audit.text


@pytest.mark.parametrize("role", ["owner", "admin", "researcher", "reviewer", "viewer"])
def test_capability_matrix(db_engine, role):
    with Session(db_engine) as session, session.begin():
        user = User(
            email=f"matrix-{uuid4().hex}@example.test", password_hash="unused", verified_at=utcnow()
        )
        session.add(user)
        session.flush()
        ws = Workspace(name="matrix")
        session.add(ws)
        session.flush()
        member = Membership(user_id=user.id, workspace_id=ws.id, role=role)
        session.add(member)
        session.flush()
        assert require_workspace(session, user.id, ws.id, "workspace.read").id == member.id
        for capability in ["members.manage", "jobs.create", "audit.read"]:
            allowed = role in (
                {"owner", "admin", "researcher"}
                if capability == "jobs.create"
                else {"owner", "admin"}
            )
            if allowed:
                require_workspace(session, user.id, ws.id, capability)
            else:
                with pytest.raises(DomainError) as exc:
                    require_workspace(session, user.id, ws.id, capability)
                assert exc.value.status == 403


def test_two_owners_cannot_both_remove_last_owner(db_engine):
    with Session(db_engine) as session, session.begin():
        users = [
            User(
                email=f"owner-{uuid4().hex}@example.test",
                password_hash="unused",
                verified_at=utcnow(),
            )
            for _ in range(2)
        ]
        session.add_all(users)
        session.flush()
        ws = create_workspace(session, users[0].id, "race")
        second = Membership(workspace_id=ws.id, user_id=users[1].id, role="owner")
        session.add(second)
        session.flush()
        first = session.scalar(
            select(Membership).where(
                Membership.workspace_id == ws.id, Membership.user_id == users[0].id
            )
        )
        values = [(users[0].id, first.id), (users[1].id, second.id)]
        wid = ws.id
    barrier = Barrier(2)

    def remove(value):
        barrier.wait()
        try:
            with Session(db_engine) as session, session.begin():
                change_member(session, value[0], wid, value[1])
            return "removed"
        except DomainError as exc:
            return exc.code

    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(remove, values))
    assert sorted(results) == ["LAST_OWNER", "removed"]
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(
                    Membership.workspace_id == wid,
                    Membership.status == "active",
                    Membership.role == "owner",
                )
            )
            == 1
        )


def test_csrf_origin_is_required_before_credentials(auth_app):
    client, _, _ = auth_app
    for headers in [{}, {"origin": "https://attacker.example"}]:
        assert (
            client.post(
                "/api/v1/auth/login",
                headers=headers,
                json={"email": "some@example.test", "password": "password"},
            ).status_code
            == 403
        )


def test_jobs_api_uses_real_auth(auth_app):
    client, delivered, _ = auth_app
    _, actor, _ = register(client, delivered)
    wid = client.post("/api/v1/workspaces", headers=actor, json={"name": "Job workspace"}).json()[
        "id"
    ]
    result = client.post(
        f"/api/v1/workspaces/{wid}/jobs", headers=actor, json={"command_key": "check"}
    )
    assert result.status_code == 202, result.text
    jid = result.json()["id"]
    assert (
        client.post(
            f"/api/v1/workspaces/{wid}/jobs", headers=actor, json={"command_key": "check"}
        ).json()["id"]
        == jid
    )
    assert client.get(f"/api/v1/workspaces/{wid}/jobs/{jid}").status_code == 401
    _, other, _ = register(client, delivered)
    assert client.get(f"/api/v1/workspaces/{wid}/jobs/{jid}", headers=other).status_code == 404
    assert (
        client.post(f"/api/v1/workspaces/{wid}/jobs/{jid}/cancel", headers=actor).json()["state"]
        == "cancelled"
    )


def test_verification_resend_workspace_list_and_session_revoke(auth_app):
    client, delivered, _ = auth_app
    email = f"resend-{uuid4().hex}@example.test"
    client.post(
        "/api/v1/auth/register", headers=ORIGIN, json={"email": email, "password": PASSWORD}
    )
    old = delivered[-1][2]
    assert (
        client.post(
            "/api/v1/auth/verification/request", headers=ORIGIN, json={"email": email}
        ).status_code
        == 202
    )
    new = delivered[-1][2]
    assert new != old
    assert (
        client.post("/api/v1/auth/verify-email", headers=ORIGIN, json={"token": old}).status_code
        == 400
    )
    assert (
        client.post("/api/v1/auth/verify-email", headers=ORIGIN, json={"token": new}).status_code
        == 200
    )
    response = client.post(
        "/api/v1/auth/login", headers=ORIGIN, json={"email": email, "password": PASSWORD}
    )
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie
    token = response.json()
    headers = {"authorization": "Bearer " + token["access_token"]}
    assert client.get("/api/v1/workspaces", headers=headers).json() == {"items": []}
    created = client.post("/api/v1/workspaces", headers=headers, json={"name": "My workspace"})
    assert (
        client.get("/api/v1/workspaces", headers=headers).json()["items"][0]["id"]
        == created.json()["id"]
    )
    assert client.get("/api/v1/workspaces?limit=101", headers=headers).status_code == 422
    assert (
        client.delete(
            "/api/v1/me/login-sessions/" + token["family_id"], headers=headers
        ).status_code
        == 204
    )
    assert client.get("/api/v1/me", headers=headers).status_code == 401
