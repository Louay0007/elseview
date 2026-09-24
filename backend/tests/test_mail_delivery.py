import smtplib
from smtplib import SMTP as StdlibSMTP
from unittest.mock import Mock

import pytest
from pydantic import SecretStr, ValidationError

from app.auth.delivery import deliver
from app.common.errors import DomainError
from app.config import Settings, load_settings


def smtp_settings(settings, **changes):
    values = settings.model_dump()
    values.update(
        app_env="production",
        public_origin="https://research.example.test",
        allowed_origins=["https://research.example.test"],
        mail_mode="smtp",
        smtp_host="smtp.example.test",
        smtp_sender="noreply@example.test",
        smtp_username="synthetic-user",
        smtp_password="synthetic-password",
        smtp_delivery_approved=True,
        job_runner_enabled=True,
    )
    values.update(changes)
    return Settings(**values)


@pytest.fixture
def transport(monkeypatch):
    connection = Mock()
    connection.send_message.return_value = {}
    implicit = Mock(return_value=connection)
    starttls = Mock(return_value=connection)
    monkeypatch.setattr(smtplib, "SMTP_SSL", implicit)
    monkeypatch.setattr(smtplib, "SMTP", starttls)
    return connection, implicit, starttls


def test_local_mode_still_captures_privately(settings, transport):
    deliver(settings, "synthetic@example.test", "verify", "synthetic-code")
    assert len(list((settings.private_root / "dev-mail").glob("*.json"))) == 1
    transport[1].assert_not_called()
    transport[2].assert_not_called()


def test_disabled_mode_never_sends(settings, transport):
    settings.mail_mode = "disabled"
    with pytest.raises(DomainError) as exc:
        deliver(settings, "synthetic@example.test", "verify", "synthetic-code")
    assert exc.value.code == "DELIVERY_UNAVAILABLE"
    transport[1].assert_not_called()


@pytest.mark.parametrize("purpose", ["verify", "reset", "workspace_invite", "recruitment_invite"])
@pytest.mark.parametrize("tls", ["implicit", "starttls"])
def test_tls_send_has_explicit_single_recipient(settings, transport, purpose, tls):
    config = smtp_settings(settings, smtp_tls=tls)
    connection, implicit, starttls = transport
    deliver(config, "synthetic@example.test", purpose, "synthetic-code")
    factory = implicit if tls == "implicit" else starttls
    assert factory.call_args.kwargs["timeout"] == 5
    if tls == "implicit":
        assert factory.call_args.kwargs["context"].check_hostname
        starttls.assert_not_called()
    else:
        assert connection.starttls.call_args.kwargs["context"].check_hostname
        assert connection.ehlo.call_count == 2
        assert [call[0] for call in connection.method_calls][:4] == [
            "ehlo",
            "starttls",
            "ehlo",
            "login",
        ]
    call = connection.send_message.call_args
    assert call.kwargs == {
        "from_addr": "noreply@example.test",
        "to_addrs": ["synthetic@example.test"],
    }
    assert "synthetic-code" in call.args[0].get_content()
    assert "synthetic-password" not in str(call.args[0])
    connection.close.assert_called_once()


@pytest.mark.parametrize(
    "changes",
    [
        {"job_runner_enabled": False},
        {"smtp_delivery_approved": False},
        {"smtp_host": "https://smtp.example.test"},
        {"smtp_host": "smtp.example.test\n"},
        {"smtp_sender": "bad\r\nBcc: other@example.test"},
        {"smtp_sender": ""},
        {"smtp_password": ""},
        {"smtp_username": "synthetic-é"},
        {"smtp_password": "synthetic-é"},
        {"smtp_tls": "none"},
        {"smtp_timeout_seconds": 0},
        {"smtp_timeout_seconds": 20},
    ],
)
def test_unsafe_smtp_config_rejected(settings, changes):
    with pytest.raises(ValidationError):
        smtp_settings(settings, **changes)


def test_live_mail_rejected_in_development(settings):
    with pytest.raises(ValidationError):
        smtp_settings(
            settings,
            app_env="development",
            public_origin="http://localhost:8080",
            allowed_origins=["http://localhost:8080"],
        )


def test_smtp_credentials_are_redacted(settings):
    config = smtp_settings(settings)
    assert "synthetic-password" not in repr(config)
    assert "synthetic-user" not in repr(config)


@pytest.mark.parametrize(
    "email,purpose,token",
    [
        ("synthetic@example.test\r\nBcc: other@example.test", "verify", "code"),
        ("synthetic@example.test", "unknown", "code"),
        ("synthetic@example.test", "verify", "code\r\ncontent"),
        ("synthetic@example.test", "verify", ""),
        ("synthetic@example.test", "interview_reminder", "unexpected-code"),
        ("synthetic@example.test", "diary_reminder", "unexpected-code"),
    ],
)
def test_bad_delivery_never_connects(settings, transport, email, purpose, token):
    with pytest.raises(DomainError):
        deliver(smtp_settings(settings), email, purpose, token)
    transport[1].assert_not_called()


@pytest.mark.parametrize(
    "failure,code",
    [
        (
            smtplib.SMTPRecipientsRefused({"synthetic@example.test": (550, b"private")}),
            "DELIVERY_REJECTED",
        ),
        (smtplib.SMTPDataError(550, b"private"), "DELIVERY_REJECTED"),
        (smtplib.SMTPDataError(250, b"private"), "DELIVERY_UNCERTAIN"),
        (TimeoutError("private"), "DELIVERY_UNCERTAIN"),
        (smtplib.SMTPServerDisconnected("private"), "DELIVERY_UNCERTAIN"),
    ],
)
def test_send_failure_is_not_retried_or_exposed(settings, transport, failure, code):
    transport[0].send_message.side_effect = failure
    with pytest.raises(DomainError) as exc:
        deliver(smtp_settings(settings), "synthetic@example.test", "verify", "code")
    assert exc.value.code == code
    assert "private" not in str(exc.value)
    assert exc.value.__suppress_context__
    transport[0].send_message.assert_called_once()
    transport[0].close.assert_called_once()


def test_authentication_failure_does_not_dispatch(settings, transport):
    transport[0].login.side_effect = smtplib.SMTPAuthenticationError(535, b"private")
    with pytest.raises(DomainError) as exc:
        deliver(smtp_settings(settings), "synthetic@example.test", "verify", "code")
    assert exc.value.code == "DELIVERY_UNAVAILABLE"
    transport[0].send_message.assert_not_called()


def test_stdlib_auth_encoding_failure_is_known_predispatch(settings, transport):
    from app.auth.outbox import send_outcome

    config = smtp_settings(settings)
    # Defense in depth if an embedding caller mutates previously validated settings.
    config.smtp_password = SecretStr("synthetic-é")
    smtp = StdlibSMTP(local_hostname="synthetic.invalid")
    smtp.ehlo_resp = b"ready"
    smtp.esmtp_features = {"auth": "PLAIN"}
    transport[0].login.side_effect = smtp.login
    assert (
        send_outcome(
            lambda *args: deliver(config, *args), "eligible@example.test", "reset", "synthetic-code"
        )
        == "DELIVERY_UNAVAILABLE"
    )
    transport[0].login.assert_called_once()
    transport[0].send_message.assert_not_called()


def test_no_starttls_downgrade(settings, transport):
    transport[0].starttls.side_effect = smtplib.SMTPNotSupportedError("private")
    with pytest.raises(DomainError):
        deliver(
            smtp_settings(settings, smtp_tls="starttls"), "synthetic@example.test", "verify", "code"
        )
    transport[0].login.assert_not_called()
    transport[0].send_message.assert_not_called()


def test_cleanup_failure_does_not_retry_accepted_mail(settings, transport):
    transport[0].close.side_effect = OSError("private")
    deliver(smtp_settings(settings), "synthetic@example.test", "verify", "code")
    transport[0].send_message.assert_called_once()


@pytest.mark.parametrize(
    "code", ["DELIVERY_UNAVAILABLE", "DELIVERY_REJECTED", "DELIVERY_UNCERTAIN"]
)
def test_public_instruction_failure_hides_recipient_and_capability(settings, caplog, code):
    from app.auth.outbox import send_outcome

    sender = Mock(side_effect=DomainError(code, "private provider detail", 503))
    assert send_outcome(sender, "synthetic@example.test", "reset", "synthetic-code") == code
    sender.assert_called_once_with("synthetic@example.test", "reset", "synthetic-code")
    assert not caplog.text
    for private in ("private provider detail", "synthetic@example.test", "synthetic-code"):
        assert private not in caplog.text


def test_unclassified_delivery_failure_is_uncertain(settings):
    from app.auth.outbox import send_outcome

    sender = Mock(side_effect=DomainError("UNEXPECTED", "private error", 500))
    assert (
        send_outcome(sender, "synthetic@example.test", "reset", "synthetic-code")
        == "DELIVERY_UNCERTAIN"
    )


def test_smtp_setting_typo_is_rejected(monkeypatch):
    monkeypatch.setenv("SMTP_PASSWROD", "synthetic-password")
    with pytest.raises(ValueError, match="Unknown application environment setting"):
        load_settings()
