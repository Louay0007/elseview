"""All mutations participate in the caller's transaction; none commits."""

import hashlib
import json
from datetime import UTC, timedelta
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.auth.models import Membership, User, Workspace
from app.auth.service import require_workspace
from app.common.errors import DomainError
from app.jobs.models import Job, JobAttempt


async def system_check(payload):
    return {"status": "ok"}


# Explicit server-side allowlist: handler, replay safety. No dynamic imports.
REGISTRY = {"system.check": (system_check, True)}
TERMINAL = {"succeeded", "failed", "cancelled", "uncertain"}


def now(session):
    return session.scalar(select(func.clock_timestamp()))


def _authority(session, job):
    workspace = session.scalar(
        select(Workspace)
        .where(Workspace.id == job.workspace_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    user = session.scalar(
        select(User)
        .where(User.id == job.requester_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    member = session.scalar(
        select(Membership)
        .where(Membership.workspace_id == job.workspace_id, Membership.user_id == job.requester_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    return bool(
        workspace
        and user
        and member
        and workspace.status == "active"
        and workspace.privacy_epoch == job.privacy_epoch
        and user.status == "active"
        and user.verified_at is not None
        and member.status == "active"
        and member.role in {"owner", "admin", "researcher"}
    )


def enqueue(
    session,
    *,
    workspace_id,
    requester_id,
    command_key,
    kind="system.check",
    payload=None,
    target_id=None,
    run_after=None,
    max_attempts=3,
):
    require_workspace(session, requester_id, workspace_id, "jobs.create")
    if kind not in REGISTRY:
        raise DomainError("invalid_job_kind", "Unknown job kind", 422)
    # The demo accepts no arbitrary data, preventing accidental PII storage.
    if payload is not None and payload != {}:
        raise DomainError("invalid_job_payload", "system.check requires an empty payload", 422)
    if not isinstance(command_key, str) or not 1 <= len(command_key) <= 128:
        raise DomainError("invalid_command_key", "Command key must contain 1–128 characters", 422)
    if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
        raise DomainError("invalid_attempt_limit", "Invalid attempt limit", 422)
    if run_after is not None and (run_after.tzinfo is None or run_after.utcoffset() is None):
        raise DomainError("invalid_schedule", "Schedule must include timezone", 422)
    digest = hashlib.sha256(
        json.dumps(
            {
                "kind": kind,
                "payload": payload or {},
                "target_id": str(target_id) if target_id else None,
                "max_attempts": max_attempts,
                "run_after": run_after.astimezone(UTC).isoformat() if run_after else None,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    workspace = session.get(Workspace, workspace_id)
    authority = Job(
        workspace_id=workspace_id, requester_id=requester_id, privacy_epoch=workspace.privacy_epoch
    )
    if not _authority(session, authority):
        raise DomainError("authorization_changed", "Job creation is no longer permitted", 403)
    values = dict(
        id=uuid4(),
        workspace_id=workspace_id,
        requester_id=requester_id,
        command_key=command_key,
        kind=kind,
        payload=payload or {},
        target_id=target_id,
        payload_hash=digest,
        privacy_epoch=workspace.privacy_epoch,
        replay_safe=REGISTRY[kind][1],
        run_after=run_after or now(session),
        max_attempts=max_attempts,
    )
    session.execute(
        insert(Job).values(**values).on_conflict_do_nothing(constraint="uq_job_command")
    )
    job = session.scalar(
        select(Job).where(
            Job.workspace_id == workspace_id,
            Job.requester_id == requester_id,
            Job.command_key == command_key,
        )
    )
    if job.payload_hash != digest:
        raise DomainError("idempotency_conflict", "Command key was used with different input", 409)
    return job


def _finish_attempt(session, job, outcome, error=None):
    attempt = session.scalar(
        select(JobAttempt).where(
            JobAttempt.job_id == job.id, JobAttempt.lease_token == job.lease_token
        )
    )
    if attempt:
        attempt.finished_at, attempt.outcome, attempt.error_code = now(session), outcome, error


def _end(session, job, state, error=None):
    _finish_attempt(session, job, state, error)
    job.state, job.error_code = state, error
    job.lease_token = job.lease_expires_at = None


def recover_expired(session):
    jobs = session.scalars(
        select(Job)
        .where(Job.state == "running", Job.lease_expires_at <= now(session))
        .order_by(Job.lease_expires_at, Job.id)
        .limit(100)
        .with_for_update(skip_locked=True)
    ).all()
    for job in jobs:
        if not _authority(session, job):
            _end(session, job, "cancelled", "authorization_changed")
        elif not job.replay_safe:
            _end(session, job, "uncertain", "lease_expired")
        elif job.attempt_count >= job.max_attempts:
            _end(session, job, "failed", "attempts_exhausted")
        else:
            _end(session, job, "pending", "lease_expired")
            job.run_after = now(session) + timedelta(seconds=min(60, 2**job.attempt_count))
    session.flush()
    return len(jobs)


def claim(session, lease_seconds=30):
    recover_expired(session)
    # Bounded scan also prevents an invalid queue from holding the worker indefinitely.
    for _ in range(100):
        job = session.scalar(
            select(Job)
            .where(Job.state == "pending", Job.run_after <= now(session))
            .order_by(Job.run_after, Job.created_at, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        if not _authority(session, job):
            _end(session, job, "cancelled", "authorization_changed")
        elif job.kind not in REGISTRY:
            _end(session, job, "failed", "unknown_handler")
        elif job.attempt_count >= job.max_attempts:
            _end(session, job, "failed", "attempts_exhausted")
        else:
            job.state, job.error_code = "running", None
            job.attempt_count += 1
            job.lease_token = uuid4()
            job.lease_expires_at = now(session) + timedelta(seconds=lease_seconds)
            session.add(
                JobAttempt(job_id=job.id, number=job.attempt_count, lease_token=job.lease_token)
            )
            session.flush()
            return job
        session.flush()
    return None


def _fence(session, job_id, token):
    job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if (
        not job
        or job.state != "running"
        or job.lease_token != token
        or job.lease_expires_at <= now(session)
    ):
        return None
    if not _authority(session, job):
        _end(session, job, "cancelled", "authorization_changed")
        return None
    return job


def heartbeat(session, job_id, token, lease_seconds=30):
    job = _fence(session, job_id, token)
    if job is None:
        return False
    job.lease_expires_at = now(session) + timedelta(seconds=lease_seconds)
    return True


def complete(session, job_id, token, result, persist=None):
    job = _fence(session, job_id, token)
    if job is None:
        return False
    if result != {"status": "ok"}:
        raise DomainError("invalid_job_result", "Result must contain allowlisted metadata", 422)
    # Trusted caller callback for atomic DB effects; never invoke external effects here.
    if persist is not None:
        persist(session, job)
    job.result = result
    _end(session, job, "succeeded")
    return True


def fail(session, job_id, token, error_code="handler_error", retryable=False):
    job = _fence(session, job_id, token)
    if job is None:
        return False
    code = (
        error_code
        if error_code in {"handler_error", "handler_timeout", "worker_shutdown"}
        else "handler_error"
    )
    state = "uncertain" if not job.replay_safe else "failed"
    if job.replay_safe and retryable and job.attempt_count < job.max_attempts:
        state = "pending"
        job.run_after = now(session) + timedelta(seconds=min(60, 2**job.attempt_count))
    _end(session, job, state, code)
    return True


def get_job(session, workspace_id, user_id, job_id):
    member = require_workspace(session, user_id, workspace_id, "jobs.read")
    job = session.scalar(select(Job).where(Job.id == job_id, Job.workspace_id == workspace_id))
    if job is None or (member.role not in {"owner", "admin"} and job.requester_id != user_id):
        raise DomainError("job_not_found", "Job not found", 404)
    return job


def list_jobs(session, workspace_id, user_id, limit=50):
    member = require_workspace(session, user_id, workspace_id, "jobs.read")
    query = select(Job).where(Job.workspace_id == workspace_id)
    if member.role not in {"owner", "admin"}:
        query = query.where(Job.requester_id == user_id)
    return session.scalars(
        query.order_by(Job.created_at.desc(), Job.id).limit(min(limit, 100))
    ).all()


def cancel(session, *, workspace_id, user_id, job_id):
    job = get_job(session, workspace_id, user_id, job_id)
    job = session.scalar(
        select(Job)
        .where(Job.id == job.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job.state not in TERMINAL:
        _end(
            session,
            job,
            "uncertain" if job.state == "running" and not job.replay_safe else "cancelled",
            "cancelled_by_user",
        )
    return job
