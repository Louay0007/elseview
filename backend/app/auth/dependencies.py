from uuid import UUID

from fastapi import Request
from sqlalchemy import select

from app.auth.models import RefreshToken, User
from app.auth.security import decode_access, utcnow
from app.common.errors import DomainError


def current_user(request: Request) -> User:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise DomainError("UNAUTHORIZED", "Authentication required.", 401)
    claims = decode_access(authorization[7:], request.app.state.settings)
    with request.app.state.database.sessions() as session:
        user = session.get(User, UUID(claims["sub"]))
        active_token = session.scalar(
            select(RefreshToken.id).where(
                RefreshToken.user_id == UUID(claims["sub"]),
                RefreshToken.family_id == UUID(claims["sid"]),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.used_at.is_(None),
                RefreshToken.expires_at > utcnow(),
            )
        )
        if (
            user is None
            or user.status != "active"
            or not user.verified_at
            or user.auth_version != claims["ver"]
            or not active_token
        ):
            raise DomainError("UNAUTHORIZED", "Authentication required.", 401)
        request.state.auth_family_id = UUID(claims["sid"])
        session.expunge(user)
        return user


def check_origin(request: Request):
    if request.headers.get("origin") not in request.app.state.settings.allowed_origins:
        raise DomainError("CSRF_FAILED", "Request verification failed.", 403)


def rate_limit(request: Request, scope: str, identifier: str, limit=10):
    # Do not trust unconfigured X-Forwarded-For. Per-account plus conservative connection bucket.
    cache = request.app.state.rate_limiter
    peer = request.client.host if request.client else "unknown"
    cache.check(f"{scope}:peer", peer, limit=100, window_seconds=60)
    cache.check(scope, identifier, limit=limit, window_seconds=60)
