from sqlalchemy import select

from app.auth.security import utcnow
from app.privacy_ops.models import LegalHold, Tombstone


def workspace_held(session, workspace_id):
    """Shared snapshots/comments/studies cannot safely be split by subject."""
    return (
        session.scalar(
            select(LegalHold.id)
            .where(LegalHold.workspace_id == workspace_id, LegalHold.released_at.is_(None))
            .limit(1)
        )
        is not None
    )


def held(session, workspace_id, subject_id):
    # A missed review is an operational alert, NEVER an automatic release.
    return (
        session.scalar(
            select(LegalHold.id).where(
                LegalHold.workspace_id == workspace_id,
                LegalHold.subject_id == subject_id,
                LegalHold.released_at.is_(None),
            )
        )
        is not None
    )


def tombstone(session, workspace_id, subject_id, purpose):
    row = session.scalar(
        select(Tombstone).where(
            Tombstone.workspace_id == workspace_id,
            Tombstone.subject_id == subject_id,
            Tombstone.purpose == purpose,
        )
    )
    if row is None:
        row = Tombstone(workspace_id=workspace_id, subject_id=subject_id, purpose=purpose)
        session.add(row)
        session.flush()
    return row


def invalidate_subject_safely(session, workspace_id, subject_id):
    if not held(session, workspace_id, subject_id):
        from app.ai.service import invalidate_subject

        invalidate_subject(session, workspace_id, subject_id)
        return
    from app.ai.models import AIRun
    from app.analytics.service import invalidate_session
    from app.collection.models import CollectionSession

    for run in session.scalars(select(AIRun).where(AIRun.workspace_id == workspace_id)):
        run.state = "invalidated"  # raw output retained offline under hold
    for row in session.scalars(
        select(CollectionSession).where(
            CollectionSession.workspace_id == workspace_id,
            CollectionSession.subject_id == subject_id,
        )
    ):
        invalidate_session(session, workspace_id, row.id)


def retention_expired(session, workspace_id, asset):
    """Only an explicitly reviewed, unexpired policy can shorten asset retention."""
    purpose = "media" if asset.media_type.startswith(("audio/", "image/")) else "raw"
    cutoff = reviewed_cutoff(session, workspace_id, purpose)
    return cutoff is not None and asset.created_at <= cutoff


def reviewed_cutoff(session, workspace_id, purpose):
    """Never fall back to an older review when the latest decision is overdue."""
    from datetime import timedelta

    from app.privacy_ops.models import ReviewedRetention

    policy = session.scalar(
        select(ReviewedRetention)
        .where(
            ReviewedRetention.workspace_id == workspace_id,
            ReviewedRetention.purpose == purpose,
        )
        .order_by(ReviewedRetention.version.desc())
        .limit(1)
    )
    if policy is None or policy.review_deadline <= utcnow():
        return None
    return utcnow() - timedelta(days=policy.days)


def sweep_producers(session, workspace_id, limit=100):
    """Caller owns workspace lock. Bounded, producer-local deletion, no account erasure.

    Shared derivatives cannot be attributed perfectly; any active workspace hold
    defers this sweep rather than destroying another held subject's source.
    """

    from app.ai.models import AIEvidence, AIRun
    from app.analytics.models import (
        AnalysisSnapshot,
        Export,
        ReportShare,
    )
    from app.collection.models import (
        CollectionSession,
    )
    from app.common.privacy import lock_workspace

    workspace = lock_workspace(session, workspace_id)
    counts = {"raw": 0, "derived": 0, "export": 0}
    if session.scalar(
        select(LegalHold.id)
        .where(LegalHold.workspace_id == workspace_id, LegalHold.released_at.is_(None))
        .limit(1)
    ):
        return counts
    limit = min(100, max(1, limit))

    def expired(model, purpose, *conditions):
        cutoff = reviewed_cutoff(session, workspace_id, purpose)
        if cutoff is None:
            return []
        return session.scalars(
            select(model)
            .where(model.workspace_id == workspace_id, model.created_at <= cutoff, *conditions)
            .order_by(model.created_at, model.id)
            .limit(limit)
        ).all()

    from sqlalchemy import JSON, and_, or_

    from app.privacy_ops.events import apply_event, record_event

    retained_ai = or_(
        AIRun.state != "invalidated",
        and_(AIRun.output.is_not(None), AIRun.output != JSON.NULL),
        AIRun.instruction != "",
        AIRun.coverage != {},
        select(AIEvidence.id).where(AIEvidence.run_id == AIRun.id).exists(),
    )
    for model, purpose, action, conditions in (
        (CollectionSession, "raw", "session_delete", (CollectionSession.state != "erased",)),
        (AIRun, "derived", "ai_delete", (retained_ai,)),
        (AnalysisSnapshot, "derived", "snapshot_delete", ()),
        (Export, "export", "export_delete", ()),
        (ReportShare, "export", "share_revoke", (ReportShare.revoked_at.is_(None),)),
    ):
        for row in expired(model, purpose, *conditions):
            record_event(session, workspace_id, action, row.id)
            apply_event(session, workspace_id, action, row.id)
            counts[purpose] += 1
    if any(counts.values()):
        workspace.privacy_epoch += 1  # fence in-flight producers before commit
    session.flush()
    return counts


def held_asset(session, asset):
    if held(session, asset.workspace_id, asset.owner_id):
        return True
    from app.longitudinal.models import Recording

    return any(
        held(session, asset.workspace_id, subject)
        for subject in session.scalars(
            select(Recording.subject_id).where(
                Recording.workspace_id == asset.workspace_id, Recording.asset_id == asset.id
            )
        )
    )
