"""All reads are privacy gates, including metadata, exports and anonymous shares.

Workspace locking serializes collection/review/privacy writes with the bounded freeze.
No raw response copies are retained in reports or exports.
"""

import json
import secrets
from collections import Counter
from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete, select

from app.auth.models import Membership, User
from app.auth.security import utcnow
from app.collection.models import AnswerRevision, CollectionSession
from app.common.errors import DomainError
from app.common.privacy import (
    consent_granted,
    get_scoped,
    lock_workspace,
    require_unrestricted,
    restricted,
)
from app.common.privacy_models import ConsentReceipt
from app.studies import methods
from app.studies.models import Study, StudyVersion
from app.studies.service import authorize, version_for

from .metrics import (
    MIN_GROUP,
    VERSION,
    compare_metrics,
    csv_document,
    digest,
    redacted_metrics,
    reduce_block,
)
from .models import AnalysisSnapshot, Export, Report, ReportShare, ReportVersion, SnapshotSource

MAX_SOURCES = 1000


def unavailable():
    raise DomainError("ANALYSIS_UNAVAILABLE", "Analysis is no longer available.", 409)


def decision_snapshot(session, workspace_id, session_id):
    from app.reviews.service import accepted_decision_snapshot

    value = accepted_decision_snapshot(session, workspace_id, session_id)
    if value is None:
        return None
    return {
        "decision_id": str(value["decision_id"]),
        "version": value["version"],
        "accepted_at": value["accepted_at"].isoformat()
        if hasattr(value["accepted_at"], "isoformat")
        else value["accepted_at"],
    }


def has_consent(session, row):
    receipt = (
        session.get(ConsentReceipt, row.consent_receipt_id) if row.consent_receipt_id else None
    )
    return bool(
        receipt
        and receipt.workspace_id == row.workspace_id
        and receipt.subject_id == row.subject_id
        and receipt.study_version_id == row.version_id
        and not restricted(session, row.workspace_id, row.subject_id)
        and consent_granted(
            session, row.workspace_id, row.subject_id, "study", receipt.document_id, row.version_id
        )
    )


def final_revisions(session, row):
    result, values = {}, {}
    for key, ref in sorted((row.submitted_snapshot or {}).items()):
        revision = session.scalar(
            select(AnswerRevision).where(
                AnswerRevision.session_id == row.id,
                AnswerRevision.answer_id == UUID(ref["answer_id"]),
                AnswerRevision.revision == ref["revision"],
            )
        )
        if revision is None:
            unavailable()
        result[key] = str(revision.id)
        values[key] = {"status": revision.status, "value": revision.value}
    return result, values


def source_digest(row, refs, values, decision):
    return digest(
        {
            "session": str(row.id),
            "version": str(row.version_id),
            "receipt": str(row.consent_receipt_id),
            "revisions": refs,
            "answers": values,
            "decision": decision,
        }
    )


def freeze(session, workspace_id, actor_id, study_id, version_id):
    workspace = lock_workspace(session, workspace_id)
    _, version = version_for(session, workspace_id, actor_id, study_id, version_id, "read")
    if version.state != "published":
        raise DomainError("PUBLISHED_REQUIRED", "Only published versions can be analyzed.", 409)
    rows = session.scalars(
        select(CollectionSession)
        .where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.version_id == version_id,
            CollectionSession.state.not_in(["withdrawn", "erased"]),
        )
        .order_by(CollectionSession.id)
        .limit(MAX_SOURCES + 1)
        .with_for_update()
    ).all()
    if len(rows) > MAX_SOURCES:
        raise DomainError(
            "SNAPSHOT_LIMIT", "Source population exceeds the bounded snapshot limit.", 422
        )
    # One locked manifest, with no repeated population pagination or moving cutoff.
    snapshot = AnalysisSnapshot(
        workspace_id=workspace_id,
        study_id=study_id,
        version_id=version_id,
        source_count=len(rows),
        consent_epoch=workspace.privacy_epoch,
        definition_digest=digest(version.blocks_json),
        manifest_digest="0" * 64,
        metrics={},
    )
    session.add(snapshot)
    session.flush()
    sources, included, excluded = [], [], Counter()
    for row in rows:
        reason, refs, values, decision = "included", {}, {}, None
        if row.state != "submitted":
            reason = "not_submitted"
        elif not has_consent(session, row):
            reason = "consent"
        else:
            decision = decision_snapshot(session, workspace_id, row.id)
            if decision is None:
                reason = "not_accepted"
            else:
                refs, values = final_revisions(session, row)
                included.append(values)
        if reason != "included":
            excluded[reason] += 1
        source = SnapshotSource(
            workspace_id=workspace_id,
            snapshot_id=snapshot.id,
            session_id=row.id,
            consent_receipt_id=row.consent_receipt_id,
            consent_epoch=workspace.privacy_epoch,
            decision=decision,
            revisions=refs,
            digest=source_digest(row, refs, values, decision),
            exclusion_reason=reason,
        )
        session.add(source)
        sources.append(source)
    blocks = [methods.parse_block(b) for b in version.blocks_json]
    snapshot.metrics = {
        "metric_version": VERSION,
        "source_unit": "session",
        "population_scope": "nonwithdrawn_sessions_of_exact_version_at_capture",
        "outside_population": ["withdrawn", "erased"],
        "exclusion_policy": "pinned_at_capture_never_promoted",
        "unit_note": "sessions_not_unique_people_across_versions",
        "included": len(included),
        "excluded": dict(excluded),
        "blocks": {
            b.block_key: reduce_block(
                b,
                [v.get(b.block_key, {"status": "missing", "value": None}) for v in included],
                dict(excluded),
            )
            for b in blocks
        },
        "sampling": "panel_sample_not_population_representative",
    }
    snapshot.manifest_digest = digest(
        [
            {"session": str(s.session_id), "digest": s.digest, "exclusion": s.exclusion_reason}
            for s in sources
        ]
    )
    session.flush()
    snapshot.state = "ready"
    session.flush()
    return snapshot


def validate_sources(session, workspace_id, snapshot_id):
    """Internal access gate; callers MUST separately enforce study authorization.

    Returns (snapshot, sources). Rechecks live collection state, consent, review
    identity/version and immutable revision digests on every invocation.
    """
    workspace = lock_workspace(session, workspace_id)
    if workspace.status != "active":
        unavailable()
    snapshot = get_scoped(session, AnalysisSnapshot, workspace_id, snapshot_id)
    if snapshot.state != "ready":
        unavailable()
    study = get_scoped(session, Study, workspace_id, snapshot.study_id)
    owner = get_scoped(session, Membership, workspace_id, study.owner_membership_id)
    user = session.get(User, owner.user_id)
    if owner.status != "active" or not user or user.status != "active" or not user.verified_at:
        unavailable()
    require_unrestricted(session, workspace_id, owner.user_id)
    version = get_scoped(session, StudyVersion, workspace_id, snapshot.version_id)
    if version.study_id != study.id or digest(version.blocks_json) != snapshot.definition_digest:
        unavailable()
    sources = session.scalars(
        select(SnapshotSource)
        .where(
            SnapshotSource.workspace_id == workspace_id, SnapshotSource.snapshot_id == snapshot.id
        )
        .order_by(SnapshotSource.session_id)
    ).all()
    if (
        len(sources) != snapshot.source_count
        or digest(
            [
                {"session": str(s.session_id), "digest": s.digest, "exclusion": s.exclusion_reason}
                for s in sources
            ]
        )
        != snapshot.manifest_digest
    ):
        unavailable()
    for source in sources:
        row = session.scalar(
            select(CollectionSession)
            .where(
                CollectionSession.workspace_id == workspace_id,
                CollectionSession.id == source.session_id,
            )
            .execution_options(populate_existing=True)
        )
        # Even excluded references cannot expose an erased/withdrawn participant.
        if (
            row is None
            or row.state in {"withdrawn", "erased"}
            or restricted(session, workspace_id, row.subject_id)
        ):
            unavailable()
        if source.exclusion_reason != "included":
            continue
        if (
            row.state != "submitted"
            or row.version_id != snapshot.version_id
            or row.consent_receipt_id != source.consent_receipt_id
            or not has_consent(session, row)
        ):
            unavailable()
        decision = decision_snapshot(session, workspace_id, row.id)
        if decision is None or decision != source.decision:
            unavailable()
        refs, values = final_revisions(session, row)
        if refs != source.revisions or source_digest(row, refs, values, decision) != source.digest:
            unavailable()
    return snapshot, sources


def access_snapshot(session, workspace_id, actor_id, snapshot_id, capability="read"):
    lock_workspace(session, workspace_id)
    snapshot = get_scoped(session, AnalysisSnapshot, workspace_id, snapshot_id)
    authorize(session, workspace_id, actor_id, snapshot.study_id, capability)
    return validate_sources(session, workspace_id, snapshot_id)


def release_suppressed(session, snapshot):
    """Conservative release gate across stored history, including invalidated facts.

    Not differential privacy: previously downloaded data cannot be recalled.
    Workspace lock is held by every caller's live-source gate.
    """
    peers = session.scalars(
        select(AnalysisSnapshot.id)
        .where(
            AnalysisSnapshot.workspace_id == snapshot.workspace_id,
            AnalysisSnapshot.study_id == snapshot.study_id,
            AnalysisSnapshot.definition_digest == snapshot.definition_digest,
            AnalysisSnapshot.id != snapshot.id,
        )
        .limit(1001)
    ).all()
    if len(peers) > 1000:
        return True  # bounded fail closed, never silently truncate release history
    populations = {}
    for source in session.scalars(
        select(SnapshotSource).where(
            SnapshotSource.workspace_id == snapshot.workspace_id,
            SnapshotSource.snapshot_id.in_([snapshot.id, *peers]),
            SnapshotSource.exclusion_reason == "included",
        )
    ):
        populations.setdefault(source.snapshot_id, set()).add(source.session_id)
    current = populations.get(snapshot.id, set())
    return any(
        current & other
        and any(0 < n < MIN_GROUP for n in (len(current - other), len(other - current)))
        for key, other in populations.items()
        if key != snapshot.id
    )


def release_metrics(session, snapshot):
    if release_suppressed(session, snapshot):
        return {
            "suppressed": True,
            "reason": "overlapping_release_history",
            "metric_version": VERSION,
            "source_unit": "session",
        }
    return redacted_metrics(snapshot.metrics)


def snapshot_view(session, workspace_id, actor_id, snapshot_id):
    snapshot, _ = access_snapshot(session, workspace_id, actor_id, snapshot_id)
    return {
        "id": str(snapshot.id),
        "version_id": str(snapshot.version_id),
        "manifest_digest": snapshot.manifest_digest,
        "metrics": release_metrics(session, snapshot),
    }


def source_access_summary(session, workspace_id, actor_id, snapshot_id):
    """Guarded raw-authorized manifest; never called by public shares."""
    snapshot, sources = access_snapshot(session, workspace_id, actor_id, snapshot_id, "raw")
    return {
        "snapshot_id": str(snapshot.id),
        "sources": [
            {
                "session_id": str(s.session_id),
                "revision_ids": s.revisions,
                "digest": s.digest,
                "consent_epoch": s.consent_epoch,
                "exclusion_reason": s.exclusion_reason,
                "decision": s.decision,
            }
            for s in sources
        ],
    }


def compare(session, workspace_id, actor_id, left_id, right_id):
    left, ls = access_snapshot(session, workspace_id, actor_id, left_id)
    right, rs = access_snapshot(session, workspace_id, actor_id, right_id)
    if (
        left.study_id != right.study_id
        or left.definition_digest != right.definition_digest
        or left.metrics["metric_version"] != right.metrics["metric_version"]
    ):
        raise DomainError(
            "INCOMPATIBLE_SNAPSHOTS", "Comparisons require identical measurement definitions.", 422
        )
    if release_suppressed(session, left) or release_suppressed(session, right):
        return {
            "suppressed": True,
            "reason": "overlapping_release_history",
            "metric_version": VERSION,
        }
    # Overlapping populations leak small additions/removals through differencing.
    lset = {s.session_id for s in ls if s.exclusion_reason == "included"}
    rset = {s.session_id for s in rs if s.exclusion_reason == "included"}
    if lset & rset and (len(lset - rset) < MIN_GROUP or len(rset - lset) < MIN_GROUP):
        return {
            "suppressed": True,
            "reason": "small_or_complementary_group",
            "metric_version": VERSION,
        }
    result = compare_metrics(left.metrics, right.metrics, len(lset), len(rset))
    # Do not publish differences for a hidden small/complementary metric cell.
    if not result["suppressed"]:
        safe = compare_metrics(
            redacted_metrics(left.metrics), redacted_metrics(right.metrics), len(lset), len(rset)
        )
        result["differences"] = safe["differences"]
    return result


def create_report(session, workspace_id, actor_id, snapshot_id):
    snapshot, _ = access_snapshot(session, workspace_id, actor_id, snapshot_id, "edit")
    report = Report(workspace_id=workspace_id, study_id=snapshot.study_id)
    session.add(report)
    session.flush()
    version = ReportVersion(
        workspace_id=workspace_id, report_id=report.id, snapshot_id=snapshot_id, number=1
    )
    session.add(version)
    session.flush()
    return report_view(session, workspace_id, actor_id, report.id)


def report_access(session, workspace_id, actor_id, report_id, capability="read", number=None):
    lock_workspace(session, workspace_id)
    report = get_scoped(session, Report, workspace_id, report_id)
    authorize(session, workspace_id, actor_id, report.study_id, capability)
    rv = session.scalar(
        select(ReportVersion).where(
            ReportVersion.workspace_id == workspace_id,
            ReportVersion.report_id == report.id,
            ReportVersion.number == (number or report.revision),
        )
    )
    if not rv or rv.state == "invalidated":
        unavailable()
    snapshot, sources = validate_sources(session, workspace_id, rv.snapshot_id)
    if snapshot.study_id != report.study_id:
        unavailable()
    return report, rv, snapshot, sources


def report_view(session, workspace_id, actor_id, report_id, number=None):
    report, rv, snapshot, _ = report_access(
        session, workspace_id, actor_id, report_id, number=number
    )
    return {
        "id": str(report.id),
        "version_id": str(rv.id),
        "revision": rv.number,
        "state": rv.state,
        "snapshot_id": str(snapshot.id),
        "metrics": release_metrics(session, snapshot),
    }


def approve(session, workspace_id, actor_id, report_id, expected_revision):
    report, rv, _, _ = report_access(session, workspace_id, actor_id, report_id, "publish")
    if report.revision != expected_revision or rv.state != "draft":
        raise DomainError(
            "REVISION_CONFLICT", "The report revision changed or is not a draft.", 409
        )
    rv.state, rv.approved_at = "approved", utcnow()
    session.flush()
    return report_view(session, workspace_id, actor_id, report_id)


def revise(session, workspace_id, actor_id, report_id, snapshot_id, expected_revision):
    # Allows replacement of an invalidated report with a fresh lawful snapshot.
    lock_workspace(session, workspace_id)
    report = get_scoped(session, Report, workspace_id, report_id)
    authorize(session, workspace_id, actor_id, report.study_id, "edit")
    snapshot, _ = access_snapshot(session, workspace_id, actor_id, snapshot_id, "edit")
    if report.revision != expected_revision or snapshot.study_id != report.study_id:
        raise DomainError("REVISION_CONFLICT", "Report revision or study does not match.", 409)
    report.revision += 1
    session.add(
        ReportVersion(
            workspace_id=workspace_id,
            report_id=report.id,
            snapshot_id=snapshot.id,
            number=report.revision,
        )
    )
    session.flush()
    return report_view(session, workspace_id, actor_id, report_id)


def safe_summary(snapshot):
    # Deliberately no labels, free text, source IDs, categorical rare cells, or quotes.
    # A public report is only a coarse approved availability summary.
    count = snapshot.metrics["included"]
    measures = []
    safe = redacted_metrics(snapshot.metrics)
    allowed = {"response", "missingness", "completion", "time_on_task", "timing_valid", "median"}
    for index, block in enumerate(safe.get("blocks", {}).values(), 1):
        if not isinstance(block, dict):
            continue
        projected = {}
        for name in sorted(allowed & block.keys()):
            item = block[name]
            if not isinstance(item, dict):
                continue
            if item.get("suppressed"):
                projected[name] = {"suppressed": True}
            else:
                projected[name] = {
                    key: item[key]
                    for key in ("numerator", "denominator", "value", "sample_n")
                    if key in item and (item[key] is None or type(item[key]) in (int, float))
                }
        measures.append({"measure_index": index, "metrics": projected})
    return {
        "metric_version": VERSION,
        "source_unit": "session",
        "sample_size_band": "suppressed"
        if count < MIN_GROUP
        else "5-19"
        if count < 20
        else "20-99"
        if count < 100
        else "100+",
        "sampling": "panel_sample_not_population_representative",
        "status": "approved",
        "measures": measures,
    }


def create_share(session, workspace_id, actor_id, report_id, ttl_seconds):
    _, rv, _, _ = report_access(session, workspace_id, actor_id, report_id, "publish")
    if rv.state != "approved" or not 60 <= ttl_seconds <= 2592000:
        raise DomainError(
            "INVALID_SHARE", "An approved report and bounded expiration are required.", 422
        )
    token = secrets.token_urlsafe(32)
    now = utcnow()
    share = ReportShare(
        workspace_id=workspace_id,
        report_version_id=rv.id,
        issuer_id=actor_id,
        token_hash=digest(token),
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    session.add(share)
    session.flush()
    return {"id": str(share.id), "token": token, "expires_at": share.expires_at.isoformat()}


def read_share(session, token):
    if not 40 <= len(token) <= 128:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    share = session.scalar(select(ReportShare).where(ReportShare.token_hash == digest(token)))
    if share is None:
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    lock_workspace(session, share.workspace_id)
    session.refresh(share)
    if share.revoked_at or share.expires_at <= utcnow():
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    rv = get_scoped(session, ReportVersion, share.workspace_id, share.report_version_id)
    if rv.state != "approved":
        raise DomainError("NOT_FOUND", "Resource not found.", 404)
    try:
        report = get_scoped(session, Report, share.workspace_id, rv.report_id)
        issuer = session.get(User, share.issuer_id)
        if not issuer or issuer.status != "active" or not issuer.verified_at:
            unavailable()
        authorize(session, share.workspace_id, share.issuer_id, report.study_id, "publish")
        snapshot, _ = validate_sources(session, share.workspace_id, rv.snapshot_id)
    except DomainError:
        raise DomainError("NOT_FOUND", "Resource not found.", 404) from None
    if release_suppressed(session, snapshot):
        return {
            "status": "approved",
            "suppressed": True,
            "metric_version": VERSION,
            "source_unit": "session",
        }
    return safe_summary(snapshot)


def revoke_share(session, workspace_id, actor_id, share_id):
    lock_workspace(session, workspace_id)
    share = get_scoped(session, ReportShare, workspace_id, share_id)
    rv = get_scoped(session, ReportVersion, workspace_id, share.report_version_id)
    report = get_scoped(session, Report, workspace_id, rv.report_id)
    authorize(session, workspace_id, actor_id, report.study_id, "publish")
    share.revoked_at = share.revoked_at or utcnow()
    session.flush()
    return {"revoked": True}


def create_export(session, workspace_id, actor_id, report_id, format, scope):
    _, rv, _, _ = report_access(session, workspace_id, actor_id, report_id, "export")
    if format not in {"json", "csv"} or scope not in {"raw", "summary"}:
        raise DomainError(
            "INVALID_EXPORT", "Only CSV and JSON summary/raw exports are supported.", 422
        )
    if scope == "raw":
        report_access(session, workspace_id, actor_id, report_id, "raw")
    item = Export(workspace_id=workspace_id, report_version_id=rv.id, format=format, scope=scope)
    session.add(item)
    session.flush()
    return {"id": str(item.id), "format": item.format, "scope": item.scope}


def download_export(session, workspace_id, actor_id, export_id):
    lock_workspace(session, workspace_id)
    item = get_scoped(session, Export, workspace_id, export_id)
    rv = get_scoped(session, ReportVersion, workspace_id, item.report_version_id)
    _, _, snapshot, sources = report_access(
        session, workspace_id, actor_id, rv.report_id, "export", rv.number
    )
    if item.state != "ready":
        unavailable()
    data = {"metric_version": VERSION, "metrics": release_metrics(session, snapshot)}
    if item.scope == "raw":
        authorize(session, workspace_id, actor_id, snapshot.study_id, "raw")
        data["metrics"] = snapshot.metrics
        data["responses"] = []
        for source in sources:
            if source.exclusion_reason == "included":
                row = get_scoped(session, CollectionSession, workspace_id, source.session_id)
                _, values = final_revisions(session, row)
                data["responses"].append({"source_id": str(source.id), "answers": values})
    return (
        json.dumps(data, ensure_ascii=False, allow_nan=False, sort_keys=True)
        if item.format == "json"
        else csv_document(data),
        "application/json" if item.format == "json" else "text/csv",
    )


def invalidate_session(session, workspace_id, session_id):
    """Lead calls in the same transaction before session withdrawal changes."""
    lock_workspace(session, workspace_id)
    ids = session.scalars(
        select(SnapshotSource.snapshot_id).where(
            SnapshotSource.workspace_id == workspace_id, SnapshotSource.session_id == session_id
        )
    ).all()
    for snapshot in session.scalars(
        select(AnalysisSnapshot).where(
            AnalysisSnapshot.workspace_id == workspace_id, AnalysisSnapshot.id.in_(ids)
        )
    ):
        snapshot.state = "invalidated"
    session.flush()
    versions = session.scalars(
        select(ReportVersion).where(
            ReportVersion.workspace_id == workspace_id, ReportVersion.snapshot_id.in_(ids)
        )
    ).all()
    vids = [v.id for v in versions]
    for rv in versions:
        rv.state = "invalidated"
    for item in session.scalars(
        select(Export).where(
            Export.workspace_id == workspace_id, Export.report_version_id.in_(vids)
        )
    ):
        item.state = "invalidated"
    for share in session.scalars(
        select(ReportShare).where(
            ReportShare.workspace_id == workspace_id, ReportShare.report_version_id.in_(vids)
        )
    ):
        share.revoked_at = share.revoked_at or utcnow()
    session.flush()
    return len(ids)


def purge_sessions(session, workspace_id, session_ids):
    """Remove all derived facts containing these sources, before source deletion.

    Entire overlapping snapshots are purged (never retained partially recomputed).
    Reports with any affected revision are removed together with all their versions.
    """
    lock_workspace(session, workspace_id)
    ids = set(
        session.scalars(
            select(SnapshotSource.snapshot_id).where(
                SnapshotSource.workspace_id == workspace_id,
                SnapshotSource.session_id.in_(session_ids),
            )
        ).all()
    )
    for sid in session_ids:
        invalidate_session(session, workspace_id, sid)
    report_ids = set(
        session.scalars(
            select(ReportVersion.report_id).where(
                ReportVersion.workspace_id == workspace_id, ReportVersion.snapshot_id.in_(ids)
            )
        ).all()
    )
    versions = session.scalars(
        select(ReportVersion).where(
            ReportVersion.workspace_id == workspace_id, ReportVersion.report_id.in_(report_ids)
        )
    ).all()
    vids = [v.id for v in versions]
    for model in (ReportShare, Export):
        session.execute(
            delete(model).where(
                model.workspace_id == workspace_id, model.report_version_id.in_(vids)
            )
        )
    session.execute(
        delete(ReportVersion).where(
            ReportVersion.workspace_id == workspace_id, ReportVersion.id.in_(vids)
        )
    )
    session.execute(
        delete(Report).where(Report.workspace_id == workspace_id, Report.id.in_(report_ids))
    )
    session.execute(
        delete(SnapshotSource).where(
            SnapshotSource.workspace_id == workspace_id, SnapshotSource.snapshot_id.in_(ids)
        )
    )
    session.execute(
        delete(AnalysisSnapshot).where(
            AnalysisSnapshot.workspace_id == workspace_id, AnalysisSnapshot.id.in_(ids)
        )
    )
    session.flush()
    return len(ids)


def purge_studies(session, workspace_id, study_ids):
    """Owner cleanup including empty snapshots. Call before deleting studies."""
    lock_workspace(session, workspace_id)
    snapshots = session.scalars(
        select(AnalysisSnapshot).where(
            AnalysisSnapshot.workspace_id == workspace_id, AnalysisSnapshot.study_id.in_(study_ids)
        )
    ).all()
    ids = [s.id for s in snapshots]
    for snapshot in snapshots:
        snapshot.state = "invalidated"
    session.flush()
    reports = session.scalars(
        select(Report.id).where(Report.workspace_id == workspace_id, Report.study_id.in_(study_ids))
    ).all()
    vids = session.scalars(
        select(ReportVersion.id).where(
            ReportVersion.workspace_id == workspace_id, ReportVersion.report_id.in_(reports)
        )
    ).all()
    for model in (ReportShare, Export):
        session.execute(
            delete(model).where(
                model.workspace_id == workspace_id, model.report_version_id.in_(vids)
            )
        )
    session.execute(
        delete(ReportVersion).where(
            ReportVersion.workspace_id == workspace_id, ReportVersion.report_id.in_(reports)
        )
    )
    session.execute(
        delete(Report).where(Report.workspace_id == workspace_id, Report.id.in_(reports))
    )
    session.execute(
        delete(SnapshotSource).where(
            SnapshotSource.workspace_id == workspace_id, SnapshotSource.snapshot_id.in_(ids)
        )
    )
    session.execute(
        delete(AnalysisSnapshot).where(
            AnalysisSnapshot.workspace_id == workspace_id, AnalysisSnapshot.id.in_(ids)
        )
    )
    session.flush()
    return len(ids)
