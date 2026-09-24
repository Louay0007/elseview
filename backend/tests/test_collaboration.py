import asyncio

import httpx
import pytest

from app.collaboration.calendar import escape, fold
from app.collaboration.webhooks import (
    WebhookFailure,
    dispatch,
    signature,
    validate_destination,
    verify_signature,
)
from app.common.errors import DomainError


def test_ics_escaping_and_utf8_folding():
    assert escape("a,b;c\\d\r\nEND:VEVENT") == "a\\,b\\;c\\\\d\\nEND:VEVENT"
    text = "SUMMARY:" + ("é世" * 80)
    encoded = fold(text)
    assert all(len(line.encode()) <= 75 for line in encoded.split("\r\n"))
    assert encoded.replace("\r\n ", "") == text


def test_signature_replay_and_tamper():
    secret = b"x" * 32
    body = b"{}"
    sig = signature(secret, "id", 100, body)
    seen = set()
    assert verify_signature(secret, "id", 100, body, sig, now=100, seen=seen)
    assert not verify_signature(secret, "id", 100, body, sig, now=100, seen=seen)
    assert not verify_signature(secret, "id", 100, body, sig, now=401)
    assert not verify_signature(secret, "other", 100, body, sig, now=100)
    assert not verify_signature(secret, "id", 100, b"changed", sig, now=100)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/h",
        "https://127.0.0.1/h",
        "https://[::1]/h",
        "https://169.254.169.254/h",
        "https://localhost/h",
        "https://example.com/h?secret=x",
        "https://user:secret@example.com/h",
    ],
)
def test_destinations(url):
    with pytest.raises(DomainError):
        validate_destination(url, [url])


def test_dns_private_mixed_denied():
    url = "https://example.com/h"
    for ips in ([], ["93.184.216.34", "10.0.0.1"], ["::ffff:127.0.0.1"]):
        with pytest.raises(DomainError):
            validate_destination(url, [url], ips)


def test_real_httpx_mock_retry_redirect_and_stable_delivery(caplog):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(429 if len(requests) == 1 else 204, headers={"Retry-After": "900"})

    transport = httpx.MockTransport(handle)
    with pytest.raises(WebhookFailure) as caught:
        asyncio.run(dispatch("https://example.com/h", "stable", b"secret" * 8, transport=transport))
    assert caught.value.retryable and caught.value.retry_after == 60
    assert asyncio.run(
        dispatch("https://example.com/h", "stable", b"secret" * 8, transport=transport)
    ) == {"status": "ok"}
    assert requests[0].headers["Webhook-Id"] == requests[1].headers["Webhook-Id"]
    assert requests[0].content == requests[1].content
    for status in (302, 401, 500):
        with pytest.raises(WebhookFailure) as caught:
            asyncio.run(
                dispatch(
                    "https://example.com/h",
                    "stable",
                    b"secret" * 8,
                    transport=httpx.MockTransport(
                        lambda r, status=status: httpx.Response(
                            status, headers={"Location": "http://127.0.0.1/"}
                        )
                    ),
                )
            )
        assert caught.value.retryable == (status == 500)
    assert "secretsecret" not in caplog.text


def test_live_pins_dns_and_tls_hostname_without_outbound(monkeypatch):
    import socket

    seen = []
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )

    def transport(request):
        seen.append(request)
        return httpx.Response(204)

    asyncio.run(
        dispatch(
            "https://example.com/h",
            "id",
            b"x" * 32,
            live=True,
            approved=["https://example.com/h"],
            transport=httpx.MockTransport(transport),
        )
    )
    assert seen[0].url.host == "93.184.216.34"
    assert seen[0].headers["Host"] == "example.com"
    assert seen[0].extensions["sni_hostname"] == "example.com"


def test_dns_rebinding_to_private_never_connects(monkeypatch):
    import socket

    calls = []
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))],
    )

    def transport(request):
        calls.append(request)
        return httpx.Response(204)

    with pytest.raises(DomainError):
        asyncio.run(
            dispatch(
                "https://example.com/h",
                "id",
                b"x" * 32,
                live=True,
                approved=["https://example.com/h"],
                transport=httpx.MockTransport(transport),
            )
        )
    assert calls == []


def test_authority_rechecked_after_resolution_before_http(monkeypatch):
    import socket

    calls = []
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )

    async def stale():
        raise WebhookFailure()

    with pytest.raises(WebhookFailure):
        asyncio.run(
            dispatch(
                "https://example.com/h",
                "id",
                b"x" * 32,
                live=True,
                approved=["https://example.com/h"],
                transport=httpx.MockTransport(lambda req: calls.append(req)),
                before_send=stale,
            )
        )
    assert calls == []
