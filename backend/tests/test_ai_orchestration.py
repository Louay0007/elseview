"""Bounded synthetic revision-2 planning and exact evidence validation."""

import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ai import adapter, analysis_inputs, profiles, service
from app.ai import orchestration as graph
from app.ai.schemas import EstimateBody, RunBody

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def enable_graphs(settings):
    settings.ai_orchestration_enabled = True


def candidate(settings, depth="standard", operation="themes"):
    body = EstimateBody(
        study_id=uuid4(),
        snapshot_id=uuid4(),
        operation=operation,
        depth=depth,
        profile_revision="2",
        right_snapshot_id=uuid4() if operation == "comparison_report" else None,
    )
    return graph.candidate(settings, SimpleNamespace(id=uuid4(), privacy_epoch=1), uuid4(), body)


@pytest.mark.parametrize("depth,calls", [("quick", 1), ("standard", 3), ("deep", 5)])
@pytest.mark.parametrize("text", ["échec observé ", "واجهة صعبة ", "3lech ma yekhdemch "])
def test_graph_utf8_bounds_and_original_spans(settings, monkeypatch, depth, calls, text):
    run = candidate(settings, depth)
    sources = {"a": text * 10000, "b": text * 10000}
    monkeypatch.setattr(analysis_inputs, "collect", lambda *args: (sources, {}, []))
    steps, _, _, _, coverage, estimate = graph.build_plan(None, settings, run)
    assert len(steps) == calls == estimate["planned_calls"]
    assert estimate["max_provider_calls"] == calls
    assert not estimate["reservation_created"] and not estimate["budget_checked"]
    assert "spans" not in estimate["coverage"]
    assert coverage["partial"]
    effective = profiles.execution_settings(settings, run.config)
    for step in steps:
        projection = step["reservation"]
        assert (
            projection["input_tokens_upper_bound"] + projection["max_output_tokens"]
            <= effective.llm_context_limit
        )
        if step["stage"] == "map":
            prompt = graph.prompt_for(run, sources, {}, step["membership"])
            assert adapter.estimate(effective, prompt) == Decimal(projection["reserved_cost"])
    assert graph.build_plan(None, settings, run)[-1] == estimate
    assert coverage["unique_source_chars"] <= coverage["source_chars_included_with_overlap"]


@pytest.mark.parametrize("operation", ["study_helper", "subgroup_insights", "translation"])
def test_revision_matrix_rejects_unsupported(operation):
    with pytest.raises(ValidationError):
        EstimateBody(
            study_id=uuid4(), snapshot_id=uuid4(), profile_revision="2", operation=operation
        )


def test_revision2_requires_confirmation_and_two_distinct_comparison_inputs():
    base = dict(study_id=uuid4(), snapshot_id=uuid4(), operation="themes", profile_revision="2")
    with pytest.raises(ValidationError):
        RunBody(**base, command_key="unconfirmed")
    with pytest.raises(ValidationError):
        EstimateBody(
            **(base | {"operation": "comparison_report", "right_snapshot_id": base["snapshot_id"]})
        )
    with pytest.raises(ValidationError):
        EstimateBody(
            **(
                base
                | {
                    "operation": "comparison_report",
                    "profile_revision": "1",
                    "right_snapshot_id": uuid4(),
                }
            )
        )


def test_default_hash_is_pre_revision2_contract():
    body = RunBody(study_id=uuid4(), operation="study_helper", command_key="legacy")
    assert service.request_identity(body) == adapter.digest(
        {
            "study_id": str(body.study_id),
            "snapshot_id": None,
            "operation": "study_helper",
            "instruction": "",
            "researcher_text_approved": False,
        }
    )


def test_comparison_unknown_metric_and_numeric_fields_rejected(settings):
    run = candidate(settings, operation="comparison_report")
    facts = {"suppressed": False, "references": {"known": {"difference": 0.1}}}
    body = {
        "findings": [{"text": "Synthetic finding", "metric_refs": ["known"]}],
        "limitations": ["Synthetic"],
        "insufficient_evidence": False,
    }
    assert graph.validated(run, json.dumps(body), {}, facts, {"metric_refs": ["known"]})[0] == body
    for changed in [
        body | {"difference": 999},
        body | {"findings": [{"text": "Invented", "metric_refs": ["unknown"]}]},
    ]:
        with pytest.raises(ValueError):
            graph.validated(run, json.dumps(changed), {}, facts, {"metric_refs": ["known"]})
    with pytest.raises(ValueError):
        graph.validated(
            run, json.dumps(body), {}, facts | {"suppressed": True}, {"metric_refs": ["known"]}
        )


def test_final_evidence_must_be_in_admitted_original_span(settings):
    run = candidate(settings)
    run.coverage = {"partial": True}
    body = {
        "findings": [{"text": "Synthetic", "evidence": [{"source_id": "a", "quote": "hidden"}]}],
        "limitations": ["Synthetic"],
        "insufficient_evidence": False,
    }
    with pytest.raises(ValueError, match="invented_quote"):
        graph.validated(
            run, json.dumps(body), {"a": "visible hidden"}, {}, {"spans": {"a": [[0, 7]]}}
        )


def test_suppressed_comparison_is_zero_calls(settings, monkeypatch):
    run = candidate(settings, operation="comparison_report")
    monkeypatch.setattr(
        analysis_inputs,
        "collect",
        lambda *args: (
            {},
            {"suppressed": True, "reason": "small_or_complementary_group", "references": {}},
            [],
        ),
    )
    steps, *_, estimate = graph.build_plan(None, settings, run)
    assert steps == [] and estimate["planned_calls"] == 0
    assert Decimal(estimate["reserved_cost"]) == 0


def test_comparison_collects_only_released_metrics_and_preserves_provenance(settings, monkeypatch):
    run = candidate(settings, operation="comparison_report")
    snapshot_ids = [sid for _, sid in run._input_ids]
    snapshots = {
        sid: SimpleNamespace(
            id=sid,
            study_id=run.study_id,
            definition_digest="definition",
            manifest_digest=str(sid),
            metrics={"metric_version": "p09.1"},
        )
        for sid in snapshot_ids
    }
    source = SimpleNamespace(
        exclusion_reason="included",
        session_id=uuid4(),
        revisions={"text": "RAW_TEXT_MUST_NOT_LOAD"},
    )
    row = SimpleNamespace(subject_id=uuid4(), version_id=uuid4())
    session = SimpleNamespace(
        get=lambda model, key: (
            row
            if model is analysis_inputs.CollectionSession
            else pytest.fail("Raw answer read for comparison")
        )
    )
    monkeypatch.setattr(
        analysis_inputs,
        "lock_workspace",
        lambda *args: SimpleNamespace(privacy_epoch=run.privacy_epoch),
    )
    permissions = []
    monkeypatch.setattr(analysis_inputs, "authorize", lambda *args: permissions.append(args[-1]))
    monkeypatch.setattr(analysis_inputs, "consent_granted", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        analysis_inputs.analytics,
        "access_snapshot",
        lambda session, wid, actor, sid, capability: (snapshots[sid], [source]),
    )
    monkeypatch.setattr(
        analysis_inputs.analytics,
        "compare",
        lambda *args: {
            "suppressed": False,
            "metric_version": "p09.1",
            "differences": {"blocks/task/time": 10, "blocks/task/missingness": 0},
        },
    )
    metric = {
        "numerator": 10,
        "denominator": 10,
        "value": 100,
        "aggregation": "median",
        "provenance": "self_report",
        "population": "completed_tasks",
        "sample_n": 10,
        "source_unit": "session",
        "unit": "ms",
        "exclusions": "redacted",
    }
    monkeypatch.setattr(
        analysis_inputs.analytics,
        "release_metrics",
        lambda *args: {
            "blocks": {
                "task": {
                    "time": metric,
                    "missingness": {
                        "numerator": 0,
                        "denominator": 10,
                        "value": 0,
                        "source_unit": "session",
                    },
                }
            }
        },
    )
    sources, facts, bindings = analysis_inputs.collect(session, run)
    assert sources == {} and len(bindings) == 2 and permissions == ["ai", "read"]
    reference = facts["references"]["metric-" + adapter.digest("blocks/task/time")[:24]]
    assert reference["left"]["provenance"] == "self_report" and reference["left"]["sample_n"] == 10
    assert reference["difference"] == 10
    prompt = graph.prompt_for(run, {}, facts, {"metric_refs": list(facts["references"])})
    assert "RAW_TEXT" not in json.dumps(prompt) and "source_id" not in json.dumps(prompt)
    run.config = run.config | {"facts_digest": adapter.digest({"old": "released history"})}
    from app.common.errors import DomainError

    with pytest.raises(DomainError, match="AI_INPUT_CHANGED"):
        analysis_inputs.collect(session, run)


def test_internal_gate_rejects_new_graphs(settings):
    settings.ai_orchestration_enabled = False
    from app.common.errors import DomainError

    with pytest.raises(DomainError, match="AI_REVISION_DISABLED"):
        candidate(settings)
