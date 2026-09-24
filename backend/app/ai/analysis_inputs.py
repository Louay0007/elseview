"""Current, consented inputs; comparison facts contain released aggregates only."""

from uuid import UUID

from sqlalchemy import select

from app.analytics import service as analytics
from app.collection.models import AnswerRevision, CollectionSession
from app.common.privacy import consent_granted, lock_workspace
from app.studies.service import authorize

from . import adapter
from .models import AIRunInput


def collect(session, run, reader=None):
    from .service import denied

    workspace = lock_workspace(session, run.workspace_id)
    if workspace.privacy_epoch != run.privacy_epoch or run.state == "invalidated":
        denied()
    comparison = run.operation == "comparison_report"
    for actor in {run.requester_id, reader or run.requester_id}:
        authorize(session, run.workspace_id, actor, run.study_id, "ai")
        authorize(session, run.workspace_id, actor, run.study_id, "read" if comparison else "raw")
    inputs = getattr(run, "_input_ids", None)
    pinned = {}
    if inputs is None:
        rows = session.scalars(
            select(AIRunInput).where(AIRunInput.run_id == run.id).order_by(AIRunInput.role)
        ).all()
        inputs = [(row.role, row.snapshot_id) for row in rows]
        pinned = {row.role: row.binding for row in rows}
    if len(inputs) != (2 if comparison else 1):
        denied()
    sources, bindings, snapshots = {}, [], []
    for role, snapshot_id in inputs:
        snapshot, refs = analytics.access_snapshot(
            session, run.workspace_id, run.requester_id, snapshot_id, "ai"
        )
        if snapshot.study_id != run.study_id:
            denied()
        binding = {
            "definition": snapshot.definition_digest,
            "manifest": snapshot.manifest_digest,
            "metric_version": snapshot.metrics["metric_version"],
            "epoch": run.privacy_epoch,
        }
        if pinned and pinned.get(role) != binding:
            denied()
        bindings.append({"role": role, "snapshot_id": str(snapshot_id), "binding": binding})
        snapshots.append(snapshot)
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
            if comparison:
                continue
            for revision_id in ref.revisions.values():
                revision = session.get(AnswerRevision, UUID(revision_id))
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
    facts = {}
    if comparison:
        left, right = snapshots
        compared = analytics.compare(session, run.workspace_id, run.requester_id, left.id, right.id)
        facts = {
            "suppressed": compared["suppressed"],
            "metric_version": compared["metric_version"],
            "interpretation": "descriptive_only_not_causal",
            "references": {},
        }
        if compared["suppressed"]:
            facts["reason"] = compared["reason"]
        else:
            released = [analytics.release_metrics(session, snapshot) for snapshot in snapshots]

            def at(value, path):
                for key in path.split("/"):
                    value = value[key]
                return value

            for path, difference in sorted(compared["differences"].items()):
                a, b = [at(value, path) for value in released]
                if a.get("suppressed") or b.get("suppressed"):
                    continue

                # Reducer values only; never labels, free text, session or revision IDs.
                def measure(value):
                    return {
                        key: value[key]
                        for key in (
                            "numerator",
                            "denominator",
                            "value",
                            "missing",
                            "metric_version",
                            "source_unit",
                            "aggregation",
                            "sample_n",
                            "provenance",
                            "population",
                            "unit",
                            "exclusions",
                        )
                        if key in value
                    }

                reference = "metric-" + adapter.digest(path)[:24]
                facts["references"][reference] = {
                    "path": path,
                    "left": measure(a),
                    "right": measure(b),
                    "difference": difference,
                    "measurement_definition": left.definition_digest,
                }
    if run.config.get("facts_digest") and run.config["facts_digest"] != adapter.digest(facts):
        denied("AI_INPUT_CHANGED")
    return sources, facts, bindings
