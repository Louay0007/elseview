"""Opt-in built frontend -> real HTTP -> isolated PostgreSQL/Valkey, without auth bypasses."""

import json
import os
import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path
from threading import Thread
from uuid import uuid4

import pytest
import uvicorn
from fastapi.responses import HTMLResponse
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles

from app.auth.models import Membership, RefreshToken, User, Workspace
from app.main import create_app
from app.recruiting.models import ParticipantProfile

pytestmark = [pytest.mark.db, pytest.mark.cache, pytest.mark.browser]
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def browser_build():
    chrome = Path(
        os.environ.get(
            "CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
    )
    assert chrome.is_file() and shutil.which("node") and shutil.which("npm"), (
        "Live browser tests require installed Chrome, Node and frontend dependencies"
    )
    result = subprocess.run(
        ["npm", "run", "build"], cwd=ROOT / "frontend", capture_output=True, timeout=120
    )
    assert result.returncode == 0, "Build the frontend successfully before browser integration"
    return ROOT / "frontend/dist"


@pytest.mark.parametrize("viewport", ["1440x900", "390x844"])
def test_live_account_workspace_and_session_lifecycle(
    settings, db_engine, browser_build, viewport, request
):
    listener = socket.socket()
    request.addfinalizer(listener.close)
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    config = settings.model_copy(
        update={
            "database_url": SecretStr(db_engine.url.render_as_string(hide_password=False)),
            "cache_url": SecretStr(os.environ["CACHE_URL"]),
            "public_origin": origin,
            "allowed_origins": [origin],
            "job_runner_enabled": False,
            "mail_mode": "local",
        }
    )
    app = create_app(config)
    request.addfinalizer(app.state.database.close)
    request.addfinalizer(app.state.cache.close)
    request.addfinalizer(app.state.rate_limiter.close)
    email = f"browser-{uuid4().hex}@example.test"
    password = secrets.token_urlsafe(32)
    workspace_name = f"Étude دراسة {uuid4().hex[:8]}"
    # Provision only the verified synthetic identity; all measured actions use the real UI.
    deliveries = []
    original_delivery = app.state.auth.deliver
    try:
        app.state.auth.deliver = lambda *args: deliveries.append(args)
        app.state.auth.register(email, password, "Chercheur باحث")
        app.state.auth.consume_token(deliveries[-1][2], "verify")
    finally:
        app.state.auth.deliver = original_delivery
        deliveries.clear()
    payload = json.dumps({"email": email, "password": password, "workspace": workspace_name})
    fixture = (
        Path(__file__)
        .with_name("live_account.html")
        .read_text()
        .replace("__ACCOUNT_FIXTURE__", payload.replace("<", "\\u003c"))
    )

    @app.get("/tests/account-live.html", include_in_schema=False)
    def test_page():
        return HTMLResponse(fixture, headers={"Cache-Control": "no-store"})

    app.mount("/", StaticFiles(directory=browser_build, html=True))
    server = uvicorn.Server(
        uvicorn.Config(app, access_log=False, log_config=None, log_level="critical")
    )
    thread = Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    try:
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started, "Local test API failed to become ready"
        result = subprocess.run(
            ["node", "scripts/browser_contracts.mjs", "/tests/account-live.html"],
            cwd=ROOT,
            env=os.environ | {"CONTRACT_BASE_URL": origin, "CONTRACT_VIEWPORT": viewport},
            capture_output=True,
            text=True,
            timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert '"status":"passed"' in result.stdout
        with Session(db_engine) as session:
            user = session.scalar(select(User).where(User.email == email))
            workspaces = session.scalars(
                select(Workspace).join(Membership).where(Membership.user_id == user.id)
            ).all()
            assert len(workspaces) == 1 and workspaces[0].name == workspace_name
            profiles = session.scalars(
                select(ParticipantProfile).where(ParticipantProfile.user_id == user.id)
            ).all()
            assert len(profiles) == 1 and profiles[0].status == "active"
            assert profiles[0].attributes["age"] == 32
            tokens = session.scalars(
                select(RefreshToken).where(RefreshToken.user_id == user.id)
            ).all()
            assert len(tokens) == 2 and all(token.revoked_at is not None for token in tokens)
    finally:
        server.should_exit = True
        if thread.ident is not None:
            thread.join(timeout=10)
        assert not thread.is_alive(), "Owned browser test server did not stop"
