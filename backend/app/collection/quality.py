"""Deterministic evidence only: never a review decision or compensation denial."""

from sqlalchemy import select

from app.auth.models import User, Workspace
from app.collection.models import Answer, AnswerRevision, CollectionSession, InteractionAttempt
from app.common.privacy import consent_granted
from app.common.privacy_models import ConsentReceipt
from app.studies.models import StudyVersion


def enqueue_quality(session, row):
    from app.jobs.service import enqueue

    return enqueue(
        session,
        workspace_id=row.workspace_id,
        requester_id=row.subject_id,
        command_key="collection.submit:" + str(row.id),
        kind="collection.quality",
        target_id=row.id,
        internal=True,
    )


def quality_job_allowed(session, job):
    workspace = session.scalar(
        select(Workspace)
        .where(Workspace.id == job.workspace_id)
        .with_for_update(read=True)
        .execution_options(populate_existing=True)
    )
    row = session.scalar(
        select(CollectionSession)
        .where(CollectionSession.id == job.target_id)
        .execution_options(populate_existing=True)
    )
    user = session.get(User, job.requester_id)
    if not user or user.status != "active" or not user.verified_at:
        return False
    if (
        not row
        or not workspace
        or workspace.status != "active"
        or workspace.privacy_epoch != job.privacy_epoch
    ):
        return False
    if (
        row.workspace_id != job.workspace_id
        or row.subject_id != job.requester_id
        or row.state != "submitted"
    ):
        return False
    receipt = session.get(ConsentReceipt, row.consent_receipt_id)
    from app.common.errors import DomainError
    from app.recruiting.models import Candidate
    from app.recruiting.service import validate_source

    candidate = session.get(Candidate, row.candidate_id)
    try:
        if candidate is None:
            return False
        validate_source(session, candidate)
    except DomainError:
        return False
    return bool(
        receipt
        and consent_granted(
            session, row.workspace_id, row.subject_id, "study", receipt.document_id, row.version_id
        )
    )


def finish_quality(session, job):
    if not quality_job_allowed(session, job):
        return {"status": "unavailable"}
    row = session.get(CollectionSession, job.target_id)
    version = session.get(StudyVersion, row.version_id)
    flags = []
    for key, pointer in (row.submitted_snapshot or {}).items():
        answer = session.scalar(
            select(Answer).where(Answer.session_id == row.id, Answer.block_key == key)
        )
        revision = session.scalar(
            select(AnswerRevision).where(
                AnswerRevision.answer_id == answer.id,
                AnswerRevision.revision == pointer["revision"],
            )
        )
        value = revision.payload.get("value") or {}
        expected = version.rules_json.get(key, {}).get("expected_option")
        if expected is not None and value.get("option_id") != expected:
            flags.append({"block_key": key, "code": "attention_mismatch"})
        if revision.payload["status"] == "unable":
            flags.append({"block_key": key, "code": "participant_unable"})
        rule = version.rules_json.get(key, {})
        if revision.payload["status"] == "responded":
            if "min_text_length" in rule and len(value.get("text", "")) < rule["min_text_length"]:
                flags.append({"block_key": key, "code": "short_text"})
            if "min_elapsed_ms" in rule and value.get("elapsed_ms", 0) < rule["min_elapsed_ms"]:
                flags.append({"block_key": key, "code": "fast_task"})
    for attempt in session.scalars(
        select(InteractionAttempt).where(InteractionAttempt.session_id == row.id)
    ):
        if attempt.state != "completed" or attempt.visible_ms != 5000:
            flags.append({"block_key": attempt.block_key, "code": "exposure_timing_uncertain"})
    row.quality_summary = {
        "status": "pending_human_review",
        "policy": "p07_deterministic_v1",
        "flags": flags,
        "decision": None,
        "reward_decision": None,
    }
    from app.reviews.service import sync_quality

    sync_quality(session, row)
    return row.quality_summary
