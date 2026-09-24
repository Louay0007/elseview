"""Global assessment privacy, deliberately outside workspace subject exports."""

from uuid import UUID

from sqlalchemy import select, update

from app.auth.security import utcnow
from app.recruiting.models import (
    LanguageAssessmentAttempt as Attempt,
)
from app.recruiting.models import (
    LanguageAssessmentConsent as Consent,
)
from app.recruiting.models import (
    LanguageAssessmentDecision as Decision,
)
from app.recruiting.models import (
    LanguageAssessmentVersion as Version,
)
from app.recruiting.models import (
    ParticipantProfile,
)


def purge_attempt(session, attempt):
    attempt.responses_json = None
    attempt.submission_digest = None
    attempt.appeal_reason = None
    attempt.appeal_digest = None
    attempt.purged_at = attempt.purged_at or utcnow()
    if attempt.state in {"started", "submitted"}:
        attempt.state = "abandoned"
    session.execute(
        update(Decision)
        .where(Decision.attempt_id == attempt.id)
        .values(findings_json=None, rationale=None, request_digest="0" * 64)
    )


def purge_account(session, subject_id):
    """Called under account's user lock; idempotent, no workspace lock acquisition."""
    profile_ids = select(ParticipantProfile.id).where(ParticipantProfile.user_id == subject_id)
    for attempt in session.scalars(
        select(Attempt).where(Attempt.profile_id.in_(profile_ids)).with_for_update()
    ):
        purge_attempt(session, attempt)
        attempt.state = "withdrawn"
    # Institutional version/decision UUID attribution remains, never names/email.
    # Disable future starts on content authored or approved by the erased operator.
    session.execute(
        update(Version)
        .where(
            (Version.author_id == subject_id) | (Version.approved_by == subject_id),
            Version.state == "approved",
        )
        .values(state="retired")
    )
    session.execute(
        update(Version)
        .where(Version.approved_by == subject_id)
        .values(review_reference="operator-erased")
    )
    session.execute(
        update(Decision)
        .where(Decision.reviewer_id == subject_id)
        .values(findings_json=None, rationale=None, request_digest="0" * 64)
    )
    session.flush()


def sweep(session, *, language=None, limit=100):
    if not 1 <= limit <= 500:
        raise ValueError("Invalid assessment purge limit")
    query = select(Attempt).where(Attempt.retention_until <= utcnow(), Attempt.purged_at.is_(None))
    if language:
        query = query.where(Attempt.language == language)
    attempts = list(
        session.scalars(
            query.order_by(Attempt.retention_until, Attempt.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    for attempt in attempts:
        purge_attempt(session, attempt)
    session.flush()
    return len(attempts)


def export_revocations(session):
    return [
        dict(profile_id=str(p), grant_id=str(g))
        for p, g in session.execute(
            select(Consent.profile_id, Consent.grant_id)
            .where(Consent.decision == "withdrawn")
            .distinct()
            .order_by(Consent.profile_id, Consent.grant_id)
        )
    ]


def validate_revocations(rows):
    if not isinstance(rows, list):
        raise ValueError("Invalid assessment revocations")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"profile_id", "grant_id"}:
            raise ValueError("Invalid assessment revocation")
        if any(not isinstance(value, str) for value in row.values()):
            raise ValueError("Invalid assessment revocation identifiers")
        pair = (UUID(row["profile_id"]), UUID(row["grant_id"]))
        if pair in seen:
            raise ValueError("Duplicate assessment revocation")
        seen.add(pair)


def replay_revocations(session, rows):
    from app.recruiting.assessments import CONSENT_DIGEST
    from app.recruiting.service import digest

    validate_revocations(rows)
    for row in rows:
        profile_id, grant_id = UUID(row["profile_id"]), UUID(row["grant_id"])
        grant = session.get(Consent, grant_id)
        if grant is None:
            continue
        if grant.profile_id != profile_id or grant.decision != "granted":
            raise ValueError("Assessment revocation scope mismatch")
        if not session.scalar(
            select(Consent.id)
            .where(Consent.grant_id == grant_id, Consent.decision == "withdrawn")
            .limit(1)
        ):
            session.add(
                Consent(
                    profile_id=profile_id,
                    grant_id=grant_id,
                    decision="withdrawn",
                    document_version="1",
                    document_digest=CONSENT_DIGEST,
                    receipt_key="restore:" + str(grant_id),
                    request_digest=digest(row),
                )
            )
        session.execute(
            update(Attempt)
            .where(Attempt.profile_id == profile_id, Attempt.consent_grant_id == grant_id)
            .values(state="withdrawn")
        )
    session.flush()
