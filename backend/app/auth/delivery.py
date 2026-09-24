"""Opt-in TLS mail transport and private local capture; never log message contents."""

import json
import os
import smtplib
import ssl
import time
from email.errors import HeaderParseError
from email.headerregistry import Address
from email.message import EmailMessage
from uuid import uuid4

from app.common.errors import DomainError

SUBJECTS = {
    "verify": "Verify your Elseview email",
    "reset": "Reset your Elseview password",
    "workspace_invite": "Your Elseview workspace invitation",
    "recruitment_invite": "Your Elseview research invitation",
    "interview_reminder": "Your Elseview interview reminder",
    "diary_reminder": "Your Elseview diary reminder",
}
REMINDERS = {"interview_reminder", "diary_reminder"}


def deliver(settings, email, purpose, token):
    if settings.mail_mode == "local":
        return deliver_local(settings, email, purpose, token)
    if settings.mail_mode != "smtp" or settings.app_env != "production":
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery is not configured.", 503)
    return deliver_smtp(settings, email, purpose, token)


def deliver_smtp(settings, email, purpose, token):
    if not settings.smtp_delivery_approved:
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery is not configured.", 503)
    try:
        recipient = Address(addr_spec=email)
        sender = Address(addr_spec=settings.smtp_sender)
        if (
            not recipient.username
            or not recipient.domain
            or not email.isascii()
            or purpose not in SUBJECTS
            or (purpose in REMINDERS and token is not None)
            or (
                purpose not in REMINDERS
                and (
                    not isinstance(token, str)
                    or not 1 <= len(token) <= 256
                    or any(ord(c) < 33 or ord(c) > 126 for c in token)
                )
            )
        ):
            raise ValueError("Invalid delivery input")
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = SUBJECTS[purpose]
        if purpose in REMINDERS:
            message.set_content(
                "You have an upcoming interview or an open diary activity in Elseview. "
                "Sign in to review your current schedule. "
                "You can turn off email reminders in your notification preferences.\n"
            )
        else:
            message.set_content(
                "Use this one-time code in Elseview to complete your request:\n\n"
                + token
                + "\n\nDo not share this code. If you did not request it, ignore this message.\n"
            )
    except (TypeError, ValueError, HeaderParseError):
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery cannot be prepared.", 503) from None

    connection = None
    dispatching = False
    try:
        context = ssl.create_default_context()
        if settings.smtp_tls == "implicit":
            connection = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=context,
            )
        else:
            connection = smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
            )
            connection.ehlo()
            connection.starttls(context=context)
            connection.ehlo()
        connection.login(
            settings.smtp_username.get_secret_value(), settings.smtp_password.get_secret_value()
        )
        dispatching = True
        refused = connection.send_message(
            message, from_addr=sender.addr_spec, to_addrs=[recipient.addr_spec]
        )
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused):
        raise DomainError("DELIVERY_REJECTED", "Delivery was rejected.", 503) from None
    except smtplib.SMTPDataError as exc:
        code = "DELIVERY_REJECTED" if 400 <= exc.smtp_code < 600 else "DELIVERY_UNCERTAIN"
        raise DomainError(code, "Delivery was not confirmed.", 503) from None
    except (smtplib.SMTPException, OSError, UnicodeError):
        code = "DELIVERY_UNCERTAIN" if dispatching else "DELIVERY_UNAVAILABLE"
        raise DomainError(code, "Delivery was not confirmed.", 503) from None
    finally:
        if connection is not None:
            # QUIT failure after DATA acceptance must not turn a successful send into a retry.
            try:
                connection.close()
            except (smtplib.SMTPException, OSError):
                pass


def cleanup_local(settings):
    """Separate from SQL retention: private dev captures expire after 24 hours.

    Also run at application startup/shutdown, so expiry does not need another send.
    Production never creates this spool; it is not a durable mailbox or audit log.
    """
    if settings.app_env not in {"development", "test"}:
        return
    root = settings.private_root / "dev-mail"
    if root.is_symlink():
        raise ValueError("Development mailbox cannot be a symlink")
    for old in root.glob("*.json"):
        if old.is_symlink() or old.stat().st_mtime < time.time() - 86400:
            old.unlink(missing_ok=True)


def deliver_local(settings, email, purpose, token):
    if settings.app_env not in {"development", "test"}:
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery is not configured.", 503)
    root = settings.private_root / "dev-mail"
    cleanup_local(settings)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    if sum(1 for _ in root.glob("*.json")) >= 1000:
        raise DomainError("DELIVERY_UNAVAILABLE", "Delivery is temporarily unavailable.", 503)
    path = root / f"{uuid4()}.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        json.dump({"recipient": email, "purpose": purpose, "token": token}, output)
