import os
import socket
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.config import Settings
from app.main import create_app
from app.test_runner import prepare_database, validate_test_database


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        app_env="development",
        ai_mode="mock",
        database_url="postgresql+psycopg://app:unit-secret@localhost:5432/elseview_app",
        migration_database_url="postgresql+psycopg://owner:unit-secret@localhost:5432/elseview_app",
        test_database_url="postgresql+psycopg://tester:unit-secret@localhost:5432/elseview_test",
        cache_url="redis://:unit-secret@localhost:6379/0",
        secret_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        private_root=tmp_path,
    )


@pytest.fixture
def client(settings, monkeypatch):
    app = create_app(settings)
    monkeypatch.setattr(app.state.database, "check_ready", lambda: True)
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def block_network(monkeypatch, request):
    """Tests may connect only to the configured PostgreSQL server in explicitly enabled DB tests."""
    allowed = set()
    if request.node.get_closest_marker("db") and os.environ.get("TEST_ALLOW_DB") == "1":
        from sqlalchemy.engine import make_url

        url = make_url(os.environ["TEST_DATABASE_URL"])
        allowed = {
            (item[4][0], url.port or 5432)
            for item in socket.getaddrinfo(url.host, url.port or 5432, type=socket.SOCK_STREAM)
        }
    original = socket.socket.connect
    if request.node.get_closest_marker("cache") and os.environ.get("TEST_ALLOW_DB") == "1":
        from urllib.parse import urlsplit

        cache = urlsplit(os.environ["CACHE_URL"])
        allowed.update(
            (item[4][0], cache.port or 6379)
            for item in socket.getaddrinfo(
                cache.hostname, cache.port or 6379, type=socket.SOCK_STREAM
            )
        )
    original_ex = socket.socket.connect_ex

    def check(sock, address, method):
        if sock.family == socket.AF_UNIX:
            return method(sock, address)
        if isinstance(address, tuple) and (address[0], address[1]) in allowed:
            return method(sock, address)
        raise AssertionError("External network is prohibited in tests")

    monkeypatch.setattr(socket.socket, "connect", lambda sock, addr: check(sock, addr, original))
    monkeypatch.setattr(
        socket.socket, "connect_ex", lambda sock, addr: check(sock, addr, original_ex)
    )


@pytest.fixture(scope="session")
def migrated_database():
    if os.environ.get("TEST_ALLOW_DB") != "1":
        pytest.skip("Use python -m app.test_runner with explicit dedicated test-database guard")
    url = validate_test_database(
        os.environ["DATABASE_URL"],
        os.environ["TEST_DATABASE_URL"],
        os.environ.get("TEST_ALLOW_RESET", ""),
    )
    previous = os.environ.get("MIGRATION_DATABASE_URL")
    os.environ["MIGRATION_DATABASE_URL"] = url
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    prepare_database(config, url, os.environ.get("TEST_DATABASE_MODE", "reset"))
    yield url
    if previous is None:
        os.environ.pop("MIGRATION_DATABASE_URL", None)
    else:
        os.environ["MIGRATION_DATABASE_URL"] = previous


@pytest.fixture
def db_engine(migrated_database):
    engine = create_engine(migrated_database, hide_parameters=True)
    yield engine
    engine.dispose()


@pytest.fixture
def migration_engine(migrated_database, monkeypatch):
    """Round-trip migrations only in a new empty database, never accumulated test data."""
    from uuid import uuid4

    from sqlalchemy.engine import make_url
    from sqlalchemy.pool import NullPool

    name = "migration_" + uuid4().hex + "_test"
    url = make_url(migrated_database)
    admin = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        hide_parameters=True,
    )
    engine = None
    created = False
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{name}" TEMPLATE template0')
        created = True
        isolated_url = url.set(database=name).render_as_string(hide_password=False)
        monkeypatch.setenv("MIGRATION_DATABASE_URL", isolated_url)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        prepare_database(config, isolated_url, "fresh")
        engine = create_engine(isolated_url, poolclass=NullPool, hide_parameters=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        try:
            if created:
                with admin.connect() as connection:
                    connection.exec_driver_sql(f'DROP DATABASE "{name}"')
        finally:
            admin.dispose()


@pytest.fixture
def fixed_clock():
    from datetime import UTC, datetime

    return lambda: datetime(2026, 9, 23, 12, 0, tzinfo=UTC)


@pytest.fixture
def fixed_random():
    import random

    return random.Random(42)


@pytest.fixture
def research_app(settings, db_engine):
    from uuid import uuid4

    from pydantic import SecretStr
    from sqlalchemy.orm import Session

    from app.auth.models import Membership, User
    from app.auth.security import utcnow
    from app.auth.service import create_workspace

    config = settings.model_copy(
        update={"database_url": SecretStr(db_engine.url.render_as_string(hide_password=False))}
    )
    app = create_app(config)

    class LocalLimiter:
        def check(self, *args, **kwargs):
            pass

        def close(self):
            pass

    app.state.rate_limiter.close()
    app.state.rate_limiter = LocalLimiter()

    def actor(workspace_id=None, role="owner"):
        with Session(db_engine) as session, session.begin():
            user = User(
                email=f"research-{uuid4().hex}@example.test",
                password_hash="unused-synthetic",
                verified_at=utcnow(),
            )
            session.add(user)
            session.flush()
            if workspace_id is None:
                workspace_id = create_workspace(session, user.id, "Synthetic research").id
            else:
                session.add(Membership(workspace_id=workspace_id, user_id=user.id, role=role))
            credentials = app.state.auth._new_login(session, user)
            return {"authorization": "Bearer " + credentials["access_token"]}, user.id, workspace_id

    with TestClient(app) as client:
        yield client, app, actor


@pytest.fixture
def mock_provider():
    import httpx

    return httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []}))
