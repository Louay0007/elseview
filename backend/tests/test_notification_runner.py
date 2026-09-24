import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from test_mail_delivery import smtp_settings, transport  # noqa: F401

from app.auth import outbox
from app.auth.delivery import deliver
from app.collaboration import mail
from app.jobs.runner import JobRunner


def test_mail_subqueues_alternate_and_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(outbox, "dispatch_one", lambda *args: calls.append("auth") or True)
    monkeypatch.setattr(mail, "dispatch_one", lambda *args: calls.append("notification") or True)
    runner = JobRunner(None, SimpleNamespace())
    for _ in range(4):
        assert runner._send_next_mail()
    assert calls == ["auth", "notification", "auth", "notification"]
    calls.clear()
    monkeypatch.setattr(outbox, "dispatch_one", lambda *args: calls.append("empty") or False)
    assert runner._send_next_mail()
    assert calls == ["empty", "notification"]


@pytest.mark.parametrize("purpose", ["interview_reminder", "diary_reminder"])
def test_reminder_transport_has_no_capability_or_private_research(settings, transport, purpose):  # noqa: F811
    deliver(smtp_settings(settings), "synthetic@example.test", purpose, None)
    message = transport[0].send_message.call_args.args[0]
    assert "Sign in to review your current schedule." in message.get_content()
    assert "one-time code" not in message.get_content()
    assert "http" not in message.get_content()
    deliver(settings, "synthetic@example.test", purpose, None)
    path = next((settings.private_root / "dev-mail").glob("*.json"))
    assert json.loads(path.read_text()) == {
        "recipient": "synthetic@example.test",
        "purpose": purpose,
        "token": None,
    }
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("mode,enabled", [("local", True), ("smtp", False), ("disabled", False)])
def test_immediate_notifications_never_race_worker_or_send_live(monkeypatch, mode, enabled):
    calls = []
    monkeypatch.setattr(mail, "dispatch_one", lambda *args: calls.append(1))
    mail.dispatch_local(
        None, SimpleNamespace(app_env="test", mail_mode=mode, job_runner_enabled=enabled), uuid4()
    )
    assert not calls
