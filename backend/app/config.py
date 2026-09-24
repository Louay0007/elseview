"""Fail-closed configuration. Environment values must never appear in error logs."""

import ipaddress
import os
from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="forbid", case_sensitive=False, hide_input_in_errors=True
    )

    app_env: Literal["development", "test", "production"] = "development"
    ai_mode: Literal["disabled", "mock", "live"] = "mock"
    collaboration_integration_mode: Literal["disabled", "mock", "live"] = "disabled"
    collaboration_webhook_destinations: list[str] = []
    collaboration_webhook_secret: SecretStr = SecretStr("")
    collaboration_webhook_timeout_seconds: float = Field(default=3, gt=0, le=30)
    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "mock-v1"
    llm_approved_hosts: list[str] = []
    llm_profile_approved: bool = False
    llm_privacy_approved: bool = False
    llm_privacy_record: str = ""
    llm_config_revision: str = "1"
    llm_model_revision: str = "unspecified"
    llm_timeout_seconds: float = Field(default=5, gt=0, le=120)
    llm_max_output_tokens: int = Field(default=1500, ge=64, le=8000)
    llm_context_limit: int = Field(default=16000, ge=2048, le=200000)
    llm_concurrency: Literal[1] = 1
    llm_max_attempts: Literal[1] = 1
    llm_output_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    llm_supports_json_schema: bool = False
    llm_supports_json_object: bool = False
    llm_input_price_per_million: Decimal = Field(default=Decimal("0"), ge=0)
    llm_output_price_per_million: Decimal = Field(default=Decimal("0"), ge=0)
    llm_other_charge_reserve: Decimal = Field(default=Decimal("0"), ge=0)
    llm_study_budget: Decimal = Field(default=Decimal("1"), gt=0)
    llm_workspace_daily_budget: Decimal = Field(default=Decimal("5"), gt=0)
    llm_currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    llm_budget_timezone: Literal["UTC"] = "UTC"
    database_url: SecretStr
    migration_database_url: SecretStr
    test_database_url: SecretStr
    cache_url: SecretStr
    secret_key: SecretStr
    public_origin: str = "http://localhost:8080"
    allowed_origins: list[str] = ["http://localhost:8080"]
    private_root: Path = Path("/app/private")
    job_runner_enabled: bool = False
    private_workspace_bytes: int = Field(default=268435456, ge=16777216, le=10737418240)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    max_request_bytes: int = Field(default=1_048_576, ge=1, le=10_485_760)
    db_pool_size: int = Field(default=5, ge=1, le=20)
    db_max_overflow: int = Field(default=0, ge=0, le=5)
    db_connect_timeout: int = Field(default=2, ge=1, le=10)
    auth_issuer: str = "elseview"
    auth_audience: str = "elseview-api"
    auth_access_seconds: int = Field(default=900, ge=60, le=3600)
    auth_refresh_days: int = Field(default=30, ge=1, le=90)
    auth_verify_seconds: int = Field(default=1800, ge=60, le=86400)
    job_poll_seconds: float = Field(default=2.0, ge=0.1, le=60)
    job_lease_seconds: int = Field(default=30, ge=5, le=3600)
    job_timeout_seconds: float = Field(default=10, ge=0.1, le=300)
    job_shutdown_seconds: float = Field(default=3, ge=0.1, le=30)

    @field_validator("secret_key")
    @classmethod
    def strong_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) < 32 or len(set(raw)) < 12:
            raise ValueError("SECRET_KEY must be a generated high-entropy secret")
        return value

    @field_validator("database_url", "migration_database_url", "test_database_url")
    @classmethod
    def postgres_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and all(
                (url.username, url.password, url.host, url.database)
            )
        except Exception:
            valid = False
        if not valid:
            raise ValueError("A complete postgresql+psycopg URL is required")
        return value

    @field_validator("cache_url")
    @classmethod
    def cache_address(cls, value: SecretStr) -> SecretStr:
        try:
            url = urlsplit(value.get_secret_value())
            valid = url.scheme in {"redis", "rediss"} and url.hostname and url.password
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("An authenticated Redis-protocol cache URL is required")
        return value

    @field_validator("private_root")
    @classmethod
    def absolute_storage(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("PRIVATE_ROOT must be absolute")
        return value

    @model_validator(mode="after")
    def policy(self) -> "Settings":
        if self.collaboration_integration_mode != "disabled" and (
            not self.collaboration_webhook_destinations
            or len(self.collaboration_webhook_secret.get_secret_value()) < 32
            or self.collaboration_webhook_timeout_seconds >= self.job_timeout_seconds
        ):
            raise ValueError(
                "Enabled webhooks require approved destinations, a strong secret and bounded timeout"
            )
        if self.ai_mode == "live":
            url = urlsplit(self.llm_base_url)
            try:
                unsafe_host = not ipaddress.ip_address(url.hostname or "").is_global
            except ValueError:
                unsafe_host = (
                    not url.hostname
                    or "." not in url.hostname
                    or url.hostname.endswith((".internal", ".local", ".localhost"))
                )
            if not (
                self.llm_profile_approved
                and self.llm_privacy_approved
                and self.llm_privacy_record.strip()
                and self.llm_api_key.get_secret_value()
                and self.llm_model.strip()
                and self.llm_model != "mock-v1"
                and url.scheme == "https"
                and url.hostname in self.llm_approved_hosts
                and not unsafe_host
                and url.hostname not in {"localhost", "127.0.0.1", "::1"}
                and not url.username
                and not url.password
                and not url.query
                and not url.fragment
                and url.port in {None, 443}
                and self.llm_timeout_seconds < self.job_timeout_seconds
                and self.llm_input_price_per_million > 0
                and self.llm_output_price_per_million > 0
            ):
                raise ValueError(
                    "Live AI requires an approved HTTPS capability/privacy profile and pricing"
                )
        if self.job_timeout_seconds >= self.job_lease_seconds:
            raise ValueError("Job timeout must be shorter than its lease")
        app = make_url(self.database_url.get_secret_value())
        migration = make_url(self.migration_database_url.get_secret_value())
        test = make_url(self.test_database_url.get_secret_value())
        if app.database == test.database or not test.database.endswith("_test"):
            raise ValueError("Test database must be distinct and end in _test")
        if (app.host, app.port, app.database) != (
            migration.host,
            migration.port,
            migration.database,
        ):
            raise ValueError("Migration URL must address the application database")
        if not self.allowed_origins:
            raise ValueError("At least one exact allowed origin is required")
        for origin in [self.public_origin, *self.allowed_origins]:
            try:
                u = urlsplit(origin)
                _ = u.port
                valid = (
                    u.scheme in {"http", "https"}
                    and u.hostname
                    and not u.username
                    and not u.password
                    and not u.path
                    and not u.query
                    and not u.fragment
                    and "*" not in origin
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError(
                    "Origins must be exact HTTP(S) origins without paths or credentials"
                )
            local = u.hostname in {"localhost", "127.0.0.1", "::1"}
            if self.app_env in {"development", "test"} and not local:
                raise ValueError("Development/test public origins must be loopback")
            if self.app_env == "production" and (local or u.scheme != "https"):
                raise ValueError("Production origins require a non-loopback HTTPS host")
        if self.public_origin not in self.allowed_origins:
            raise ValueError("PUBLIC_ORIGIN must be allowed")
        return self


def load_settings() -> Settings:
    """Ignore unrelated OS variables; reject misspelled application-owned settings."""
    owned = (
        "COLLABORATION_",
        "APP_",
        "AUTH_",
        "AI_",
        "LLM_",
        "DATABASE_",
        "MIGRATION_DATABASE_",
        "TEST_DATABASE_",
        "CACHE_",
        "SECRET_",
        "PRIVATE_",
        "PUBLIC_",
        "ALLOWED_",
        "JOB_",
        "MAX_",
        "DB_",
        "LOG_",
    )
    known = {name.upper() for name in Settings.model_fields}
    permitted_controls = {
        "TEST_ALLOW_RESET",
        "TEST_ALLOW_DB",
        "DB_ADMIN_PASSWORD",
        "DB_OWNER_PASSWORD",
        "DB_APP_PASSWORD",
        "DB_TEST_PASSWORD",
        "CACHE_PASSWORD",
    }
    if any(k.startswith(owned) and k not in known | permitted_controls for k in os.environ):
        raise ValueError("Unknown application environment setting")
    return Settings()
