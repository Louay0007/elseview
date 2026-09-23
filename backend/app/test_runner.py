"""Explicit guarded entry point for destructive tests on the dedicated test database."""

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


def main():
    import pytest

    test_url = validate_test_database(
        os.environ.get("DATABASE_URL", ""),
        os.environ.get("TEST_DATABASE_URL", ""),
        os.environ.get("TEST_ALLOW_RESET", ""),
    )
    os.environ["TEST_ALLOW_DB"] = "1"
    os.environ["MIGRATION_DATABASE_URL"] = test_url
    os.environ["AI_MODE"] = "mock"
    os.environ["APP_ENV"] = "test"
    os.environ["JOB_RUNNER_ENABLED"] = "false"
    os.chdir(Path(__file__).resolve().parents[1])
    return pytest.main(["-m", "not live_llm and not load", *sys.argv[1:]])


if __name__ == "__main__":
    sys.exit(main())
