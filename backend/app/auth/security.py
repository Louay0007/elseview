import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.common.errors import DomainError

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("not-a-real-user-password-" + secrets.token_hex(16))


def utcnow():
    return datetime.now(UTC)


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def verify_password(value: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(value, hashed)
    except Exception:
        return False


def access_token(user, family_id, settings):
    now = utcnow()
    return jwt.encode(
        {
            "sub": str(user.id),
            "sid": str(family_id),
            "ver": user.auth_version,
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=settings.auth_access_seconds),
            "jti": str(uuid4()),
            "type": "access",
        },
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    )


def decode_access(raw: str, settings):
    try:
        claims = jwt.decode(
            raw,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
            issuer=settings.auth_issuer,
            audience=settings.auth_audience,
            options={
                "require": ["sub", "sid", "ver", "exp", "iat", "nbf", "iss", "aud", "jti", "type"]
            },
        )
        if claims["type"] != "access" or type(claims["ver"]) is not int:
            raise ValueError()
        UUID(claims["sub"])
        UUID(claims["sid"])
        return claims
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise DomainError("UNAUTHORIZED", "Authentication required.", 401) from None
