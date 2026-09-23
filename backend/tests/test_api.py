"""HTTP tests run in-process and never require a database connection."""

import logging
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.main import create_app


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]
    UUID(body["request_id"])
    assert response.headers["x-request-id"] == body["request_id"]
    return body


def test_liveness(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["x-request-id"])


def test_elseview_application_brand(client):
    assert client.app.title == "Elseview"
    assert client.app.description == "See what you’re missing."
    assert client.app.version == "0.1.0"


def test_readiness(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_failure_is_safe(client, monkeypatch):
    monkeypatch.setattr(client.app.state.database, "check_ready", lambda: False)
    body = assert_error(client.get("/api/v1/health/ready"), 503, "NOT_READY")
    assert body["error"]["message"] == "Service is not ready."


def test_valid_request_id_is_preserved(client):
    request_id = str(uuid4())
    response = client.get("/api/v1/health/live", headers={"x-request-id": request_id})
    assert response.headers["x-request-id"] == request_id


@pytest.mark.parametrize("request_id", ["not-a-uuid", "", "a" * 1024])
def test_invalid_request_id_is_replaced(client, request_id):
    response = client.get("/api/v1/health/live", headers={"x-request-id": request_id})
    generated = response.headers["x-request-id"]
    UUID(generated)
    assert generated != request_id


@pytest.mark.parametrize(
    "path", ["/missing", "/docs", "/redoc", "/openapi.json", "/api/v1/openapi.json"]
)
def test_missing_routes_and_disabled_documentation(client, path):
    assert_error(client.get(path), 404, "NOT_FOUND")


def test_disallowed_method(client):
    assert_error(client.post("/api/v1/health/live"), 405, "METHOD_NOT_ALLOWED")


class ExampleBody(BaseModel):
    count: int = Field(gt=0)


def test_validation_error_uses_safe_envelope(settings, monkeypatch):
    app = create_app(settings)
    monkeypatch.setattr(app.state.database, "check_ready", lambda: True)

    @app.post("/test/validation")
    def validate(body: ExampleBody):
        return {"count": body.count}

    with TestClient(app) as client:
        marker = "private-invalid-value-should-not-be-echoed"
        response = client.post("/test/validation", json={"count": marker})
        assert_error(response, 422, "VALIDATION_ERROR")
        assert marker not in response.text


def test_unhandled_exception_does_not_expose_details(settings, monkeypatch, caplog):
    app = create_app(settings)
    monkeypatch.setattr(app.state.database, "check_ready", lambda: True)
    marker = "private-exception-detail-should-not-be-logged"
    secret = settings.secret_key.get_secret_value()

    @app.get("/test/exception")
    def explode():
        raise RuntimeError(f"{marker}: {secret}")

    with caplog.at_level(logging.ERROR, logger="elseview"):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/test/exception")
    assert_error(response, 500, "INTERNAL_ERROR")
    assert marker not in response.text
    assert secret not in response.text
    assert marker not in caplog.text
    assert secret not in caplog.text


def test_oversized_body_is_rejected(client, settings):
    response = client.post("/api/v1/health/live", content=b"x" * (settings.max_request_bytes + 1))
    assert_error(response, 413, "PAYLOAD_TOO_LARGE")


def test_chunked_body_is_bounded_by_actual_bytes(client, settings):
    def chunks():
        yield b"x" * settings.max_request_bytes
        yield b"y"

    response = client.post(
        "/api/v1/health/live", content=chunks(), headers={"transfer-encoding": "chunked"}
    )
    assert_error(response, 413, "PAYLOAD_TOO_LARGE")


@pytest.mark.parametrize("value", ["not-an-integer", "-1"])
def test_invalid_content_length(client, value):
    response = client.post("/api/v1/health/live", content=b"x", headers={"content-length": value})
    assert_error(response, 400, "INVALID_CONTENT_LENGTH")


def test_lifespan_tracks_started_and_disposes_engine(settings, monkeypatch):
    app = create_app(settings)
    disposed = []
    monkeypatch.setattr(app.state.database, "check_ready", lambda: True)
    monkeypatch.setattr(app.state.database.engine, "dispose", lambda: disposed.append(True))
    with TestClient(app):
        assert app.state.started is True
    assert app.state.started is False
    assert disposed == [True]
