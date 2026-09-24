"""Additive migration checks against a fresh disposable PostgreSQL only."""

import importlib.util
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from test_language_assessments_db import assessment as assessment
from test_language_assessments_db import begin, ok, publish

pytestmark = pytest.mark.db


def migration():
    path = Path(__file__).resolve().parents[1] / "migrations/versions/026_language_assessments.py"
    spec = importlib.util.spec_from_file_location("assessment_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_chain_and_additive_tables(db_engine):
    assert migration().down_revision == "025_auth_delivery"
    names = set(inspect(db_engine).get_table_names())
    assert {
        "qualifications",
        "language_assessment_versions",
        "language_assessment_keys",
        "language_assessment_consents",
        "language_assessment_attempts",
        "language_assessment_decisions",
    } <= names


def test_scope_constraint_and_populated_downgrade_refusal(assessment):
    x = assessment
    attempt = ok(begin(x, publish(x)), 201)
    with x["app"].state.database.sessions.begin() as session:
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text(
                    "UPDATE language_assessment_attempts SET consent_grant_id=:id WHERE id=:attempt"
                ),
                {"id": uuid4(), "attempt": UUID(attempt["id"])},
            )
        with pytest.raises(DBAPIError), session.begin_nested():
            session.execute(
                text(
                    "UPDATE language_assessment_attempts SET language='arabizi' WHERE id=:attempt"
                ),
                {"attempt": UUID(attempt["id"])},
            )
        module = migration()
        with pytest.raises(DBAPIError, match="downgrade refused"), session.begin_nested():
            module.op = Operations(MigrationContext.configure(session.connection()))
            module.downgrade()
        assert (
            session.scalar(
                text("SELECT count(*) FROM language_assessment_attempts WHERE id=:id"),
                {"id": UUID(attempt["id"])},
            )
            == 1
        )
