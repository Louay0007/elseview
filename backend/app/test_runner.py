"""Guarded dedicated-database tests; --fresh migrates an empty database without resetting it."""

import os
import sys
from pathlib import Path

from sqlalchemy.engine import make_url


def validate_test_database(app_url: str, test_url: str, guard: str) -> str:
    try:
        app, test = make_url(app_url), make_url(test_url)
        valid = (
            test.drivername == "postgresql+psycopg"
            and test.database
            and test.database.endswith("_test")
            and test.database != app.database
            and guard == test.database
            and test.username
            and test.password
            and test.host
        )
    except Exception:
        valid = False
    if not valid:
        raise RuntimeError(
            "Refusing database tests: dedicated _test database and exact reset guard required"
        )
    return test_url


def prepare_database(config, url: str, mode: str = "reset"):
    from alembic import command
    from sqlalchemy import create_engine, inspect

    if mode not in {"reset", "fresh"}:
        raise RuntimeError("Unknown test database mode")
    if mode == "fresh":
        engine = create_engine(url, hide_parameters=True)
        try:
            with engine.connect() as connection:
                inspector = inspect(connection)
                if (
                    inspector.get_table_names()
                    or inspector.get_view_names()
                    or inspector.get_materialized_view_names()
                    or inspector.get_enums()
                    or inspector.get_sequence_names()
                    or set(inspector.get_schema_names())
                    - {"public", "pg_catalog", "information_schema"}
                ):
                    raise RuntimeError(
                        "Fresh test mode requires an empty database; no reset performed"
                    )
        finally:
            engine.dispose()
    else:
        command.downgrade(config, "base")
    command.upgrade(config, "head")


def main():
    import pytest

    test_url = validate_test_database(
        os.environ.get("DATABASE_URL", ""),
        os.environ.get("TEST_DATABASE_URL", ""),
        os.environ.get("TEST_ALLOW_RESET", ""),
    )
    arguments = sys.argv[1:]
    if "--fresh" in arguments:
        arguments.remove("--fresh")
        os.environ["TEST_DATABASE_MODE"] = "fresh"
    os.environ["TEST_ALLOW_DB"] = "1"
    os.environ["MIGRATION_DATABASE_URL"] = test_url
    os.environ["AI_MODE"] = "mock"
    os.environ["APP_ENV"] = "test"
    os.environ["JOB_RUNNER_ENABLED"] = "false"
    os.chdir(Path(__file__).resolve().parents[1])
    return pytest.main(["-m", "not live_llm and not load and not browser", *arguments])


if __name__ == "__main__":
    sys.exit(main())
