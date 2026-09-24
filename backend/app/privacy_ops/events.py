"""Identifier-only decisions replayed against a quarantined snapshot."""

from sqlalchemy import delete, select

from app.privacy_ops.models import RestoreEvent

ACTIONS = frozenset(
    {
        "session_withdraw",
        "session_delete",
        "asset_delete",
        "ai_delete",
        "snapshot_delete",
        "export_delete",
        "share_revoke",
        "consent_revoke",
        "dataset_delete",
        "study_delete",
        "recording_delete",
        "contact_delete",
        "candidate_delete",
        "comment_delete",
        "idempotency_scrub",
        "audit_scrub",
    }
)


def record_event(session, workspace_id, action, resource_id):
    if action not in ACTIONS:
        raise ValueError("Invalid event action")
    row = session.scalar(
        select(RestoreEvent).where(
            RestoreEvent.workspace_id == workspace_id,
            RestoreEvent.action == action,
            RestoreEvent.resource_id == resource_id,
        )
    )
    if row is None:
        row = RestoreEvent(workspace_id=workspace_id, action=action, resource_id=resource_id)
        session.add(row)
        session.flush()
    return row


def apply_event(session, workspace_id, action, resource_id, storage=None):
    if action in {
        "dataset_delete",
        "study_delete",
        "recording_delete",
        "contact_delete",
        "candidate_delete",
        "comment_delete",
        "idempotency_scrub",
        "audit_scrub",
    }:
        from app.privacy_ops.lifecycle import apply_lifecycle_event

        return apply_lifecycle_event(session, workspace_id, action, resource_id, storage=storage)
    if action == "consent_revoke":
        return apply_consent_event(session, workspace_id, action, resource_id)
    from app.ai.models import AIEvidence, AIRun
    from app.analytics.models import (
        AnalysisSnapshot,
        Export,
        ReportShare,
        ReportVersion,
        SnapshotSource,
    )
    from app.auth.security import utcnow
    from app.collection.models import (
        Answer,
        AnswerRevision,
        CollectionSession,
        InteractionAttempt,
        ResponseEvent,
    )
    from app.common.privacy_models import Asset
    from app.privacy_ops.service import held_asset, workspace_held

    models = dict(
        session_withdraw=CollectionSession,
        session_delete=CollectionSession,
        asset_delete=Asset,
        ai_delete=AIRun,
        snapshot_delete=AnalysisSnapshot,
        export_delete=Export,
        share_revoke=ReportShare,
    )
    model = models[action]
    row = session.scalar(
        select(model).where(model.workspace_id == workspace_id, model.id == resource_id)
    )
    if row is None:
        return
    if action not in {"session_withdraw", "share_revoke"} and (
        held_asset(session, row)
        if action == "asset_delete"
        else workspace_held(session, workspace_id)
    ):
        raise ValueError("Scoped deletion conflicts with current hold; reconcile before replay")
    if action == "session_withdraw":
        from app.collection.privacy import withdraw_session

        withdraw_session(session, row)
    elif action == "session_delete":
        from app.analytics.service import purge_sessions
        from app.reviews.privacy import purge_sessions as purge_reviews

        snapshots = select(SnapshotSource.snapshot_id).where(
            SnapshotSource.workspace_id == workspace_id, SnapshotSource.session_id == row.id
        )
        for run in session.scalars(
            select(AIRun).where(
                AIRun.workspace_id == workspace_id, AIRun.snapshot_id.in_(snapshots)
            )
        ).all():
            apply_event(session, workspace_id, "ai_delete", run.id)
            run.snapshot_id = None
        session.flush()
        purge_sessions(session, workspace_id, [row.id])
        purge_reviews(session, workspace_id, [row.id])
        row.state = "erased"
        session.flush()
        for child in (AnswerRevision, ResponseEvent, InteractionAttempt, Answer):
            session.execute(delete(child).where(child.session_id == row.id))
        row.assignments, row.submitted_snapshot = {}, None
        row.quality_summary, row.consent_receipt_id = None, None
    elif action == "ai_delete":
        from app.billing.service import release_ai_addon

        release_ai_addon(session, workspace_id, row.id)
        row.state, row.output, row.instruction, row.coverage = "invalidated", None, "", {}
        session.execute(delete(AIEvidence).where(AIEvidence.run_id == row.id))
    elif action == "snapshot_delete":
        for run in session.scalars(
            select(AIRun).where(AIRun.workspace_id == workspace_id, AIRun.snapshot_id == row.id)
        ).all():
            apply_event(session, workspace_id, "ai_delete", run.id)
            run.snapshot_id = None
        session.flush()
        versions = select(ReportVersion.id).where(
            ReportVersion.workspace_id == workspace_id, ReportVersion.snapshot_id == row.id
        )
        for child in (ReportShare, Export):
            session.execute(delete(child).where(child.report_version_id.in_(versions)))
        session.execute(delete(ReportVersion).where(ReportVersion.id.in_(versions)))
        session.execute(delete(SnapshotSource).where(SnapshotSource.snapshot_id == row.id))
        session.delete(row)
    elif action == "asset_delete":
        if storage is None:
            raise ValueError("Storage required for asset replay")
        storage.delete(row.storage_key)
        row.state = "purged"
    elif action == "export_delete":
        session.delete(row)
    elif action == "share_revoke":
        row.revoked_at = row.revoked_at or utcnow()
    session.flush()


def apply_consent_event(session, workspace_id, action, resource_id):
    from app.ai.service import invalidate_sessions
    from app.auth.security import utcnow
    from app.collection.models import CollectionSession
    from app.common.privacy_models import ConsentDocument, ConsentReceipt

    prior = session.scalar(
        select(ConsentReceipt).where(
            ConsentReceipt.workspace_id == workspace_id, ConsentReceipt.id == resource_id
        )
    )
    if prior is None:
        return
    doc = session.get(ConsentDocument, prior.document_id)
    subject_id, version_id = prior.subject_id, prior.study_version_id
    key = "restore:" + action + ":" + str(resource_id)
    if (
        session.scalar(
            select(ConsentReceipt.id).where(
                ConsentReceipt.workspace_id == workspace_id,
                ConsentReceipt.subject_id == subject_id,
                ConsentReceipt.receipt_key == key,
            )
        )
        is None
    ):
        session.add(
            ConsentReceipt(
                workspace_id=workspace_id,
                subject_id=subject_id,
                document_id=doc.id,
                study_version_id=version_id,
                presented_digest=doc.digest,
                receipt_key=key,
                decision="withdrawn",
                created_at=utcnow(),
            )
        )
    sessions = list(
        session.scalars(
            select(CollectionSession.id).where(
                CollectionSession.workspace_id == workspace_id,
                CollectionSession.subject_id == subject_id,
                *([CollectionSession.version_id == version_id] if version_id else []),
            )
        )
    )
    invalidate_sessions(session, workspace_id, sessions)
    if doc.purpose == "recording":
        from app.longitudinal.service import recording_revoke

        recording_revoke(session, workspace_id, subject_id, version_id)
        if version_id is None:
            from app.common.privacy_models import Asset

            for asset in session.scalars(
                select(Asset).where(
                    Asset.workspace_id == workspace_id,
                    Asset.owner_id == subject_id,
                    Asset.purpose == "recording",
                    Asset.state != "purged",
                )
            ):
                asset.state = "blocked"
    session.flush()
