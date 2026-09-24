"""Offline DDL checks and guarded PostgreSQL tests in transaction-local schemas."""

import importlib.util
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def migration():
    path = Path(__file__).parents[1] / "migrations/versions/024_exposure_preparation.py"
    spec = importlib.util.spec_from_file_location("exposure_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_downgrade_guards_before_removing_protocol_and_restores_legacy_default(migration):
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        migration.downgrade()
    sql = output.getvalue()
    assert "CHECK (protocol_version = 1)" in sql
    assert sql.index("ADD CONSTRAINT ck_attempt_rollback_requires_legacy") < sql.index("DROP")
    assert "ALTER COLUMN started_at SET NOT NULL" in sql
    assert "ALTER COLUMN started_at SET DEFAULT now()" in sql
    assert "DROP TABLE" not in sql and "DELETE" not in sql and "UPDATE" not in sql


@pytest.mark.db
@pytest.mark.parametrize(
    "state", [None, "legacy", "preparing", "started", "completed", "interrupted"]
)
def test_downgrade_roundtrip_or_preserves_v2_facts(db_engine, migration, state):
    # Never alter application tables: DDL and synthetic rows roll back together.
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            schema = "exposure_migration_" + uuid4().hex
            connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(sa.text(f'SET LOCAL search_path TO "{schema}"'))
            connection.execute(
                sa.text("""
                CREATE TABLE interaction_attempts (
                    id uuid PRIMARY KEY, session_id uuid NOT NULL, block_key varchar(64) NOT NULL,
                    state varchar(24) NOT NULL, started_at timestamptz NOT NULL DEFAULT now(),
                    ended_at timestamptz, visible_ms integer,
                    CONSTRAINT uq_interaction_attempt UNIQUE (session_id, block_key)
                )
            """)
            )
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
                if state:
                    connection.execute(
                        sa.text("""
                            INSERT INTO interaction_attempts
                                (id, session_id, block_key, state, protocol_version, started_at,
                                 prepared_at, preparation_expires_at, preparation_hash)
                            VALUES (:id, :session_id, 'exposure', :state, :protocol,
                                CASE WHEN :has_start THEN now() ELSE NULL END,
                                now(), now() + interval '30 seconds', :hash)
                        """),
                        {
                            "id": uuid4(),
                            "session_id": uuid4(),
                            "state": "started" if state == "legacy" else state,
                            "protocol": 1 if state == "legacy" else 2,
                            "has_start": state in {"legacy", "started", "completed"},
                            "hash": "a" * 64,
                        },
                    )
                before = (
                    connection.execute(sa.text("SELECT * FROM interaction_attempts"))
                    .mappings()
                    .all()
                )
                if state not in {None, "legacy"}:
                    with pytest.raises(IntegrityError, match="ck_attempt_rollback_requires_legacy"):
                        with connection.begin_nested():
                            migration.downgrade()
                    after = (
                        connection.execute(sa.text("SELECT * FROM interaction_attempts"))
                        .mappings()
                        .all()
                    )
                    assert after == before
                else:
                    migration.downgrade()
                    columns = {
                        c["name"]: c
                        for c in sa.inspect(connection).get_columns("interaction_attempts")
                    }
                    assert "protocol_version" not in columns
                    assert not columns["started_at"]["nullable"]
                    assert columns["started_at"]["default"] == "now()"
                    migration.upgrade()
                    if state:
                        after = (
                            connection.execute(sa.text("SELECT * FROM interaction_attempts"))
                            .mappings()
                            .one()
                        )
                        for field in (
                            "id",
                            "session_id",
                            "block_key",
                            "state",
                            "started_at",
                            "protocol_version",
                        ):
                            assert after[field] == before[0][field]
                    constraints = sa.inspect(connection).get_unique_constraints(
                        "interaction_attempts"
                    )
                    assert any(c["name"] == "uq_interaction_attempt" for c in constraints)
        finally:
            transaction.rollback()
