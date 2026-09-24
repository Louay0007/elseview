"""Bounded depth regressions; no provider, database, or paid activation."""

import asyncio
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai import adapter, profiles, service
from app.ai.models import AIRun
from app.ai.schemas import EstimateBody, RunBody
from app.common.errors import DomainError

pytestmark = pytest.mark.unit


def test_standard_preserves_existing_limits(settings):
    profile = profiles.resolve(settings)
    assert profile["max_source_chars"] == max(500, settings.llm_context_limit // 3)
    assert profile["max_output_tokens"] == settings.llm_max_output_tokens
    assert profile["max_output_bytes"] == 100000
    assert profile["max_provider_calls"] == 1


def test_depths_are_bounded_and_distinct(settings):
    quick, standard, deep = [profiles.resolve(settings, d) for d in ("quick", "standard", "deep")]
    assert quick["max_source_chars"] < standard["max_source_chars"] < deep["max_source_chars"]
    assert quick["max_output_tokens"] < standard["max_output_tokens"] == deep["max_output_tokens"]
    assert len({adapter.digest(p) for p in (quick, standard, deep)}) == 3
    assert all(
        p["execution"] == "single_call" and p["revision"] == "1" for p in (quick, standard, deep)
    )


def test_pinned_settings_and_legacy_fallback(settings):
    config = service.config(settings)
    original = profiles.effective(config)
    config["depth_profile"] = profiles.resolve(settings, "quick")
    settings.llm_max_output_tokens = 7000
    settings.llm_input_price_per_million = Decimal("99")
    effective = profiles.execution_settings(settings, config)
    assert effective.llm_max_output_tokens == original["max_output_tokens"] // 2
    assert effective.llm_input_price_per_million == Decimal(config["llm_input_price_per_million"])
    del config["depth_profile"]
    assert profiles.effective(config) == original
    assert original["revision"] == "legacy"


def body(depth="standard", **updates):
    return RunBody(
        study_id=uuid4(), operation="study_helper", command_key="depth", depth=depth, **updates
    )


def run_for(settings, request=None):
    return service.candidate(
        settings, SimpleNamespace(id=uuid4(), privacy_epoch=1), uuid4(), request or body()
    )


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
def test_plan_uses_actual_bounds_and_cost(settings, monkeypatch, depth):
    settings.llm_input_price_per_million = Decimal("1.25")
    settings.llm_output_price_per_million = Decimal("2.5")
    settings.llm_other_charge_reserve = Decimal("0.01")
    sources = {"a": "a" * 12000, "b": "b" * 12000}
    monkeypatch.setattr(service, "context", lambda *args: (sources, {}))
    run = run_for(settings, body(depth))
    prompt, _, coverage, estimate = service.plan(None, settings, run)
    effective = profiles.execution_settings(settings, run.config)
    profile = run.config["depth_profile"]
    assert Decimal(estimate["reserved_cost"]) == adapter.estimate(effective, prompt)
    assert (
        estimate["input_tokens_upper_bound"]
        == len(json.dumps(prompt, ensure_ascii=False).encode()) + 512
    )
    assert estimate["max_output_tokens"] == profile["max_output_tokens"]
    assert estimate["chunks_included"] <= profile["max_chunks"]
    assert estimate["source_chars_included_with_overlap"] <= profile["max_source_chars"]
    assert coverage["partial"] and estimate["coverage"]["partial"]
    assert "spans" not in estimate["coverage"]
    if depth == "standard":
        parts, old_coverage = adapter.chunks(
            sources, max_chars=max(500, settings.llm_context_limit // 3)
        )
        assert prompt == adapter.messages(run.operation, run.instruction, parts, {})
        assert coverage == old_coverage
        assert Decimal(estimate["reserved_cost"]) == adapter.estimate(settings, prompt)


def test_default_request_and_legacy_cache_identity(settings, monkeypatch):
    request = body()
    legacy = request.model_dump(mode="json", exclude={"command_key", "depth"})
    assert service.request_identity(request) == adapter.digest(legacy)
    assert service.request_identity(request) != service.request_identity(
        request.model_copy(update={"depth": "quick"})
    )
    run = run_for(settings, request)
    monkeypatch.setattr(service, "context", lambda *args: ({}, {}))
    prompt, *_ = service.plan(None, settings, run)
    cache_key = service.cache_identity(run, prompt)
    legacy_key = service.cache_identity(run, prompt, legacy=True)
    assert cache_key != legacy_key
    run.config["depth_profile"]["revision"] = "2"
    assert service.cache_identity(run, prompt) != cache_key
    del run.config["depth_profile"]
    assert service.cache_identity(run, prompt) == legacy_key


@pytest.mark.parametrize("invalid", ["unlimited", "DEEP", None, 1])
def test_invalid_depth_rejected(invalid):
    with pytest.raises(ValidationError):
        body(invalid)


def test_estimate_read_only_and_authorized(settings, monkeypatch):
    calls = []
    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: calls.append(args[-1]))
    # No methods means any job, ledger, budget, run write, or provider access fails.
    result = service.estimate(object(), settings, workspace.id, uuid4(), body("quick"))
    assert calls == ["ai", "ai"]
    assert not result["reservation_created"] and not result["budget_checked"]
    assert result["depth_profile"]["name"] == "quick"
    assert "instruction" not in result


@pytest.mark.parametrize("code", ["AI_CONSENT_REQUIRED", "AI_UNAVAILABLE", "FORBIDDEN"])
def test_estimate_preserves_context_gates(settings, monkeypatch, code):
    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: None)

    def reject(*args):
        raise DomainError(code, "blocked", 409)

    monkeypatch.setattr(service, "context", reject)
    with pytest.raises(DomainError) as error:
        service.estimate(object(), settings, workspace.id, uuid4(), body())
    assert error.value.code == code


@pytest.mark.parametrize(
    "updates,code",
    [
        ({"instruction": "unapproved"}, "AI_TEXT_APPROVAL_REQUIRED"),
        ({"operation": "themes"}, "AI_SNAPSHOT_REQUIRED"),
    ],
)
def test_estimate_preserves_request_gates(settings, updates, code):
    candidate = body().model_copy(update=updates)
    with pytest.raises(DomainError) as error:
        service.estimate(object(), settings, uuid4(), uuid4(), candidate)
    assert error.value.code == code


@pytest.mark.parametrize("legacy", [False, True])
def test_prepare_pins_profile_and_preserves_dispatch_fence(settings, monkeypatch, legacy):
    run = run_for(settings, body("quick"))
    if legacy:
        del run.config["depth_profile"]
    monkeypatch.setattr(service, "context", lambda *args: ({"a": "x" * 4000}, {}))
    _, _, run.coverage, estimate = service.plan(None, settings, run)
    attempt = SimpleNamespace(
        state="reserved", budget_day="2026-09-24", reserved_cost=Decimal(estimate["reserved_cost"])
    )
    job = SimpleNamespace(id=uuid4(), lease_token=uuid4(), target_id=uuid4())
    monkeypatch.setattr(service.jobs, "_fence", lambda *args: job)
    monkeypatch.setattr(service.jobs, "now", lambda *args: datetime(2026, 9, 24, tzinfo=UTC))
    monkeypatch.setattr(service, "attempt_for", lambda *args: attempt)
    session = SimpleNamespace(get=lambda *args: run)
    if not legacy:
        monkeypatch.setattr(
            profiles, "resolve", lambda *args: pytest.fail("must use pinned profile")
        )
    _, _, _, effective = service.prepare(
        session, settings, job, dispatch=False, include_settings=True
    )
    assert effective.llm_max_output_tokens == profiles.effective(run.config)["max_output_tokens"]
    assert attempt.state == "reserved"
    settings.llm_max_output_tokens += 1
    with pytest.raises(DomainError) as error:
        service.prepare(session, settings, job)
    assert error.value.code == "AI_DISPATCH_BLOCKED"
    assert attempt.state == "reserved"


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("usage", [{"prompt_tokens": 10, "completion_tokens": 20}, None])
def test_finish_uses_pinned_price_output_and_unknown_charge(settings, monkeypatch, legacy, usage):
    from app.billing import service as billing

    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("2")
    run = run_for(settings, body("quick"))
    run.id = uuid4()
    if legacy:
        del run.config["depth_profile"]
    attempt = SimpleNamespace(state="sent")
    job = SimpleNamespace(id=uuid4(), lease_token=uuid4(), target_id=run.id)
    monkeypatch.setattr(service.jobs, "_fence", lambda *args: job)
    monkeypatch.setattr(service, "attempt_for", lambda *args: attempt)
    monkeypatch.setattr(service, "context", lambda *args: ({}, {}))
    monkeypatch.setattr(billing, "consume_ai_addon", lambda *args: None)
    charges = []
    monkeypatch.setattr(service, "settle", lambda *args: charges.append(args[-1]))
    seen = []
    original = adapter.validate_output

    def validate(*args, **kwargs):
        seen.append(kwargs["max_output_bytes"])
        return original(*args, **kwargs)

    monkeypatch.setattr(adapter, "validate_output", validate)
    settings.llm_input_price_per_million = Decimal("99")
    settings.llm_output_price_per_million = Decimal("99")
    settings.llm_other_charge_reserve = Decimal("99")
    content = json.dumps(
        {"findings": [], "limitations": ["Synthetic"], "insufficient_evidence": True}
    )
    assert service.finish(
        SimpleNamespace(get=lambda *args: run),
        settings,
        job,
        content,
        usage,
        "mock",
        {},
        {"partial": False},
    )
    assert seen == [100000 if legacy else 50000]
    assert charges == ([Decimal("0.00005000")] if usage else [])
    if usage is None:
        assert attempt.state == "uncertain"


def test_execute_passes_pinned_limits_to_generate(settings, monkeypatch):
    from app.common import dispatch_gate

    effective = settings.model_copy(update={"llm_max_output_tokens": 123})

    @contextmanager
    def begin():
        yield object()

    def prepare(*args, **kwargs):
        return ([], {}, {}, effective) if kwargs.get("include_settings") else ([], {}, {})

    monkeypatch.setattr(service, "prepare", prepare)
    monkeypatch.setattr(service, "finish", lambda *args: True)
    monkeypatch.setattr(
        dispatch_gate, "transfer", lambda *args: SimpleNamespace(release=lambda: None)
    )
    seen = []

    async def generate(config, prompt):
        seen.append(config.llm_max_output_tokens)
        return "{}", {}, "mock"

    monkeypatch.setattr(adapter, "generate", generate)
    assert asyncio.run(
        service.execute(
            SimpleNamespace(sessions=SimpleNamespace(begin=begin)),
            settings,
            SimpleNamespace(workspace_id=uuid4()),
        )
    ) == {"status": "ok"}
    assert seen == [123]


def test_output_byte_ceiling_enforced():
    content = json.dumps(
        {"findings": [], "limitations": ["é" * 100], "insufficient_evidence": True},
        ensure_ascii=False,
    )
    with pytest.raises(ValueError, match="invalid_output"):
        adapter.validate_output(content, {}, {"partial": False}, max_output_bytes=100)


@pytest.mark.parametrize("depth", ["quick", "standard", "deep"])
@pytest.mark.parametrize("exhausted", [False, True])
def test_creation_reserves_exact_estimate_and_persists_profile(
    settings, monkeypatch, depth, exhausted
):
    from app.billing import service as billing

    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("2")
    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: None)
    request = body(depth)
    estimate = service.estimate(
        object(),
        settings,
        workspace.id,
        uuid4(),
        EstimateBody(**request.model_dump(exclude={"command_key"})),
    )
    rows = []

    class Session:
        def scalar(self, query):
            return None

        def scalars(self, query):
            return SimpleNamespace(all=lambda: [])

        def add(self, row):
            rows.append(row)

        def flush(self):
            for row in rows:
                if row.id is None:
                    row.id = uuid4()

    budgets = [SimpleNamespace(reserved=Decimal(0), spent=Decimal(0)) for _ in range(2)]
    monkeypatch.setattr(service, "budgets", lambda *args: budgets)
    monkeypatch.setattr(service.jobs, "now", lambda *args: datetime(2026, 9, 24, tzinfo=UTC))
    queued = []

    def enqueue(*args, **kwargs):
        queued.append(kwargs)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(service.jobs, "enqueue", enqueue)
    addons = []
    monkeypatch.setattr(billing, "reserve_ai_addon", lambda *args: addons.append(args[-1]))
    monkeypatch.setattr(service, "view", lambda *args: rows[0])
    if exhausted:
        settings.llm_study_budget = Decimal("0.00000001")
        with pytest.raises(DomainError) as error:
            service.create(Session(), settings, workspace.id, uuid4(), request)
        assert error.value.code == "AI_BUDGET_EXHAUSTED"
        assert not queued and all(b.reserved == 0 for b in budgets)
        return
    run = service.create(Session(), settings, workspace.id, uuid4(), request)
    assert isinstance(run, AIRun)
    assert run.config["depth_profile"] == estimate["depth_profile"]
    assert all(b.reserved == Decimal(estimate["reserved_cost"]) for b in budgets)
    assert rows[1].reserved_cost == Decimal(estimate["reserved_cost"])
    assert queued[0]["max_attempts"] == 1 and addons == [run.id]


@pytest.mark.parametrize("legacy", [False, True])
def test_approved_cache_reuse_never_reserves_or_enqueues(settings, monkeypatch, legacy):
    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    actor, request = uuid4(), body()
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: None)
    cached = service.candidate(settings, workspace, actor, request)
    prompt, *_ = service.plan(object(), settings, cached)
    cached.id = uuid4()
    cached.cache_key = service.cache_identity(cached, prompt, legacy=legacy)
    if legacy:
        del cached.config["depth_profile"]
    results = iter([None, cached])
    queries = []

    def scalar(query):
        queries.append(query)
        return next(results)

    monkeypatch.setattr(service, "view", lambda *args: cached.id)
    assert (
        service.create(SimpleNamespace(scalar=scalar), settings, workspace.id, actor, request)
        == cached.id
    )
    cache_keys = next(
        value for key, value in queries[-1].compile().params.items() if key.startswith("cache_key")
    )
    assert cached.cache_key in cache_keys


@pytest.mark.parametrize(
    "error_code,state,expected",
    [
        ("never_dispatched", "released", "AI_RETRY_AFTER"),
        ("provider_outcome_unknown", "uncertain", "AI_RETRY_BLOCKED"),
    ],
)
def test_replacement_retry_fences_remain(settings, monkeypatch, error_code, state, expected):
    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: None)
    now = datetime(2026, 9, 24, tzinfo=UTC)
    monkeypatch.setattr(service.jobs, "now", lambda *args: now)
    attempt = SimpleNamespace(
        error_code=error_code, state=state, usage={"retry_after_seconds": 60}, created_at=now
    )
    session = SimpleNamespace(
        scalar=lambda *args: None, scalars=lambda *args: SimpleNamespace(all=lambda: [attempt])
    )
    with pytest.raises(DomainError) as error:
        service.create(session, settings, workspace.id, uuid4(), body("deep"))
    assert error.value.code == expected


def test_legacy_uncertain_cache_is_fenced_without_writes(settings, monkeypatch):
    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    actor = uuid4()
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: None)
    queries = []
    results = iter([None, None, uuid4()])

    def scalar(query):
        queries.append(query)
        return next(results)

    with pytest.raises(DomainError) as error:
        service.create(SimpleNamespace(scalar=scalar), settings, workspace.id, actor, body())
    assert error.value.code == "AI_PENDING_RECONCILIATION"
    params = queries[-1].compile().params
    assert ["reserved", "sent", "uncertain"] in params.values()
    cache_keys = next(value for key, value in params.items() if key.startswith("cache_key"))
    assert len(cache_keys) == 2


def test_estimate_route_is_read_only_no_store(settings, monkeypatch):
    from app.ai import router

    workspace = SimpleNamespace(id=uuid4(), privacy_epoch=1)
    monkeypatch.setattr(service, "lock_workspace", lambda *args: workspace)
    monkeypatch.setattr(service, "authorize", lambda *args: None)
    monkeypatch.setattr(router, "rate_limit", lambda *args: None)

    @contextmanager
    def begin():
        yield object()

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                settings=settings, database=SimpleNamespace(sessions=SimpleNamespace(begin=begin))
            )
        )
    )
    response = SimpleNamespace(headers={})
    result = router.estimate(workspace.id, body(), request, response, SimpleNamespace(id=uuid4()))
    assert response.headers["Cache-Control"] == "no-store"
    assert not result["reservation_created"]


def test_non_ascii_context_limit_is_not_hidden(settings, monkeypatch):
    monkeypatch.setattr(service, "context", lambda *args: ({"a": "界" * 50000}, {}))
    with pytest.raises(DomainError) as error:
        service.plan(None, settings, run_for(settings, body("deep")))
    assert error.value.code == "AI_CONTEXT_LIMIT"
