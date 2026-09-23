"""Disposable aggregate caching and fail-closed abuse protection.

Never place authoritative business state, credentials, or tokens in this cache.
"""

import hashlib
import hmac
import json
import re

from redis import Redis
from redis.exceptions import RedisError

from app.common.errors import DomainError

MAX_JSON_BYTES = 1_048_576


def canonical_json(value):
    """Bounded, deterministic JSON; reject lossy keys and non-JSON Python values."""

    def validate(item, depth=0):
        if depth > 32:
            raise ValueError("JSON nesting limit exceeded")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings")
                validate(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                validate(child, depth + 1)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError("Unsupported JSON value")

    validate(value)
    result = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False
    ).encode("utf-8")
    if len(result) > MAX_JSON_BYTES:
        raise ValueError("JSON size limit exceeded")
    return result


def _label(value):
    value = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", value):
        raise ValueError("Invalid cache namespace")
    return value


class Cache:
    def __init__(self, settings, namespace="default", *, client=None):
        self.prefix = f"elseview:{_label(namespace)}:"
        self._secret = settings.secret_key.get_secret_value().encode()
        self.client = (
            client
            if client is not None
            else Redis.from_url(
                settings.cache_url.get_secret_value(),
                socket_timeout=1,
                socket_connect_timeout=1,
                decode_responses=False,
            )
        )

    def _digest(self, value):
        return hmac.new(self._secret, canonical_json(value), hashlib.sha256).hexdigest()

    def _key(self, workspace_id, namespace, version, key):
        return (
            self.prefix
            + "aggregate:"
            + self._digest([str(workspace_id), str(namespace), str(version), str(key)])
        )

    def get_json(self, workspace_id, namespace, version, key):
        try:
            raw = self.client.get(self._key(workspace_id, namespace, version, key))
            if raw is None or len(raw) > MAX_JSON_BYTES:
                return None
            value = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            canonical_json(value)
            return value
        except (RedisError, ValueError, TypeError, UnicodeError, RecursionError):
            return None

    def set_json(self, workspace_id, namespace, version, key, value, ttl):
        if type(ttl) is not int or not 1 <= ttl <= 86400:
            raise ValueError("Cache TTL must be between 1 and 86400 seconds")
        encoded = canonical_json(value)
        try:
            self.client.set(self._key(workspace_id, namespace, version, key), encoded, ex=ttl)
        except RedisError:
            pass

    def close(self):
        self.client.close()


class RateLimiter(Cache):
    _SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
    return count
    """

    def check(self, scope, identifier, limit, window_seconds):
        if type(limit) is not int or limit < 1:
            raise ValueError("Rate limit must be positive")
        if type(window_seconds) is not int or not 1 <= window_seconds <= 86400:
            raise ValueError("Invalid rate-limit window")
        key = self.prefix + "rate:" + self._digest([str(scope), str(identifier)])
        try:
            count = int(self.client.eval(self._SCRIPT, 1, key, window_seconds))
        except (RedisError, ValueError, TypeError):
            raise DomainError("RATE_LIMIT_UNAVAILABLE", "Please retry later.", 503) from None
        if count > limit:
            raise DomainError("RATE_LIMITED", "Please retry later.", 429)
