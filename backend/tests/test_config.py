"""Configuration boundaries for the P01 local-only foundation."""

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings


def configured(settings, **changes):
    values = settings.model_dump()
    values.update(changes)
    return Settings(**values)


@pytest.mark.parametrize(
    "name",
    ["database_url", "migration_database_url", "test_database_url", "cache_url", "secret_key"],
)
def test_credentials_are_required_and_secret(settings, monkeypatch, name):
    assert isinstance(getattr(settings, name), SecretStr)
    monkeypatch.delenv(name.upper(), raising=False)
    monkeypatch.delenv(name, raising=False)
    values = settings.model_dump()
    values.pop(name)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_local_defaults(settings):
    assert settings.app_env == "development"
    assert settings.ai_mode == "mock"
    assert settings.public_origin == "http://localhost:8080"
    assert settings.allowed_origins == ["http://localhost:8080"]
    assert isinstance(settings.private_root, Path)
    assert settings.job_runner_enabled is False
    assert settings.db_pool_size == 5
    assert settings.db_max_overflow == 0
    assert settings.db_connect_timeout == 2


def test_secrets_do_not_appear_in_representation(settings):
    for name in (
        "database_url",
        "migration_database_url",
        "test_database_url",
        "cache_url",
        "secret_key",
    ):
        assert getattr(settings, name).get_secret_value() not in repr(settings)


def test_constructor_rejects_unknown_options(settings):
    with pytest.raises(ValidationError):
        configured(settings, databse_url="postgresql+psycopg://localhost/typo")


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_supported_local_environments(settings, app_env):
    assert configured(settings, app_env=app_env).app_env == app_env


@pytest.mark.parametrize("ai_mode", ["disabled", "mock"])
def test_supported_ai_modes(settings, ai_mode):
    assert configured(settings, ai_mode=ai_mode).ai_mode == ai_mode


@pytest.mark.parametrize(
    "changes",
    [
        {"app_env": "staging"},
        {"ai_mode": "unknown"},
        {"ai_mode": "live"},
        {"secret_key": "too-short"},
        {"secret_key": "x" * 64},
        {"public_origin": "*"},
        {"public_origin": "http://localhost:8080/some/path"},
        {"public_origin": "http://user:password@localhost:8080"},
        {"allowed_origins": ["*"]},
        {"allowed_origins": ["http://localhost:8080/some/path"]},
        {"allowed_origins": ["http://user:password@localhost:8080"]},
        {"max_request_bytes": 0},
        {"max_request_bytes": -1},
        {"log_level": "VERBOSE_BUT_INVALID"},
        {"db_pool_size": 21},
    ],
)
def test_unsafe_or_unimplemented_configuration_is_rejected(settings, changes):
    with pytest.raises(ValueError):
        configured(settings, **changes)


@pytest.mark.parametrize("name", ["database_url", "migration_database_url", "test_database_url"])
@pytest.mark.parametrize(
    "url",
    ["sqlite:///unsafe.db", "postgresql://user:password@localhost/db", "mysql://localhost/db"],
)
def test_database_urls_require_postgresql_psycopg(settings, name, url):
    with pytest.raises(ValueError):
        configured(settings, **{name: url})


def test_app_and_test_database_names_must_differ_even_on_different_hosts(settings):
    with pytest.raises(ValueError):
        configured(
            settings,
            database_url="postgresql+psycopg://app:password@host-a/shared_database_test",
            migration_database_url="postgresql+psycopg://owner:password@host-a/shared_database_test",
            test_database_url="postgresql+psycopg://test:password@host-b/shared_database_test",
        )


@pytest.mark.parametrize(
    "origin", ["http://example.com", "https://localhost:8080", "http://localhost:8080"]
)
def test_production_rejects_insecure_or_local_origins(settings, origin):
    with pytest.raises(ValueError):
        configured(settings, app_env="production", public_origin=origin, allowed_origins=[origin])


def test_job_runner_can_be_enabled(settings):
    assert configured(settings, job_runner_enabled=True).job_runner_enabled is True
