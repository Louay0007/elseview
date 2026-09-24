from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.auth.dependencies import current_user
from app.auth.schemas import AuthLoginResponse, AuthUserResponse


@pytest.mark.parametrize(
    "path,body,method,code,expected",
    [
        (
            "register",
            {"email": "synthetic@example.test", "password": "synthetic-passphrase"},
            "register",
            202,
            {"message": "If the request is eligible, instructions will be delivered."},
        ),
        (
            "verification/request",
            {"email": "synthetic@example.test"},
            "request_token",
            202,
            {"message": "If the request is eligible, instructions will be delivered."},
        ),
        (
            "password-reset/request",
            {"email": "synthetic@example.test"},
            "request_token",
            202,
            {"message": "If the request is eligible, instructions will be delivered."},
        ),
        (
            "verify-email",
            {"token": "synthetic-token-not-a-secret"},
            "consume_token",
            200,
            {"status": "ok"},
        ),
        (
            "password-reset/confirm",
            {"token": "synthetic-token-not-a-secret", "password": "synthetic-passphrase"},
            "consume_token",
            200,
            {"status": "ok"},
        ),
    ],
)
def test_public_success_projections(
    client, settings, monkeypatch, path, body, method, code, expected
):
    monkeypatch.setattr(client.app.state.rate_limiter, "check", Mock())
    handler = Mock()
    monkeypatch.setattr(client.app.state.auth, method, handler)
    response = client.post(
        "/api/v1/auth/" + path, json=body, headers={"Origin": settings.public_origin}
    )
    assert response.status_code == code
    assert response.json() == expected
    handler.assert_called_once()


@pytest.mark.parametrize("path", ["login", "refresh"])
def test_login_projection_keeps_refresh_capability_cookie_only(client, settings, monkeypatch, path):
    monkeypatch.setattr(client.app.state.rate_limiter, "check", Mock())
    expected = {
        "access_token": "synthetic-access",
        "token_type": "bearer",
        "expires_in": 900,
        "csrf_token": "synthetic-csrf",
        "family_id": str(uuid4()),
    }
    monkeypatch.setattr(
        client.app.state.auth,
        path,
        Mock(return_value={**expected, "refresh_token": "synthetic-refresh"}),
    )
    client.cookies.set("elseview_refresh", "synthetic-old-refresh")
    response = client.post(
        "/api/v1/auth/" + path,
        json={"email": "synthetic@example.test", "password": "synthetic-passphrase"}
        if path == "login"
        else None,
        headers={"Origin": settings.public_origin, "X-CSRF-Token": "synthetic-csrf"},
    )
    assert response.status_code == 200
    assert response.json() == expected
    assert "synthetic-refresh" not in response.text
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]


def test_user_projection_excludes_internal_state(client):
    uid = uuid4()
    client.app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        id=uid,
        email="synthetic@example.test",
        display_name="تجربة / Étude",
        password_hash="synthetic-private-hash",
        auth_version=9,
    )
    try:
        response = client.get("/api/v1/me")
        assert response.status_code == 200
        assert response.json() == {
            "id": str(uid),
            "email": "synthetic@example.test",
            "display_name": "تجربة / Étude",
        }
    finally:
        client.app.dependency_overrides.clear()


def test_success_models_reject_accidental_secret_fields():
    with pytest.raises(ValidationError):
        AuthUserResponse(
            id=uuid4(), email="synthetic@example.test", display_name="", password_hash="private"
        )
    with pytest.raises(ValidationError):
        AuthLoginResponse(
            access_token="synthetic-access",
            token_type="bearer",
            expires_in=900,
            csrf_token="synthetic-csrf",
            family_id=uuid4(),
            refresh_token="private",
        )
