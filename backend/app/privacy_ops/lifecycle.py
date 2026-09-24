"""Explicit workspace-local lifecycle; no global identity or financial deletion.

Caller owns transaction. All entry points serialize against workspace privacy.
Reviewed raw retention governs datasets; contact expiry is explicit at collection.
"""

import hashlib

from sqlalchemy import delete, select

from app.auth.security import utcnow
from app.common.errors import DomainError
from app.common.privacy import lock_workspace
from app.privacy_ops.lifecycle_models import ContactHold


def contact_held(session, workspace_id, contact_id):
    return (
        session.scalar(
            select(ContactHold.id)
            .where(
                ContactHold.workspace_id == workspace_id,
                ContactHold.contact_id == contact_id,
                ContactHold.released_at.is_(None),
            )
            .limit(1)
        )
        is not None
    )


def apply_lifecycle_event(session, workspace_id, action, resource_id, storage=None):
    from app.auth.models import AuditEvent
    from app.collaboration.models import ReportComment
    from app.common.idempotency import IdempotencyRecord
    from app.evaluation.models import EvaluationDataset
    from app.longitudinal.models import Recording, TranscriptSegment
    from app.privacy_ops.service import workspace_held
    from app.recruiting.models import Candidate, PrivateContact
    from app.studies.models import Study

    lock_workspace(session, workspace_id)
    if action == "study_delete" and session.scalar(
        select(ContactHold.id)
        .where(ContactHold.workspace_id == workspace_id, ContactHold.released_at.is_(None))
        .limit(1)
    ):
        raise DomainError(
            "PRIVACY_HOLD", "Workspace contact hold defers shared study erasure.", 409
        )
    models = {
        "dataset_delete": EvaluationDataset,
        "contact_delete": PrivateContact,
        "recording_delete": Recording,
        "study_delete": Study,
        "candidate_delete": Candidate,
        "comment_delete": ReportComment,
        "idempotency_scrub": IdempotencyRecord,
        "audit_scrub": AuditEvent,
    }
    if action not in models:
        raise ValueError("Lifecycle action not implemented; restore remains quarantined")
    model = models[action]
    row = session.scalar(
        select(model).where(model.workspace_id == workspace_id, model.id == resource_id)
    )
    if row is None:
        return
    if workspace_held(session, workspace_id) or (
        action == "contact_delete" and contact_held(session, workspace_id, resource_id)
    ):
        raise DomainError("PRIVACY_HOLD", "Release the scoped hold before erasure.", 409)
    from app.privacy_ops.events import record_event

    record_event(session, workspace_id, action, resource_id)
    if action == "contact_delete":
        # Retain consent and financial identifiers, remove personal payload/lookup.
        candidates = session.scalars(
            select(Candidate).where(
                Candidate.workspace_id == workspace_id,
                Candidate.source_kind == "private",
                Candidate.source_id == resource_id,
            )
        ).all()
        for candidate in candidates:
            _purge_candidate(session, workspace_id, candidate)
        row.status, row.attributes_json, row.source = "withdrawn", {}, ""
        row.contact_lookup_hash = hashlib.sha256(("erased:" + str(row.id)).encode()).hexdigest()
    elif action == "candidate_delete":
        if (
            row.source_kind == "private"
            and row.source_id
            and contact_held(session, workspace_id, row.source_id)
        ):
            raise DomainError("PRIVACY_HOLD", "Release the contact hold before erasure.", 409)
        _purge_candidate(session, workspace_id, row)
    elif action == "study_delete":
        _purge_study(session, workspace_id, row.id, storage)
    elif action == "idempotency_scrub":
        row.response = None
        row.expires_at = min(row.expires_at, utcnow())
    elif action == "audit_scrub":
        row.details = {}
    elif action == "recording_delete":
        # Purge the actual media first, never report success for metadata-only erasure.
        from app.privacy_ops.events import apply_event, record_event

        record_event(session, workspace_id, "asset_delete", row.asset_id)
        apply_event(session, workspace_id, "asset_delete", row.asset_id, storage=storage)
        session.execute(
            delete(TranscriptSegment).where(
                TranscriptSegment.workspace_id == workspace_id,
                TranscriptSegment.recording_id == row.id,
            )
        )
        session.delete(row)
    else:
        # Evaluation children are scoped CASCADEs; immutable originals permit DELETE.
        session.delete(row)
    session.flush()


def erase_contact(session, workspace_id, contact_id):
    from app.common.privacy import get_scoped
    from app.privacy_ops.events import record_event
    from app.recruiting.models import PrivateContact

    workspace = lock_workspace(session, workspace_id)
    get_scoped(session, PrivateContact, workspace_id, contact_id)
    apply_lifecycle_event(session, workspace_id, "contact_delete", contact_id)
    record_event(session, workspace_id, "contact_delete", contact_id)
    workspace.privacy_epoch += 1
    session.flush()


def sweep_lifecycle(session, workspace_id, limit=100, storage=None):
    from sqlalchemy import JSON, and_, or_

    from app.auth.models import AuditEvent
    from app.collaboration.models import ReportComment
    from app.common.idempotency import IdempotencyRecord
    from app.evaluation.models import EvaluationDataset
    from app.longitudinal.models import Recording
    from app.privacy_ops.events import record_event
    from app.privacy_ops.models import RestoreEvent
    from app.privacy_ops.service import reviewed_cutoff, workspace_held
    from app.recruiting.models import Candidate, PrivateContact
    from app.studies.models import Study, StudyVersion

    workspace = lock_workspace(session, workspace_id)
    limit = min(100, max(1, limit))
    counts = {
        key: 0
        for key in (
            "contacts",
            "datasets",
            "recordings",
            "studies",
            "recruitment",
            "collaboration",
            "operational",
        )
    }
    if workspace_held(session, workspace_id):
        return counts
    cutoff = reviewed_cutoff(session, workspace_id, "raw")
    specs = [
        (PrivateContact, "contact_delete", "contacts", PrivateContact.retention_until <= utcnow())
    ]
    if cutoff is not None:
        specs.append(
            (
                EvaluationDataset,
                "dataset_delete",
                "datasets",
                EvaluationDataset.created_at <= cutoff,
            )
        )
        if storage is not None:
            specs.append(
                (Recording, "recording_delete", "recordings", Recording.created_at <= cutoff)
            )
    if cutoff is not None:
        study_expired = and_(Study.created_at <= cutoff, Study.status.in_(["closed", "archived"]))
        study_expired = and_(
            study_expired,
            ~select(RestoreEvent.id)
            .where(
                RestoreEvent.workspace_id == workspace_id,
                RestoreEvent.action == "study_delete",
                RestoreEvent.resource_id == Study.id,
            )
            .exists(),
        )
        study_expired = and_(
            study_expired,
            ~select(ContactHold.id)
            .where(ContactHold.workspace_id == workspace_id, ContactHold.released_at.is_(None))
            .exists(),
        )
        if storage is None:
            study_expired = and_(
                study_expired,
                ~select(Recording.id)
                .join(StudyVersion, StudyVersion.id == Recording.version_id)
                .where(Recording.workspace_id == workspace_id, StudyVersion.study_id == Study.id)
                .exists(),
            )
        specs.extend(
            [
                (Study, "study_delete", "studies", study_expired),
                (
                    Candidate,
                    "candidate_delete",
                    "recruitment",
                    and_(
                        Candidate.created_at <= cutoff,
                        or_(
                            Candidate.status != "withdrawn",
                            Candidate.attributes_json != {},
                            Candidate.source_id.is_not(None),
                        ),
                        ~select(ContactHold.id)
                        .where(
                            ContactHold.workspace_id == workspace_id,
                            ContactHold.contact_id == Candidate.source_id,
                            ContactHold.released_at.is_(None),
                        )
                        .exists(),
                    ),
                ),
                (
                    ReportComment,
                    "comment_delete",
                    "collaboration",
                    ReportComment.created_at <= cutoff,
                ),
                (
                    IdempotencyRecord,
                    "idempotency_scrub",
                    "operational",
                    and_(
                        IdempotencyRecord.created_at <= cutoff,
                        IdempotencyRecord.response.is_not(None),
                        IdempotencyRecord.response != JSON.NULL,
                    ),
                ),
                (
                    AuditEvent,
                    "audit_scrub",
                    "operational",
                    and_(AuditEvent.created_at <= cutoff, AuditEvent.details != {}),
                ),
            ]
        )
    for model, action, key, condition in specs:
        remaining = limit - sum(counts.values())
        if not remaining:
            break
        query = select(model).where(model.workspace_id == workspace_id, condition)
        if action == "contact_delete":
            query = query.where(
                ~select(RestoreEvent.id)
                .where(
                    RestoreEvent.workspace_id == workspace_id,
                    RestoreEvent.action == action,
                    RestoreEvent.resource_id == model.id,
                )
                .exists(),
                ~select(ContactHold.id)
                .where(
                    ContactHold.workspace_id == workspace_id,
                    ContactHold.contact_id == model.id,
                    ContactHold.released_at.is_(None),
                )
                .exists(),
            )
        for row in session.scalars(
            query.order_by(model.created_at, model.id).limit(remaining)
        ).all():
            apply_lifecycle_event(session, workspace_id, action, row.id, storage=storage)
            record_event(session, workspace_id, action, row.id)
            counts[key] += 1
    if any(counts.values()):
        workspace.privacy_epoch += 1
    session.flush()
    return counts


def _purge_candidate(session, wid, candidate):
    from app.collection.models import CollectionSession
    from app.privacy_ops.events import apply_event, record_event
    from app.recruiting.models import Invitation, ScreenerResult
    from app.recruiting.service import release_reservation

    # Resolve dependencies BEFORE severing the unlinked private-contact reference.
    for collection in session.scalars(
        select(CollectionSession).where(
            CollectionSession.workspace_id == wid,
            CollectionSession.candidate_id == candidate.id,
        )
    ).all():
        record_event(session, wid, "session_delete", collection.id)
        apply_event(session, wid, "session_delete", collection.id)
    release_reservation(session, wid, candidate.id)
    session.execute(
        delete(ScreenerResult).where(
            ScreenerResult.workspace_id == wid, ScreenerResult.candidate_id == candidate.id
        )
    )
    for invitation in session.scalars(
        select(Invitation).where(
            Invitation.workspace_id == wid, Invitation.candidate_id == candidate.id
        )
    ):
        invitation.revoked_at = invitation.revoked_at or utcnow()
    candidate.status, candidate.attributes_json, candidate.source_id = "withdrawn", {}, None


def _purge_study(session, wid, study_id, storage):
    """Exact source id, not owner-wide erasure. No billing tables are deleted."""
    from app.ai.models import AIRun
    from app.analytics.service import purge_studies
    from app.collection.privacy import purge_launches
    from app.common.privacy_models import ConsentReceipt
    from app.evaluation.privacy import purge_studies as purge_evaluation
    from app.longitudinal.models import Recording
    from app.longitudinal.service import purge_studies as purge_longitudinal
    from app.privacy_ops.events import apply_event, record_event
    from app.recruiting.service import erase_launches
    from app.studies.models import Launch, Study, StudyGrant, StudyVersion

    versions = select(StudyVersion.id).where(
        StudyVersion.workspace_id == wid, StudyVersion.study_id == study_id
    )
    launches = list(
        session.scalars(
            select(Launch.id).where(Launch.workspace_id == wid, Launch.version_id.in_(versions))
        )
    )
    from app.recruiting.models import Reservation

    retain_financial = (
        session.scalar(
            select(Reservation.id)
            .where(Reservation.workspace_id == wid, Reservation.launch_id.in_(launches))
            .limit(1)
        )
        is not None
    )
    from app.recruiting.models import Candidate

    held_contacts = select(ContactHold.contact_id).where(
        ContactHold.workspace_id == wid, ContactHold.released_at.is_(None)
    )
    if session.scalar(
        select(Candidate.id)
        .where(
            Candidate.workspace_id == wid,
            Candidate.launch_id.in_(launches),
            Candidate.source_kind == "private",
            Candidate.source_id.in_(held_contacts),
        )
        .limit(1)
    ):
        raise DomainError("PRIVACY_HOLD", "Study includes a held private contact.", 409)
    for recording in session.scalars(
        select(Recording).where(Recording.workspace_id == wid, Recording.version_id.in_(versions))
    ).all():
        apply_lifecycle_event(session, wid, "recording_delete", recording.id, storage)
        record_event(session, wid, "recording_delete", recording.id)
    for run in session.scalars(
        select(AIRun).where(AIRun.workspace_id == wid, AIRun.study_id == study_id)
    ).all():
        apply_event(session, wid, "ai_delete", run.id)
        record_event(session, wid, "ai_delete", run.id)
        run.study_id, run.snapshot_id = None, None
    session.flush()
    purge_longitudinal(session, wid, [study_id])
    purge_evaluation(session, wid, [study_id])
    purge_studies(session, wid, [study_id])
    purge_launches(session, wid, launches)
    if retain_financial:
        _minimize_study_shells(session, wid, study_id, launches)
    else:
        erase_launches(session, wid, launches)
    session.execute(
        delete(ConsentReceipt).where(
            ConsentReceipt.workspace_id == wid, ConsentReceipt.study_version_id.in_(versions)
        )
    )
    if retain_financial:
        session.execute(
            delete(StudyGrant).where(
                StudyGrant.workspace_id == wid, StudyGrant.study_id == study_id
            )
        )
        return
    session.execute(
        delete(Launch).where(Launch.workspace_id == wid, Launch.version_id.in_(versions))
    )
    session.execute(
        delete(StudyGrant).where(StudyGrant.workspace_id == wid, StudyGrant.study_id == study_id)
    )
    # Template instances/grants cascade with their exact source version.
    session.execute(
        delete(StudyVersion).where(
            StudyVersion.workspace_id == wid, StudyVersion.study_id == study_id
        )
    )
    session.execute(delete(Study).where(Study.workspace_id == wid, Study.id == study_id))


def _minimize_study_shells(session, wid, study_id, launches):
    """Keep financial IDs/counts/provenance hashes, remove executable and raw content."""
    from app.collaboration.models import TemplateGrant
    from app.recruiting.models import Candidate, QuotaCell, RecruitmentConfig
    from app.studies.models import Launch, Study, StudyVersion
    from app.templates.models import TemplateInstance

    for candidate in session.scalars(
        select(Candidate).where(Candidate.workspace_id == wid, Candidate.launch_id.in_(launches))
    ).all():
        _purge_candidate(session, wid, candidate)
    for config in session.scalars(
        select(RecruitmentConfig).where(
            RecruitmentConfig.workspace_id == wid, RecruitmentConfig.launch_id.in_(launches)
        )
    ):
        config.filters_json, config.screener_json = {}, {}
    for cell in session.scalars(
        select(QuotaCell).where(QuotaCell.workspace_id == wid, QuotaCell.launch_id.in_(launches))
    ):
        cell.filters_json = {}
    for launch in session.scalars(
        select(Launch).where(Launch.workspace_id == wid, Launch.id.in_(launches))
    ):
        launch.state = "closed"
    for template in session.scalars(
        select(TemplateInstance).where(
            TemplateInstance.workspace_id == wid, TemplateInstance.study_id == study_id
        )
    ):
        template.recipe_snapshot, template.inputs_snapshot = {}, {}
        session.execute(
            delete(TemplateGrant).where(
                TemplateGrant.workspace_id == wid, TemplateGrant.instance_id == template.id
            )
        )
    for version in session.scalars(
        select(StudyVersion).where(
            StudyVersion.workspace_id == wid, StudyVersion.study_id == study_id
        )
    ):
        version.blocks_json, version.rules_json, version.consent_documents, version.locales = (
            [],
            {},
            {},
            [],
        )
    study = session.scalar(select(Study).where(Study.workspace_id == wid, Study.id == study_id))
    study.title, study.status = "Erased study", "archived"
    session.flush()
