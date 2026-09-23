"""Real PostgreSQL integration tests; the runner must supply a safe test DB."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import event, inspect, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError

from app.db import REVISION, Database
from app.main import create_app
from app.seed import seed_demo

pytestmark = pytest.mark.db


def test_foundation_revision_is_applied(db_engine, migrated_database):
    with db_engine.connect() as connection:
        revisions = (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        )
    assert revisions == [REVISION]


def test_metadata_schema(db_engine, migrated_database):
    inspector = inspect(db_engine)
    columns = {column["name"]: column for column in inspector.get_columns("app_metadata")}
    assert columns["key"]["type"].length == 64
    assert inspector.get_pk_constraint("app_metadata")["constrained_columns"] == ["key"]
    assert isinstance(columns["value"]["type"], JSONB)
    assert columns["value"]["nullable"] is False
    assert columns["is_synthetic"]["nullable"] is False
    assert columns["created_at"]["type"].timezone is True


def test_json_roundtrip_and_rollback(db_engine, migrated_database):
    key = f"test_{uuid4().hex}"
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                text(
                    "INSERT INTO app_metadata (key, value, is_synthetic) VALUES (:key, CAST(:value AS jsonb), true)"
                ),
                {"key": key, "value": '{"nested": {"items": [1, true, null]}, "label": "demo"}'},
            )
            row = connection.execute(
                text("SELECT value, created_at FROM app_metadata WHERE key = :key"), {"key": key}
            ).one()
            assert row.value == {"nested": {"items": [1, True, None]}, "label": "demo"}
            assert row.created_at.tzinfo is not None
        finally:
            transaction.rollback()
    with db_engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM app_metadata WHERE key = :key"), {"key": key}
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    "value, synthetic",
    [("{}", False), ("{}", None), (None, True)],
)
def test_metadata_rejects_invalid_rows(db_engine, migrated_database, value, synthetic):
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO app_metadata (key, value, is_synthetic) VALUES (:key, CAST(:value AS jsonb), :synthetic)"
                    ),
                    {"key": f"test_{uuid4().hex}", "value": value, "synthetic": synthetic},
                )
        finally:
            transaction.rollback()


def test_demo_seed_is_explicit_and_idempotent(db_engine, migrated_database):
    assert seed_demo(db_engine) is None
    with db_engine.connect() as connection:
        before = connection.execute(
            text(
                "SELECT key, value, is_synthetic, created_at FROM app_metadata WHERE key = 'p01_demo'"
            )
        ).one()
    assert before.is_synthetic is True
    assert seed_demo(db_engine) is None
    with db_engine.connect() as connection:
        after = connection.execute(
            text(
                "SELECT key, value, is_synthetic, created_at FROM app_metadata WHERE key = 'p01_demo'"
            )
        ).all()
    assert after == [before]


def test_boot_twice_does_not_create_tables_or_seed(
    settings, db_engine, migrated_database, monkeypatch
):
    # The safety-checked fixture, not the application DSN, selects the database.
    boot_settings = settings.model_copy(
        update={
            "database_url": SecretStr(db_engine.url.render_as_string(hide_password=False)),
        }
    )
    with db_engine.connect() as connection:
        before = connection.execute(
            text("SELECT key, value, is_synthetic, created_at FROM app_metadata ORDER BY key")
        ).all()
    statements = []

    def record_sql(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    for _ in range(2):
        app = create_app(boot_settings)
        event.listen(app.state.database.engine, "before_cursor_execute", record_sql)
        monkeypatch.setattr(app.state.database, "check_ready", lambda: True)
        with TestClient(app) as client:
            assert client.get("/api/v1/health/live").status_code == 200
    # P01 startup is lazy: even SELECTs are unnecessary until readiness is asked.
    assert statements == []
    with db_engine.connect() as connection:
        after = connection.execute(
            text("SELECT key, value, is_synthetic, created_at FROM app_metadata ORDER BY key")
        ).all()
    assert after == before


def test_real_readiness_checks_schema(settings, db_engine, monkeypatch):
    database = Database(settings)
    database.engine.dispose()
    database.engine = db_engine
    assert database.check_ready() is True
    with db_engine.begin() as conn:
        conn.execute(text("UPDATE alembic_version SET version_num = 'wrong_revision'"))
    try:
        assert database.check_ready() is False
    finally:
        with db_engine.begin() as conn:
            conn.execute(
                text("UPDATE alembic_version SET version_num = :revision"), {"revision": REVISION}
            )


def test_migration_down_up_and_repeat(db_engine):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.downgrade(config, "base")
    assert "app_metadata" not in inspect(db_engine).get_table_names()
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    seed_demo(db_engine)
    seed_demo(db_engine)
    with db_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM app_metadata")).scalar_one() == 1
