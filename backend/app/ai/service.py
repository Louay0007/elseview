"""Job -> workspace -> budget lock order. External I/O never holds a transaction.

Once dispatch is committed, every failure is conservatively charge-uncertain.
No retry can turn a read timeout into a second paid request.

Single backend process only: final authorization transfers the workspace gate
through HTTP request-body completion. Coordinated revocations either commit
before authorization (zero provider calls) or wait until sending has completed.
This orders application writes, not remote receipt: bytes already buffered in
the OS/network cannot be recalled, and remote processing may outlive revocation.
Direct SQL writers and multiple backend processes are outside this guarantee.
"""

import asyncio
from decimal import ROUND_UP, Decimal
from uuid import UUID

from openai import APIConnectionError, APIStatusError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.analytics import service as analytics
from app.auth.service import require_workspace
from app.collection.models import AnswerRevision, CollectionSession
from app.common.errors import DomainError
from app.common.privacy import consent_granted, get_scoped, lock_workspace
from app.jobs import service as jobs
from app.jobs.models import Job
from app.studies.service import authorize

from . import adapter
from .models import AIAttempt, AIEvidence, AIRun, UsageBudget


def denied(code="AI_UNAVAILABLE"):
    raise DomainError(code, "AI assistance is unavailable for this request.", 409)


def config(settings):
    return {
        key: str(getattr(settings, key))
        for key in type(settings).model_fields
        if key.startswith("llm_") and key != "llm_api_key"
    } | {
        "mode": settings.ai_mode,
        "prompt": adapter.PROMPT_VERSION,
        "schema": adapter.SCHEMA_VERSION,
    }


def context(session, run):
    workspace = lock_workspace(session, run.workspace_id)
    if workspace.privacy_epoch != run.privacy_epoch or run.state == "invalidated":
        denied()
    authorize(session, run.workspace_id, run.requester_id, run.study_id, "ai")
    sources, metrics = {}, {}
    if run.snapshot_id:
        snapshot, refs = analytics.access_snapshot(
            session, run.workspace_id, run.requester_id, run.snapshot_id, "ai"
        )
        if snapshot.study_id != run.study_id:
            denied()
        metrics = analytics.release_metrics(session, snapshot)
        for ref in refs:
            if ref.exclusion_reason != "included":
                continue
            row = session.get(CollectionSession, ref.session_id)
            if not consent_granted(
                session,
                run.workspace_id,
                row.subject_id,
                "ai_processing",
                study_version_id=row.version_id,
            ):
                denied("AI_CONSENT_REQUIRED")
            for revision_id in ref.revisions.values():
                revision = session.get(AnswerRevision, UUID(revision_id))
                # Only explicit textual values; never serialize demographics/identity/events.
                value = revision.value
                text = (
                    value
                    if isinstance(value, str)
                    else value.get("text", "")
                    if isinstance(value, dict)
                    else ""
                )
                if isinstance(text, str) and text:
                    sources[str(revision.id)] = text
    return sources, metrics


def budgets(session, run, day):
    # Workspace lock serializes reservation + all settlement. Stable study then daily.
    result = []
    for scope in (run.config["budget_study_scope"], f"daily:{day}"):
        session.execute(
            insert(UsageBudget)
            .values(
                workspace_id=run.workspace_id,
                scope=scope,
                currency=run.config["llm_currency"],
                reserved=0,
                spent=0,
            )
            .on_conflict_do_nothing(constraint="uq_ai_budget")
        )
        result.append(
            session.scalar(
                select(UsageBudget)
                .where(
                    UsageBudget.workspace_id == run.workspace_id,
                    UsageBudget.scope == scope,
                    UsageBudget.currency == run.config["llm_currency"],
                )
                .with_for_update()
            )
        )
    return result


def create(session, settings, workspace_id, actor_id, body):
    if settings.ai_mode == "disabled":
        denied("AI_DISABLED")
    workspace = lock_workspace(session, workspace_id)
    authorize(session, workspace_id, actor_id, body.study_id, "ai")
    request_hash = adapter.digest(body.model_dump(mode="json", exclude={"command_key"}))
    prior = session.scalar(
        select(AIRun).where(
            AIRun.workspace_id == workspace_id,
            AIRun.requester_id == actor_id,
            AIRun.command_key == body.command_key,
        )
    )
    if prior:
        if prior.request_hash != request_hash:
            denied("IDEMPOTENCY_CONFLICT")
        return view(session, workspace_id, actor_id, prior.id)
    if body.instruction and not body.researcher_text_approved:
        denied("AI_TEXT_APPROVAL_REQUIRED")
    if not body.snapshot_id and body.operation not in {
        "study_helper",
        "campaign_clarity",
        "translation",
    }:
        denied("AI_SNAPSHOT_REQUIRED")
    run = AIRun(
        workspace_id=workspace_id,
        study_id=body.study_id,
        snapshot_id=body.snapshot_id,
        requester_id=actor_id,
        command_key=body.command_key,
        request_hash=request_hash,
        operation=body.operation,
        instruction=adapter.redact(body.instruction),
        privacy_epoch=workspace.privacy_epoch,
        config=config(settings),
        cache_key="",
        state="queued",
    )
    run.config = run.config | {"budget_study_scope": f"study:{run.study_id}"}
    sources, metrics = context(session, run)
    parts, run.coverage = adapter.chunks(
        sources, max_chars=max(500, settings.llm_context_limit // 3)
    )
    prompt = adapter.messages(run.operation, run.instruction, parts, metrics)
    try:
        amount = adapter.estimate(settings, prompt)
    except ValueError:
        denied("AI_CONTEXT_LIMIT")
    run.cache_key = adapter.digest(
        {
            "workspace": str(workspace_id),
            "study": str(run.study_id),
            "snapshot": str(run.snapshot_id),
            "epoch": run.privacy_epoch,
            "config": run.config,
            "prompt": prompt,
        }
    )
    cached = session.scalar(
        select(AIRun)
        .where(
            AIRun.workspace_id == workspace_id,
            AIRun.requester_id == actor_id,
            AIRun.cache_key == run.cache_key,
            AIRun.state.in_(["draft", "approved"]),
        )
        .limit(1)
    )
    if cached:
        return view(session, workspace_id, actor_id, cached.id)
    unresolved = session.scalar(
        select(AIRun.id)
        .join(AIAttempt, AIAttempt.run_id == AIRun.id)
        .where(
            AIRun.workspace_id == workspace_id,
            AIRun.cache_key == run.cache_key,
            AIAttempt.state.in_(["reserved", "sent", "uncertain"]),
        )
        .limit(1)
    )
    if unresolved:
        denied("AI_PENDING_RECONCILIATION")
    previous = session.scalars(
        select(AIAttempt)
        .join(AIRun, AIRun.id == AIAttempt.run_id)
        .where(AIRun.workspace_id == workspace_id, AIRun.cache_key == run.cache_key)
        .order_by(AIAttempt.created_at.desc())
        .limit(2)
    ).all()
    if previous:
        last = previous[0]
        if (
            len(previous) >= 2
            or last.error_code
            not in {"never_dispatched", "connect_before_send", "provider_http_429"}
            or last.state != "released"
        ):
            denied("AI_RETRY_BLOCKED")
        delay = (last.usage or {}).get("retry_after_seconds", 60)
        if (jobs.now(session) - last.created_at).total_seconds() < delay:
            denied("AI_RETRY_AFTER")
    session.add(run)
    session.flush()
    from app.billing.service import reserve_ai_addon

    reserve_ai_addon(session, workspace_id, run.id)
    day = jobs.now(session).date().isoformat()
    for budget, ceiling in zip(
        budgets(session, run, day),
        (settings.llm_study_budget, settings.llm_workspace_daily_budget),
        strict=True,
    ):
        if budget.reserved + budget.spent + amount > ceiling:
            denied("AI_BUDGET_EXHAUSTED")
        budget.reserved += amount
    session.add(
        AIAttempt(
            workspace_id=workspace_id,
            run_id=run.id,
            state="reserved",
            reserved_cost=amount,
            budget_day=day,
        )
    )
    job = jobs.enqueue(
        session,
        workspace_id=workspace_id,
        requester_id=actor_id,
        command_key="ai:" + str(run.id),
        kind="ai.generate",
        target_id=run.id,
        max_attempts=1,
        internal=True,
    )
    run.job_id = job.id
    session.flush()
    return view(session, workspace_id, actor_id, run.id)


def authorize_job(session, job):
    try:
        run = get_scoped(session, AIRun, job.workspace_id, job.target_id)
        if run.requester_id != job.requester_id or run.job_id != job.id:
            return False
        context(session, run)
        return True
    except DomainError:
        return False


def attempt_for(session, run):
    return session.scalar(select(AIAttempt).where(AIAttempt.run_id == run.id).with_for_update())


def settle(session, run, attempt, amount):
    for budget in budgets(session, run, attempt.budget_day):
        budget.reserved -= attempt.reserved_cost
        budget.spent += amount
    attempt.actual_cost = amount
    attempt.state = "settled"


def fail_job(session, job, code=None):
    if job.kind != "ai.generate":
        return
    run = session.get(AIRun, job.target_id)
    if not run:
        return
    lock_workspace(session, run.workspace_id)
    from app.billing.service import release_ai_addon

    release_ai_addon(session, run.workspace_id, run.id)
    attempt = attempt_for(session, run)
    if attempt and attempt.state == "reserved":
        settle(session, run, attempt, Decimal(0))
        attempt.state = "released"
        # Only a durable reserved marker proves no dispatch was authorized.
        # One replacement command is allowed by create's existing attempt cap.
        attempt.error_code = "never_dispatched"
        attempt.usage = {"retry_after_seconds": 0}
    elif attempt and attempt.state == "sent":
        attempt.state = "uncertain"
    if run.state not in {"invalidated", "draft", "approved"}:
        run.state = "uncertain" if attempt and attempt.state == "uncertain" else "failed"


def prepare(session, settings, job, dispatch=True):
    current = jobs._fence(session, job.id, job.lease_token)
    if current is None:
        denied()
    run = session.get(AIRun, current.target_id)
    attempt = attempt_for(session, run)
    if attempt.budget_day != jobs.now(session).date().isoformat():
        denied("AI_RESERVATION_EXPIRED")
    if attempt.state != "reserved" or {
        k: v for k, v in run.config.items() if k != "budget_study_scope"
    } != config(settings):
        denied("AI_DISPATCH_BLOCKED")
    sources, metrics = context(session, run)
    parts, coverage = adapter.chunks(sources, max_chars=max(500, settings.llm_context_limit // 3))
    if coverage != run.coverage:
        denied()
    if dispatch:
        attempt.state, run.state = "sent", "running"
    return adapter.messages(run.operation, run.instruction, parts, metrics), sources, coverage


def finish(session, settings, job, content, usage, request_id, sources, coverage):
    current = jobs._fence(session, job.id, job.lease_token)
    if current is None:
        return False
    run = session.get(AIRun, current.target_id)
    attempt = attempt_for(session, run)
    if attempt.state != "sent":
        denied()
    context(session, run)
    attempt.request_id = (request_id or "")[:200]
    valid_usage = isinstance(usage, dict) and all(
        type(usage.get(k)) is int and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens")
    )
    if valid_usage:
        attempt.usage = {key: usage[key] for key in ("prompt_tokens", "completion_tokens")}
        cost = (
            Decimal(usage["prompt_tokens"]) * settings.llm_input_price_per_million
            + Decimal(usage["completion_tokens"]) * settings.llm_output_price_per_million
        ) / Decimal(1000000) + settings.llm_other_charge_reserve
        settle(session, run, attempt, cost.quantize(Decimal("0.00000001"), rounding=ROUND_UP))
        # Other provider billing categories are not silently treated as free.
        if settings.llm_other_charge_reserve > 0:
            attempt.error_code = "other_charges_conservative"
    else:
        attempt.state = "uncertain"
    try:
        output, evidence = adapter.validate_output(
            content, sources, coverage, require_evidence=run.snapshot_id is not None
        )
    except ValueError:
        run.state = "failed"
        attempt.error_code = "invalid_output"
        from app.billing.service import release_ai_addon

        release_ai_addon(session, run.workspace_id, run.id)
        return True
    run.output, run.state = output, "draft"
    from app.billing.service import consume_ai_addon

    consume_ai_addon(session, run.workspace_id, run.id)
    if run.operation in {"themes", "failure_clustering"}:
        run.output = output | {
            "source_counts": [
                len({e["source_id"] for e in finding["evidence"]}) for finding in output["findings"]
            ],
            "count_unit": "distinct_answer_revisions_per_finding",
        }
    for source_id, start, end, quote_hash in evidence:
        session.add(
            AIEvidence(
                workspace_id=run.workspace_id,
                run_id=run.id,
                source_id=source_id,
                start=start,
                end=end,
                quote_hash=quote_hash,
            )
        )
    return True


async def execute(database, settings, job):
    def transaction(fn, *args):
        with database.sessions.begin() as session:
            return fn(session, *args)

    # Build without authorizing send; revocation/cancellation may win before the
    # final transaction. Rebuild under its locks rather than trust stale sources.
    await asyncio.to_thread(transaction, prepare, settings, job, False)

    def authorize_dispatch():
        from app.common.dispatch_gate import transfer

        lease = None
        try:
            with database.sessions.begin() as session:
                prepared = prepare(session, settings, job)
                lease = transfer(session, job.workspace_id)
            return prepared, lease
        except BaseException:
            if lease is not None:
                lease.release()
            raise

    authorization = asyncio.create_task(asyncio.to_thread(authorize_dispatch))
    try:
        (prompt, sources, coverage), lease = await asyncio.shield(authorization)
    except BaseException:
        # Cancelling to_thread does not stop its transaction. Its eventual lease
        # must be released even when this coroutine has already gone away.
        def discard(task):
            if not task.cancelled():
                try:
                    _, pending_lease = task.result()
                except BaseException:
                    return
                pending_lease.release()

        authorization.add_done_callback(discard)
        raise
    if settings.ai_mode != "live":
        lease.release()  # No network bytes; never block mutations on fake I/O.
    token = adapter.dispatch_lease.set(lease)
    try:
        try:
            content, usage, request_id = await adapter.generate(settings, prompt)
        finally:
            # Includes failed connect, cancelled send, and provider cleanup.
            # No DB operation is allowed until this ownership ends.
            lease.release()
            adapter.dispatch_lease.reset(token)
    except (APIStatusError, APIConnectionError) as exc:
        # Header-only metadata, never persist/log provider message or echoed sources.
        failure = adapter.classify_failure(exc)
        request_id = (
            exc.response.headers.get("x-request-id", "") if isinstance(exc, APIStatusError) else ""
        )
        await asyncio.to_thread(transaction, record_error, job, failure, request_id)
        raise
    except BaseException:
        # Includes shutdown cancellation: durable sent marker already protects charge.
        raise
    await asyncio.to_thread(
        transaction, finish, settings, job, content, usage, request_id, sources, coverage
    )
    return {"status": "ok"}


def record_error(session, job, failure, request_id):
    current = jobs._fence(session, job.id, job.lease_token)
    if current is None:
        return
    run = session.get(AIRun, current.target_id)
    attempt = attempt_for(session, run)
    if failure.charge_uncertain:
        attempt.state = "uncertain"
    else:
        settle(session, run, attempt, Decimal(0))
        attempt.state = "released"
    attempt.error_code = failure.code
    attempt.request_id = request_id[:200] if request_id.isascii() else None
    attempt.usage = (
        {"retry_after_seconds": failure.retry_after} if failure.retry_after is not None else None
    )
    run.state = "uncertain" if failure.charge_uncertain else "failed"


def view(session, workspace_id, actor_id, run_id):
    run = get_scoped(session, AIRun, workspace_id, run_id)
    authorize(session, workspace_id, actor_id, run.study_id, "ai")
    context(session, run)
    attempt = attempt_for(session, run)
    return {
        "id": str(run.id),
        "job_id": str(run.job_id) if run.job_id else None,
        "operation": run.operation,
        "state": run.state,
        "draft": run.output,
        "coverage": run.coverage,
        "charge_state": attempt.state if attempt else None,
        "reserved_cost": str(attempt.reserved_cost) if attempt else None,
        "actual_cost": str(attempt.actual_cost)
        if attempt and attempt.actual_cost is not None
        else None,
        "currency": run.config["llm_currency"],
    }


def reconcile(session, workspace_id, actor_id, run_id, body):
    lock_workspace(session, workspace_id)
    require_workspace(session, actor_id, workspace_id, "privacy.manage")
    run = get_scoped(session, AIRun, workspace_id, run_id)
    attempt = attempt_for(session, run)
    if not attempt or attempt.state not in {"uncertain", "sent"}:
        denied("AI_RECONCILE_STATE")
    # Do not reconcile an active provider call; terminal jobs only.
    job = session.get(Job, run.job_id)
    if job.state not in jobs.TERMINAL:
        denied("AI_RECONCILE_STATE")
    settle(session, run, attempt, body.actual_cost)
    attempt.reconciliation = body.reference
    return {"state": "settled", "actual_cost": str(body.actual_cost)}


def _invalidate_runs(session, workspace_id, runs):
    from app.privacy_ops.models import LegalHold

    preserve = (
        session.scalar(
            select(LegalHold.id)
            .where(LegalHold.workspace_id == workspace_id, LegalHold.released_at.is_(None))
            .limit(1)
        )
        is not None
    )
    for run in runs:
        from app.billing.service import release_ai_addon

        release_ai_addon(session, workspace_id, run.id)
        if preserve:
            run.state = "invalidated"
            continue
        run.state, run.output, run.instruction = "invalidated", None, ""
        run.coverage = {}
        session.execute(delete(AIEvidence).where(AIEvidence.run_id == run.id))


def invalidate_subject(session, workspace_id, subject_id):
    # Erasure is conservative and also covers researcher-supplied free text.
    _invalidate_runs(
        session,
        workspace_id,
        session.scalars(select(AIRun).where(AIRun.workspace_id == workspace_id)),
    )


def invalidate_sessions(session, workspace_id, session_ids):
    from app.analytics.models import SnapshotSource

    if not session_ids:
        return
    affected = select(SnapshotSource.snapshot_id).where(
        SnapshotSource.workspace_id == workspace_id,
        SnapshotSource.session_id.in_(session_ids),
    )
    _invalidate_runs(
        session,
        workspace_id,
        session.scalars(
            select(AIRun).where(
                AIRun.workspace_id == workspace_id,
                AIRun.snapshot_id.in_(affected),
            )
        ),
    )
