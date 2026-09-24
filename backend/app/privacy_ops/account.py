"""Self-service global erasure. Caller owns the transaction; no network/DB side effects on import."""

import hmac
from uuid import UUID

from sqlalchemy import delete, or_, select, update

from app.auth.models import Membership, OneTimeToken, RefreshToken, User, WorkspaceInvite
from app.auth.security import token_hash, utcnow, verify_password
from app.common import privacy
from app.common.errors import DomainError
from app.common.privacy_models import PrivacyRequest
from app.common.privacy_schemas import PrivacyBody
from app.db import Base
from app.privacy_ops.account_models import AccountErasure
from app.privacy_ops.service import workspace_held
from app.recruiting.models import ParticipantProfile, Qualification
from app.reviews.models import RewardRecord


def affected_workspaces(session, subject_id):
    """Include every loaded scoped producer referencing this user, not just memberships.

    Metadata is populated by application/migration model imports. UUID identity roles
    without an FK are included conservatively (legacy datasets and requester IDs).
    """
    result = set()
    roles = {
        "user_id",
        "subject_id",
        "actor_id",
        "owner_id",
        "creator_id",
        "created_by",
        "requester_id",
        "reviewed_by",
        "recipient_id",
        "invited_by",
        "uploaded_by",
    }
    for table in sorted(Base.metadata.tables.values(), key=lambda table: table.name):
        if "workspace_id" not in table.c:
            continue
        columns = [
            column
            for column in table.c
            if column.name in roles
            or any(fk.target_fullname == "users.id" for fk in column.foreign_keys)
        ]
        if columns:
            result.update(
                session.scalars(
                    select(table.c.workspace_id).where(
                        or_(*(column == subject_id for column in columns))
                    )
                )
            )
    email = session.scalar(select(User.email).where(User.id == subject_id))
    if email:
        result.update(
            session.scalars(
                select(WorkspaceInvite.workspace_id).where(WorkspaceInvite.email == email)
            )
        )
    result.discard(None)
    return sorted(result, key=str)


def _lock_scopes(session, workspace_ids):
    for workspace_id in sorted(workspace_ids, key=str):
        privacy.lock_workspace(session, workspace_id)


def _check_obligations(session, subject_id, workspace_ids):
    if any(workspace_held(session, wid) for wid in workspace_ids):
        raise DomainError("ACCOUNT_ERASURE_HELD", "Erasure is blocked by a legal hold.", 409)
    if (
        session.scalar(
            select(RewardRecord.id)
            .where(RewardRecord.subject_id == subject_id, RewardRecord.state != "paid")
            .limit(1)
        )
        is not None
    ):
        raise DomainError(
            "ACCOUNT_ERASURE_FINANCIAL_PENDING",
            "Settle outstanding rewards before erasing this account.",
            409,
        )


def _check_last_owner(session, subject_id):
    for wid in session.scalars(
        select(Membership.workspace_id).where(
            Membership.user_id == subject_id,
            Membership.role == "owner",
            Membership.status == "active",
        )
    ):
        other = session.scalar(
            select(Membership.id)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.workspace_id == wid,
                Membership.user_id != subject_id,
                Membership.role == "owner",
                Membership.status == "active",
                User.status == "active",
            )
            .limit(1)
        )
        if other is None:
            raise DomainError(
                "LAST_OWNER", "Transfer workspace ownership before erasing your account.", 409
            )


def apply_account_restriction(session, subject_id):
    """Idempotent UUID-only restore primitive, after scoped replay locks/hold checks.

    Retain immutable panel consent evidence, financial records and referential IDs;
    never keep the global email, password, name, qualifications or profile content.
    """
    user = session.scalar(
        select(User)
        .where(User.id == subject_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user is None:
        return
    # Invitations addressed to this account are not linked by user FK. Scrub them
    # before losing the original email; affected_workspaces includes these scopes.
    session.execute(
        update(WorkspaceInvite)
        .where(WorkspaceInvite.email == user.email)
        .values(email=f"erased-{user.id}@invalid.example", revoked_at=utcnow())
    )
    if user.status != "disabled" or user.password_hash != "!account-erased":
        user.auth_version += 1
    user.status = "disabled"
    user.email = f"erased-{user.id}@invalid.example"
    user.display_name = ""
    user.password_hash = "!account-erased"
    user.verified_at = None
    now = utcnow()
    session.execute(
        update(RefreshToken).where(RefreshToken.user_id == subject_id).values(revoked_at=now)
    )
    session.execute(delete(OneTimeToken).where(OneTimeToken.user_id == subject_id))
    session.execute(
        update(Membership).where(Membership.user_id == subject_id).values(status="revoked")
    )
    for profile in session.scalars(
        select(ParticipantProfile).where(ParticipantProfile.user_id == subject_id)
    ):
        profile.attributes_json = {}
        profile.status = "withdrawn"
        session.execute(delete(Qualification).where(Qualification.profile_id == profile.id))
    session.flush()


def request_account_erasure(session, subject_id, body):
    workspace_ids = affected_workspaces(session, subject_id)
    _lock_scopes(session, workspace_ids)
    user = session.scalar(
        select(User)
        .where(User.id == subject_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        user is None
        or user.status != "active"
        or not verify_password(body.current_password.get_secret_value(), user.password_hash)
    ):
        raise DomainError("UNAUTHORIZED", "Current password required.", 401)
    # Concurrent scope creation must not result in a partial global erasure.
    if affected_workspaces(session, subject_id) != workspace_ids:
        raise DomainError(
            "ACCOUNT_SCOPE_CHANGED", "Account scopes changed; retry the request.", 409
        )
    if body.confirmation != "ERASE MY ACCOUNT":
        raise DomainError(
            "CONFIRMATION_REQUIRED", "Explicit account erasure confirmation required.", 422
        )
    _check_last_owner(session, subject_id)
    _check_obligations(session, subject_id, workspace_ids)
    prior = session.scalar(
        select(AccountErasure).where(
            or_(
                AccountErasure.subject_id == subject_id,
                AccountErasure.request_key == body.request_key,
            )
        )
    )
    if prior is not None:
        raise DomainError("ACCOUNT_ERASURE_EXISTS", "Use your erasure status receipt.", 409)
    # The client generates and retains a 256-bit capability before submission so
    # a lost response is recoverable after login has been disabled. Only its hash persists.
    record = AccountErasure(
        subject_id=subject_id,
        request_key=body.request_key,
        capability_hash=token_hash(body.status_capability),
        workspace_ids=[str(wid) for wid in workspace_ids],
        state="pending",
    )
    session.add(record)
    session.flush()
    for wid in workspace_ids:
        privacy.create_request(
            session,
            wid,
            subject_id,
            PrivacyBody(kind="erasure", request_key=f"account-{record.request_key}"),
            account_request_id=record.id,
        )
    apply_account_restriction(session, subject_id)
    session.flush()
    return record


def process_account(session, request_id):
    """Call in a NEW transaction from a sweep/poll, never inside a workspace job lock.

    Failed workspace jobs remain pending and use the existing privacy retry route.
    """
    record = session.get(AccountErasure, request_id)
    if record is None:
        return None
    workspace_ids = [UUID(value) for value in record.workspace_ids]
    _lock_scopes(session, workspace_ids)
    record = session.scalar(
        select(AccountErasure)
        .where(AccountErasure.id == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if record.state == "completed":
        return record
    # A legacy writer may have introduced a new reference after disabling login.
    # Never claim completion until an operator reconciles its scoped erasure.
    if set(affected_workspaces(session, record.subject_id)) - set(workspace_ids):
        return record
    try:
        _check_obligations(session, record.subject_id, workspace_ids)
    except DomainError:
        return record
    for wid in workspace_ids:
        completed = session.scalar(
            select(PrivacyRequest.id).where(
                PrivacyRequest.workspace_id == wid,
                PrivacyRequest.subject_id == record.subject_id,
                PrivacyRequest.request_key == f"account-{record.request_key}",
                PrivacyRequest.kind == "erasure",
                PrivacyRequest.state == "completed",
            )
        )
        if completed is None:
            return record
    apply_account_restriction(session, record.subject_id)
    record.state, record.completed_at = "completed", utcnow()
    session.flush()
    return record


def status_receipt(session, request_key, capability):
    row = session.scalar(select(AccountErasure).where(AccountErasure.request_key == request_key))
    expected = row.capability_hash if row is not None else "0" * 64
    valid = hmac.compare_digest(expected, token_hash(capability))
    if row is None or not valid:
        raise DomainError("NOT_FOUND", "Erasure receipt not found.", 404)
    return row
