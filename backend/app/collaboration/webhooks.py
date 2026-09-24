"""Metadata-only webhooks. Disabled by default; mock and explicit pinned live transport.

Stable IDs make retries receiver-deduplicable; timestamps alone are not a replay cache.
No arbitrary destination, response body, exception text, or credential is logged.
"""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import socket
import time
from urllib.parse import urlsplit

import httpx

from app.auth.service import require_workspace
from app.common.errors import DomainError
from app.common.privacy import lock_workspace, require_unrestricted
from app.jobs import service as jobs

from .models import Integration, WebhookDelivery


class WebhookFailure(Exception):
    error_code = "webhook_delivery_failed"

    def __init__(self, retryable=False, retry_after=1):
        super().__init__("Webhook delivery failed")
        self.retryable = retryable
        self.retry_after = max(1, min(60, int(retry_after)))


def validate_destination(url, approved, addresses=None):
    try:
        u = urlsplit(url)
        if (
            url not in approved
            or any(ord(char) < 33 or ord(char) == 127 for char in url)
            or "\\" in url
            or u.scheme != "https"
            or not u.hostname
            or u.username
            or u.password
            or u.fragment
            or u.query
            or u.port not in (None, 443)
        ):
            raise ValueError()
        if u.hostname.lower() in {"localhost", "metadata.google.internal"} or u.hostname.endswith(
            (".localhost", ".local", ".internal")
        ):
            raise ValueError()
        try:
            ips = [ipaddress.ip_address(u.hostname)]
        except ValueError:
            ips = []
        if addresses is not None:
            ips += [ipaddress.ip_address(a) for a in addresses]
        if any(not ip.is_global for ip in ips) or addresses == []:
            raise ValueError()
    except (ValueError, TypeError):
        raise DomainError("DESTINATION_NOT_APPROVED", "Destination is not approved.", 422) from None
    return u


def signing_secret(settings, integration_id):
    secret = getattr(settings, "collaboration_webhook_secret", None)
    raw = secret.get_secret_value() if hasattr(secret, "get_secret_value") else secret
    if not raw or len(raw) < 32:
        raise WebhookFailure()
    return hmac.new(raw.encode(), str(integration_id).encode(), hashlib.sha256).digest()


def signature(secret, delivery_id, timestamp, body):
    return hmac.new(
        secret,
        str(timestamp).encode() + b"." + str(delivery_id).encode() + b"." + body,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(secret, delivery_id, timestamp, body, supplied, *, now=None, seen=None):
    try:
        valid = abs(
            (int(time.time()) if now is None else now) - int(timestamp)
        ) <= 300 and hmac.compare_digest(signature(secret, delivery_id, timestamp, body), supplied)
    except (ValueError, TypeError):
        return False
    if not valid or (seen is not None and delivery_id in seen):
        return False
    if seen is not None:
        seen.add(delivery_id)
    return True


def authorize_job(session, job):
    try:
        w = lock_workspace(session, job.workspace_id)
        if w.status != "active" or w.privacy_epoch != job.privacy_epoch:
            return False
        require_workspace(session, job.requester_id, job.workspace_id, "members.manage")
        require_unrestricted(session, job.workspace_id, job.requester_id)
        d = session.get(WebhookDelivery, job.target_id)
        if (
            not d
            or d.workspace_id != job.workspace_id
            or d.requester_id != job.requester_id
            or d.state != "pending"
        ):
            return False
        i = session.get(Integration, d.integration_id)
        if (
            not i
            or i.workspace_id != job.workspace_id
            or not i.enabled
            or i.revision != d.integration_revision
        ):
            return False
        require_workspace(session, i.creator_id, job.workspace_id, "members.manage")
        require_unrestricted(session, job.workspace_id, i.creator_id)
        return True
    except DomainError:
        return False


def finish_delivery(session, job, *, state="succeeded", retry_after=None):
    d = session.get(WebhookDelivery, job.target_id)
    if d and d.workspace_id == job.workspace_id:
        d.state = state if state in {"pending", "succeeded", "failed", "cancelled"} else "failed"


def _prepare(database, settings, job):
    with database.sessions.begin() as session:
        fresh = jobs._fence(session, job.id, job.lease_token)
        if not fresh or not authorize_job(session, fresh):
            raise WebhookFailure()
        d = session.get(WebhookDelivery, fresh.target_id)
        i = session.get(Integration, d.integration_id)
        if getattr(settings, "collaboration_integration_mode", "disabled") not in {"mock", "live"}:
            raise WebhookFailure()
        validate_destination(
            i.destination, getattr(settings, "collaboration_webhook_destinations", [])
        )
        return i.destination, str(d.id), signing_secret(settings, i.id)


async def dispatch(
    url,
    delivery_id,
    secret,
    *,
    transport=None,
    timeout=3,
    live=False,
    approved=(),
    before_send=None,
):
    # No user payload, contact, study title, answer, report content or destination in jobs.
    body = json.dumps(
        {"id": delivery_id, "type": "collaboration.test", "schema_version": 1},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    stamp = str(int(time.time()))
    headers = {
        "Content-Type": "application/json",
        "Webhook-Id": delivery_id,
        "Webhook-Timestamp": stamp,
        "Webhook-Signature": signature(secret, delivery_id, stamp, body),
    }
    extensions = {}
    if live:
        u = validate_destination(url, approved)
        try:
            resolved = await asyncio.wait_for(
                asyncio.to_thread(socket.getaddrinfo, u.hostname, 443, type=socket.SOCK_STREAM),
                timeout=timeout,
            )
        except (OSError, TimeoutError):
            raise WebhookFailure(True) from None
        addresses = sorted({r[4][0] for r in resolved})
        validate_destination(url, approved, addresses)
        # Connect to the vetted literal IP, retaining hostname for TLS verification and Host.
        ip = addresses[0]
        host = "[" + ip + "]" if ":" in ip else ip
        url = "https://" + host + (u.path or "/")
        headers["Host"] = u.hostname
        extensions["sni_hostname"] = u.hostname
    elif transport is None:
        transport = httpx.MockTransport(lambda request: httpx.Response(204))
    if transport is not None and not isinstance(transport, httpx.MockTransport):
        raise WebhookFailure()
    if before_send is not None:
        await before_send()
    try:
        async with httpx.AsyncClient(
            transport=transport, follow_redirects=False, timeout=timeout, trust_env=False
        ) as client:
            # Stream without reading response body; arbitrary receiver payload never retained.
            async with client.stream(
                "POST", url, content=body, headers=headers, extensions=extensions
            ) as response:
                status = response.status_code
                retry_header = response.headers.get("Retry-After", "1")
        if status == 429 or status >= 500:
            retry = retry_header
            raise WebhookFailure(True, int(retry) if retry.isdigit() else 1)
        if not 200 <= status < 300:
            raise WebhookFailure()
    except httpx.HTTPError:
        raise WebhookFailure(True) from None
    return {"status": "ok"}


async def execute(database, settings, job):
    url, did, secret = await asyncio.to_thread(_prepare, database, settings, job)

    async def recheck():
        await asyncio.to_thread(_prepare, database, settings, job)

    return await dispatch(
        url,
        did,
        secret,
        timeout=getattr(settings, "collaboration_webhook_timeout_seconds", 3),
        live=settings.collaboration_integration_mode == "live",
        approved=settings.collaboration_webhook_destinations,
        before_send=recheck,
    )
