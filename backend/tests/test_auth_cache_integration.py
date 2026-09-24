import os
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.common.cache import RateLimiter
from app.main import create_app


@pytest.mark.db
@pytest.mark.cache
def test_auth_endpoints_use_real_rate_limit_and_fail_closed(settings, db_engine):
    url = urlsplit(os.environ["CACHE_URL"])
    config = settings.model_copy(
        update={
            "cache_url": SecretStr(urlunsplit(url._replace(path="/15", query=""))),
            "database_url": SecretStr(db_engine.url.render_as_string(hide_password=False)),
        }
    )
    app = create_app(config)
    app.state.rate_limiter.close()
    limiter = RateLimiter(config, namespace="auth_test_" + uuid4().hex)
    app.state.rate_limiter = limiter
    email = f"missing-{uuid4().hex}@example.test"
    try:
        with TestClient(app) as client:
            for _ in range(10):
                assert (
                    client.post(
                        "/api/v1/auth/login",
                        headers={"origin": config.public_origin},
                        json={"email": email, "password": "incorrect"},
                    ).status_code
                    == 401
                )
            response = client.post(
                "/api/v1/auth/login",
                headers={"origin": config.public_origin},
                json={"email": email, "password": "incorrect"},
            )
            assert response.status_code == 429
            assert response.json()["error"]["code"] == "RATE_LIMITED"
    finally:
        # Redis clients reconnect after close; remove this test's own namespace only.
        keys = list(limiter.client.scan_iter(match=limiter.prefix + "*"))
        if keys:
            limiter.client.delete(*keys)
        limiter.close()
