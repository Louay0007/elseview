"""Release checks over installed contracts and dependency manifests, no network."""

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "origin", ["https://attacker.invalid", "null", "http://localhost:8080.attacker.invalid"]
)
def test_browser_preflight_denies_unapproved_origin(client, origin):
    response = client.options(
        "/api/v1/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_preflight_allows_exact_origin_not_wildcard(client):
    response = client.options(
        "/api/v1/me",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8080"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_oversized_auth_body_is_rejected_before_auth_or_database(client):
    response = client.post(
        "/api/v1/auth/login",
        content=b"x" * (client.app.state.settings.max_request_bytes + 1),
        headers={"Origin": "http://localhost:8080"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_python_lock_requires_hashes_and_no_unpinned_runtime_installs():
    root = Path(__file__).parents[1]
    lock = (root / "requirements.lock").read_text()
    assert "--hash=sha256:" in lock
    docker = (root / "Dockerfile").read_text()
    assert "--require-hashes" in docker
    assert "USER 10001:10001" in docker
