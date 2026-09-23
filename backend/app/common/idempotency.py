"""Transactional PostgreSQL idempotency; caller owns commit and rollback.

Callers must exclude secrets/tokens from response and pass only safe or already
hashed sensitive fields in payload. Only payload/key digests are persisted.
Expired records remain reserved and reject reuse rather than repeat effects.
Permanent domain uniqueness constraints are still required: a new key (or removal
of a retained record) is not protected by this scoped replay mechanism.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import Mapped, mapped_column

from app.common.cache import canonical_json
from app.common.errors import DomainError
from app.db import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "actor_id", "operation", "key_hash", name="uq_idempotency_scope_key"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    operation: Mapped[str] = mapped_column(String(96))
    key_hash: Mapped[str] = mapped_column(String(64))
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC) + timedelta(hours=24)
    )


def execute_idempotent(session, workspace_id, actor_id, operation, key, payload, callback):
    """Deduplicate a retained committed scope/key, returning (status, JSON).

    ON CONFLICT waits for the competing transaction before row locking/replay.
    Exceptions intentionally propagate: the outer transaction MUST roll back.
    """
    if not isinstance(operation, str) or not 1 <= len(operation) <= 96:
        raise ValueError("Invalid idempotency operation")
    if not isinstance(key, str) or not 1 <= len(key.encode("utf-8")) <= 512:
        raise DomainError("INVALID_IDEMPOTENCY_KEY", "Invalid idempotency key.", 400)
    digest = hashlib.sha256(canonical_json(payload)).hexdigest()
    scope = dict(
        workspace_id=workspace_id,
        actor_id=actor_id,
        operation=operation,
        key_hash=hashlib.sha256(key.encode("utf-8")).hexdigest(),
    )
    now = datetime.now(UTC)
    session.execute(
        insert(IdempotencyRecord)
        .values(**scope, request_hash=digest, expires_at=now + timedelta(hours=24))
        .on_conflict_do_nothing(constraint="uq_idempotency_scope_key")
    )
    record = session.execute(
        select(IdempotencyRecord)
        .filter_by(**scope)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()
    if record.expires_at <= datetime.now(UTC):
        raise DomainError("IDEMPOTENCY_KEY_EXPIRED", "Idempotency key has expired.", 409)
    if record.request_hash != digest:
        raise DomainError(
            "IDEMPOTENCY_CONFLICT", "Idempotency key was used for another request.", 409
        )
    if record.status is not None:
        return record.status, record.response
    status, response = callback()
    if type(status) is not int or not 100 <= status <= 599:
        raise ValueError("Invalid callback status")
    canonical_json(response)
    record.status, record.response = status, response
    session.flush()
    return status, response
