import logging
from pathlib import Path

import pytest
import yaml

from app.config import load_settings
from app.main import SafeFormatter, create_app
from app.test_runner import validate_test_database

ROOT = Path(__file__).resolve().parents[2]


def test_unknown_owned_environment_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENVIROMENT", "secret-value-must-not-appear")
    with pytest.raises(ValueError, match="Unknown application") as exc:
        load_settings()
    assert "secret-value" not in str(exc.value)


def test_configuration_failure_is_sanitized(monkeypatch):
    monkeypatch.setenv("APP_ENV", "secret-value-must-not-appear")
    with pytest.raises(RuntimeError) as exc:
        create_app()
    assert "secret-value" not in str(exc.value)


def test_formatter_discards_arbitrary_message_and_exception():
    record = logging.LogRecord("elseview", logging.ERROR, "x", 1, "secret-token", (), None)
    record.exc_text = "password=private"
    assert "secret-token" not in SafeFormatter().format(record)
    assert "private" not in SafeFormatter().format(record)


@pytest.mark.parametrize(
    "app,test,guard",
    [
        ("postgresql+psycopg://u:p@h/app", "postgresql+psycopg://u:p@h/app", "app"),
        ("postgresql+psycopg://u:p@h/app", "postgresql+psycopg://u:p@h/elseview_test", ""),
        ("postgresql+psycopg://u:p@h/app", "sqlite:///elseview_test", "elseview_test"),
        ("postgresql+psycopg://u:p@h/app", "postgresql+psycopg://u:p@h/research", "research"),
    ],
)
def test_destructive_test_guard(app, test, guard):
    with pytest.raises(RuntimeError):
        validate_test_database(app, test, guard)


def test_destructive_test_guard_accepts_explicit_test_database():
    url = "postgresql+psycopg://u:p@database:5432/elseview_test"
    assert (
        validate_test_database("postgresql+psycopg://u:p@database:5432/app", url, "elseview_test")
        == url
    )


def test_external_egress_blocked():
    import socket

    with socket.socket() as sock, pytest.raises(AssertionError, match="network"):
        sock.connect(("203.0.113.10", 443))


def test_mock_provider_never_needs_network(mock_provider):
    import httpx

    with httpx.Client(transport=mock_provider) as client:
        assert client.post("https://provider.invalid/v1/chat/completions").json() == {"choices": []}


def test_compose_has_four_services_and_loopback_only():
    base = yaml.safe_load((ROOT / "compose.yaml").read_text())
    assert base["name"] == "elseview"
    assert base["volumes"]["postgres_data"]["name"] == "elseview_postgres_data"
    assert base["volumes"]["private_data"]["name"] == "elseview_private_data"
    dev = yaml.safe_load((ROOT / "compose.dev.yaml").read_text())
    assert set(base["services"]) == {"frontend", "backend", "database", "cache"}
    assert set(dev["services"]) <= set(base["services"])
    for name, service in base["services"].items():
        if name != "frontend":
            assert not service.get("ports")
        else:
            assert all(str(port).startswith("127.0.0.1:") for port in service["ports"])
    assert base["services"]["backend"]["user"] == "10001:10001"
    assert base["services"]["backend"]["environment"]["AI_MODE"] == "mock"
    assert "--reload" not in base["services"]["backend"]["command"]
    assert "--reload" in dev["services"]["backend"]["command"]


def test_container_images_pinned():
    import re

    base = yaml.safe_load((ROOT / "compose.yaml").read_text())
    for name in ("database", "cache"):
        assert re.search(r"@sha256:[0-9a-f]{64}$", base["services"][name]["image"])
    for filename in ("backend/Dockerfile", "frontend/Dockerfile"):
        for image in re.findall(r"^FROM (\S+)", (ROOT / filename).read_text(), re.M):
            assert image in {"development"} or re.search(r"@sha256:[0-9a-f]{64}$", image)


def test_clock_and_random_fixtures(fixed_clock, fixed_random):
    assert fixed_clock().isoformat() == "2026-09-23T12:00:00+00:00"
    assert fixed_random.random() == pytest.approx(0.6394267984578837)


def test_unrelated_os_environment_is_ignored(settings, monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("EDITOR", "arbitrary unrelated value")
    values = settings.model_dump()
    assert Settings(**values).ai_mode == "mock"


def test_secret_setup_never_overwrites(tmp_path):
    import importlib.util

    script = ROOT / "scripts/setup_dev.py"
    spec = importlib.util.spec_from_file_location("setup_dev_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    module.__file__ = str(scripts_dir / "setup_dev.py")
    assert module.main() == 0
    env = tmp_path / ".env"
    before = env.read_bytes()
    assert env.stat().st_mode & 0o777 == 0o600
    assert module.main() == 1
    assert env.read_bytes() == before


@pytest.mark.parametrize(
    "change",
    [
        {"cache_url": "redis://localhost:6379/0"},
        {"database_url": "bad://"},
        {"private_root": "relative"},
        {"allowed_origins": []},
        {"public_origin": "http://localhost:8080", "allowed_origins": ["http://127.0.0.1:8080"]},
        {"public_origin": "http://localhost:wrong", "allowed_origins": ["http://localhost:wrong"]},
        {"migration_database_url": "postgresql+psycopg://u:p@localhost:5432/other"},
        {
            "app_env": "production",
            "public_origin": "http://example.com",
            "allowed_origins": ["http://example.com"],
        },
    ],
)
def test_more_invalid_config(settings, change):
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(**(settings.model_dump() | change))


def test_readiness_handles_connection_failure(settings, monkeypatch):
    from app.db import Database

    db = Database(settings)

    def fail():
        raise RuntimeError("secret-database-password")

    monkeypatch.setattr(db.engine, "connect", fail)
    assert db.check_ready() is False
    db.close()
