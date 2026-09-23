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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.delivery import deliver_local
from app.auth.models import Membership, RefreshToken, User, WorkspaceInvite
from app.auth.schemas import RegisterBody, WorkspaceBody
from app.auth.security import decode_access, token_hash, utcnow
from app.auth.service import AuthService, accept_invite, create_workspace, invite_member
from app.common.errors import DomainError
from app.db import Database
from app.main import create_app


def test_private_spool(settings):
    deliver_local(settings, "synthetic@example.test", "verify", "fake-token-not-secret")
    root = settings.private_root / "dev-mail"
    files = list(root.glob("*.json"))
    assert root.stat().st_mode & 0o777 == 0o700
    assert files[0].stat().st_mode & 0o777 == 0o600
    assert json.loads(files[0].read_text())["purpose"] == "verify"
    settings.app_env = "production"
    with pytest.raises(DomainError) as exc:
        deliver_local(settings, "synthetic@example.test", "reset", "fake")
    assert exc.value.status == 503


@pytest.mark.parametrize(
    "body",
    [
        {"email": "invalid", "password": "a-long-passphrase"},
        {"email": "x@example.test", "password": "short"},
        {"email": "x@example.test", "password": "a-long-passphrase", "role": "owner"},
    ],
)
def test_auth_schema_strict(body):
    with pytest.raises(ValueError):
        RegisterBody(**body)


def test_empty_workspace_name():
    with pytest.raises(ValueError):
        WorkspaceBody(name="   ")


@pytest.mark.parametrize(
    "claims,algorithm", [({}, "HS256"), ({"sub": "x"}, "HS256"), ({"exp": 9999999999}, "HS384")]
)
def test_missing_claims_and_wrong_algorithm(settings, claims, algorithm):
    raw = jwt.encode(claims, settings.secret_key.get_secret_value(), algorithm=algorithm)
    with pytest.raises(DomainError):
        decode_access(raw, settings)


@pytest.fixture
def identity_service(settings, db_engine):
    database = Database(settings)
    database.engine.dispose()
    from sqlalchemy.orm import sessionmaker

    database.sessions = sessionmaker(db_engine, expire_on_commit=False)
    deliveries = []
    service = AuthService(database, settings, lambda *args: deliveries.append(args))
    email = f"hardening-{uuid4().hex}@example.test"
    service.register(email, "Synthetic-password-long", "Test")
    service.consume_token(deliveries[-1][2], "verify")
    return service, deliveries, email


@pytest.mark.db
def test_refresh_race_revokes_whole_family(identity_service, db_engine):
    service, _, email = identity_service
    login = service.login(email, "Synthetic-password-long")
    barrier = Barrier(2)

    def refresh():
        barrier.wait()
        try:
            return service.refresh(login["refresh_token"], login["csrf_token"])
        except DomainError:
            return None

    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(lambda _: refresh(), range(2)))
    assert sum(r is not None for r in results) == 1
    with Session(db_engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(RefreshToken)
                .where(
                    RefreshToken.family_id == login["family_id"], RefreshToken.revoked_at.is_(None)
                )
            )
            == 0
        )


@pytest.mark.db
def test_expired_refresh_and_wrong_purpose(identity_service, db_engine):
    service, deliveries, email = identity_service
    login = service.login(email, "Synthetic-password-long")
    with Session(db_engine) as session, session.begin():
        session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash(login["refresh_token"])
            )
        ).expires_at = utcnow() - timedelta(seconds=1)
    with pytest.raises(DomainError):
        service.refresh(login["refresh_token"], login["csrf_token"])
    service.request_token(email, "reset")
    with pytest.raises(DomainError):
        service.consume_token(deliveries[-1][2], "verify")


@pytest.mark.db
def test_reset_token_consumed_once_concurrently(identity_service):
    service, deliveries, email = identity_service
    service.request_token(email, "reset")
    raw = deliveries[-1][2]
    barrier = Barrier(2)

    def consume():
        barrier.wait()
        try:
            service.consume_token(raw, "reset", "New-synthetic-password")
            return True
        except DomainError:
            return False

    with ThreadPoolExecutor(2) as executor:
        assert sum(executor.map(lambda _: consume(), range(2))) == 1


@pytest.mark.db
def test_invitation_subject_expiry_and_revoked_inviter(db_engine):
    with Session(db_engine) as session, session.begin():
        users = [
            User(
                email=f"invite-{uuid4().hex}@example.test",
                password_hash="unused",
                verified_at=utcnow(),
            )
            for _ in range(3)
        ]
        session.add_all(users)
        session.flush()
        ws = create_workspace(session, users[0].id, "Invite limits")
        invite, raw = invite_member(session, users[0].id, ws.id, users[1].email, "viewer")
        uid, other_id, wid, invite_id = users[1].id, users[2].id, ws.id, invite.id
    with Session(db_engine) as session, session.begin():
        with pytest.raises(DomainError):
            accept_invite(session, session.get(User, other_id), raw)
    with Session(db_engine) as session, session.begin():
        session.get(WorkspaceInvite, invite_id).expires_at = utcnow() - timedelta(seconds=1)
    with Session(db_engine) as session, session.begin():
        with pytest.raises(DomainError):
            accept_invite(session, session.get(User, uid), raw)
    with Session(db_engine) as session, session.begin():
        invite = session.get(WorkspaceInvite, invite_id)
        invite.expires_at = utcnow() + timedelta(days=1)
        session.scalar(
            select(Membership).where(Membership.workspace_id == wid, Membership.role == "owner")
        ).status = "revoked"
    with Session(db_engine) as session, session.begin():
        with pytest.raises(DomainError):
            accept_invite(session, session.get(User, uid), raw)


@pytest.mark.db
def test_identity_model_constraints(db_engine):
    with Session(db_engine) as session, session.begin():
        user = User(
            email=f"constraint-{uuid4().hex}@example.test",
            password_hash="unused",
            verified_at=utcnow(),
        )
        session.add(user)
        session.flush()
        ws = create_workspace(session, user.id, "constraints")
        uid, wid = user.id, ws.id
    for role, workspace in [("invalid-role", wid), ("viewer", uuid4()), ("owner", wid)]:
        with pytest.raises(IntegrityError), Session(db_engine) as session, session.begin():
            session.add(Membership(user_id=uid, workspace_id=workspace, role=role))


@pytest.mark.db
def test_app_runner_lifespan_enabled(settings, db_engine):
    config = settings.model_copy(
        update={
            "database_url": SecretStr(db_engine.url.render_as_string(hide_password=False)),
            "job_runner_enabled": True,
            "job_poll_seconds": 0.1,
        }
    )
    app = create_app(config)
    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        assert app.state.job_runner._task is not None
    assert app.state.job_runner._task.done()
    assert app.state.started is False
