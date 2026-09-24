"""Migration guards run against disposable transaction-local session copies."""

import runpy
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from test_diary_recovery_db import collected, diary, longitudinal  # noqa: F401

pytestmark = pytest.mark.db


@pytest.mark.parametrize(
    "case", ["active_diary", "regular", "submitted", "no_revision", "extra_change"]
)
def test_rotation_guard_and_lossless_downgrade(diary, db_engine, case):  # noqa: F811
    migration = runpy.run_path(
        str(Path(__file__).parents[1] / "migrations/versions/027_diary_recovery.py")
    )
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            schema = "diary_guard_" + uuid4().hex
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            connection.execute(text(f'SET LOCAL search_path TO "{schema}", public'))
            connection.execute(
                text(
                    "CREATE TABLE collection_sessions (LIKE public.collection_sessions INCLUDING ALL)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO collection_sessions SELECT * FROM public.collection_sessions WHERE id=:id"
                ),
                {"id": diary["sid"]},
            )
            if case == "regular":
                connection.execute(text("UPDATE collection_sessions SET diary_occurrence_id=NULL"))
            elif case == "submitted":
                connection.execute(text("UPDATE collection_sessions SET state='submitted'"))
            with Operations.context(MigrationContext.configure(connection)):
                migration["upgrade"]()
                connection.execute(
                    text(
                        "CREATE TRIGGER recovery_guard BEFORE UPDATE ON collection_sessions FOR EACH ROW EXECUTE FUNCTION collection_session_guard()"
                    )
                )
                before = connection.execute(
                    text("SELECT to_jsonb(s) FROM collection_sessions s")
                ).scalar_one()
                update = "UPDATE collection_sessions SET capability_hash=:hash"
                if case != "no_revision":
                    update += ", revision=revision+1"
                if case == "extra_change":
                    update += ", expires_at=expires_at+interval '1 second'"
                if case != "active_diary":
                    with pytest.raises(ProgrammingError, match="invalid diary capability rotation"):
                        with connection.begin_nested():
                            connection.execute(text(update), {"hash": "a" * 64})
                    assert (
                        connection.execute(
                            text("SELECT to_jsonb(s) FROM collection_sessions s")
                        ).scalar_one()
                        == before
                    )
                else:
                    connection.execute(text(update), {"hash": "a" * 64})
                    after = connection.execute(
                        text("SELECT to_jsonb(s) FROM collection_sessions s")
                    ).scalar_one()
                    assert after == before | {
                        "capability_hash": "a" * 64,
                        "revision": before["revision"] + 1,
                    }
                    migration["downgrade"]()
                    assert (
                        connection.execute(
                            text("SELECT to_jsonb(s) FROM collection_sessions s")
                        ).scalar_one()
                        == after
                    )
                    with pytest.raises(ProgrammingError, match="session identity is immutable"):
                        with connection.begin_nested():
                            connection.execute(text(update), {"hash": "b" * 64})
                    migration["upgrade"]()
                    connection.execute(text(update), {"hash": "b" * 64})
                    assert (
                        connection.execute(
                            text("SELECT revision FROM collection_sessions")
                        ).scalar_one()
                        == 2
                    )
        finally:
            transaction.rollback()
