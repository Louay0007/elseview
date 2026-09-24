"""Human-adjudicated text tasks. Transactions belong to callers; no automatic pass.

Lock order: authority workspace (authority operations only), sorted user IDs,
then profile/version/attempt. Participant operations never acquire workspace locks.
"""

from datetime import timedelta
from typing import get_args

from sqlalchemy import func, select

from app.auth.models import User
from app.auth.security import utcnow
from app.auth.service import audit, require_workspace
from app.common.privacy import lock_workspace, require_unrestricted
from app.recruiting.assessment_schemas import Language, VersionBody
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
    LanguageAssessmentKey as Key,
)
from app.recruiting.models import (
    LanguageAssessmentVersion as Version,
)
from app.recruiting.models import (
    ParticipantProfile,
    Qualification,
)
from app.recruiting.service import digest, fail

CONSENT_DOCUMENT = (
    "Language text-assessment consent v1: optional bounded text responses and human review "
    "by authorized assessment operators, participant access to responses and decisions, "
    "and limited use of non-synthetic reviewed qualifications for public-panel recruitment. "
    "Each assessment publishes its response retention period, timing, attempt/cooldown "
    "limits and qualification validity. Identifier-only consent and decision history may "
    "be retained to prevent resurrection; responses, appeal reasons, rationale and "
    "findings are removed after the published retention deadline or account erasure. "
    "Withdraw this exact grant at any time to block its future assessment and qualification "
    "use; a new grant does not restore old evidence. This is text-task performance, not "
    "speech, accent, translation certification or professional credentials. It does not "
    "authorize study participation, recording or private-panel use. Synthetic assessments "
    "cannot confer recruitable qualifications. One appeal is available within 30 days "
    "of the first decision while evidence remains retained."
)
CONSENT_DIGEST = digest(CONSENT_DOCUMENT)
LANGUAGES = list(get_args(Language))


def lock_users(session, *ids):
    users = {}
    for uid in sorted(set(ids), key=str):
        user = session.scalar(
            select(User)
            .where(User.id == uid)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not user or user.status != "active" or not user.verified_at:
            fail("ASSESSMENT_IDENTITY_UNAVAILABLE", 403)
        users[uid] = user
    return users


def profile_for(session, user_id, *, active=True):
    lock_users(session, user_id)
    profile = session.scalar(
        select(ParticipantProfile)
        .where(ParticipantProfile.user_id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not profile or (active and profile.status != "active"):
        fail("OPT_IN_REQUIRED", 409)
    return profile


def authority(
    session, settings, workspace_id, actor_id, language, *, author=False, subject_id=None
):
    if settings.language_assessment_authority_workspace_id != workspace_id:
        fail()
    lock_workspace(session, workspace_id)
    lock_users(session, actor_id, *([subject_id] if subject_id else []))
    require_workspace(
        session, actor_id, workspace_id, "studies.create" if author else "workspace.read"
    )
    require_unrestricted(session, workspace_id, actor_id)
    if not author and language not in settings.language_assessment_reviewers.get(actor_id, []):
        fail("ASSESSMENT_REVIEWER_REQUIRED", 403)


def version_for(session, version_id, *, lock=False):
    query = select(Version).where(Version.id == version_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    version = session.scalar(query)
    if not version:
        fail()
    return version


def version_output(version, *, detail=False):
    value = dict(
        id=version.id,
        assessment_key=version.assessment_key,
        version=version.version,
        language=version.language,
        schema_version=version.schema_version,
        synthetic=version.synthetic,
        state=version.state,
        policy=version.policy_json,
        limitations=version.public_json["limitations"],
        public_digest=version.public_digest,
    )
    if detail:
        value.update(tasks=version.public_json["tasks"], content_digest=version.content_digest)
    return value


def create_version(session, settings, workspace_id, actor_id, body):
    authority(session, settings, workspace_id, actor_id, body.language, author=True)
    prior = session.scalar(
        select(Version).where(
            Version.assessment_key == body.assessment_key, Version.version == body.version
        )
    )
    full = body.model_dump(mode="json")
    if prior:
        if prior.author_id != actor_id or prior.content_digest != digest(full):
            fail("ASSESSMENT_VERSION_CONFLICT", 409)
        return prior
    public = {"tasks": full["tasks"], "limitations": full["limitations"]}
    row = Version(
        assessment_key=body.assessment_key,
        version=body.version,
        language=body.language,
        schema_version=1,
        author_id=actor_id,
        synthetic=body.synthetic,
        public_json=public,
        policy_json=full["policy"],
        public_digest=digest(full | {"material": None}),
        content_digest=digest(full),
        state="draft",
    )
    session.add(row)
    session.flush()
    session.add(Key(version_id=row.id, material_json=full["material"]))
    audit(session, "language.version_created", actor_id=actor_id, object_id=row.id)
    session.flush()
    return row


def checked_material(session, version):
    key = session.get(Key, version.id)
    if not key:
        fail("ASSESSMENT_MATERIAL_UNAVAILABLE", 409)
    try:
        full = VersionBody(
            assessment_key=version.assessment_key,
            version=version.version,
            language=version.language,
            schema_version=version.schema_version,
            synthetic=version.synthetic,
            policy=version.policy_json,
            material=key.material_json,
            **version.public_json,
        ).model_dump(mode="json")
    except (ValueError, TypeError):
        fail("ASSESSMENT_MATERIAL_UNAVAILABLE", 409)
    if digest(full) != version.content_digest:
        fail("ASSESSMENT_CONTENT_CHANGED", 409)
    return key.material_json


def approve_version(session, settings, wid, uid, version_id, body):
    version = version_for(session, version_id)
    authority(session, settings, wid, uid, version.language)
    version = version_for(session, version_id, lock=True)
    if uid == version.author_id:
        fail("INDEPENDENT_REVIEW_REQUIRED", 403)
    if body.content_digest != version.content_digest:
        fail("ASSESSMENT_DIGEST_MISMATCH", 409)
    if version.state == "approved":
        if version.approved_by != uid or version.review_reference != body.review_reference:
            fail("ASSESSMENT_APPROVAL_CONFLICT", 409)
        return version
    if version.state != "draft":
        fail("ASSESSMENT_VERSION_FROZEN", 409)
    checked_material(session, version)
    version.state, version.approved_by, version.approved_at = "approved", uid, utcnow()
    version.review_reference = body.review_reference
    audit(
        session,
        "language.version_approved",
        actor_id=uid,
        object_id=version.id,
        synthetic=version.synthetic,
    )
    session.flush()
    return version


def retire_version(session, settings, wid, uid, version_id, body):
    version = version_for(session, version_id)
    authority(session, settings, wid, uid, version.language)
    version = version_for(session, version_id, lock=True)
    if version.content_digest != body.content_digest or version.state not in {
        "approved",
        "retired",
    }:
        fail("ASSESSMENT_VERSION_CONFLICT", 409)
    version.state = "retired"
    audit(session, "language.version_retired", actor_id=uid, object_id=version.id)
    session.flush()
    return version


def grant_live(session, profile_id, grant_id):
    grant = session.scalar(
        select(Consent).where(Consent.id == grant_id, Consent.profile_id == profile_id)
    )
    return bool(
        grant
        and grant.decision == "granted"
        and grant.document_version == "1"
        and grant.document_digest == CONSENT_DIGEST
        and not session.scalar(
            select(Consent.id)
            .where(
                Consent.profile_id == profile_id,
                Consent.grant_id == grant_id,
                Consent.decision == "withdrawn",
            )
            .limit(1)
        )
    )


def require_grant(session, profile_id, grant_id):
    if not grant_live(session, profile_id, grant_id):
        fail("ASSESSMENT_CONSENT_REQUIRED", 403)


def consent_update(session, user_id, body):
    profile = profile_for(session, user_id, active=body.decision == "granted")
    if body.presented_digest != CONSENT_DIGEST:
        fail("CONSENT_DOCUMENT_MISMATCH", 409)
    request_digest = digest(body.model_dump(mode="json"))
    prior = session.scalar(
        select(Consent).where(
            Consent.profile_id == profile.id, Consent.receipt_key == body.receipt_key
        )
    )
    if prior:
        if prior.request_digest != request_digest:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return prior
    if body.grant_id:
        grant = session.scalar(
            select(Consent).where(
                Consent.id == body.grant_id,
                Consent.profile_id == profile.id,
                Consent.decision == "granted",
            )
        )
        if not grant:
            fail()
    row = Consent(
        profile_id=profile.id,
        decision=body.decision,
        document_version="1",
        document_digest=CONSENT_DIGEST,
        receipt_key=body.receipt_key,
        request_digest=request_digest,
        grant_id=body.grant_id,
    )
    session.add(row)
    session.flush()
    if body.grant_id:
        for attempt in session.scalars(
            select(Attempt)
            .where(Attempt.profile_id == profile.id, Attempt.consent_grant_id == body.grant_id)
            .with_for_update()
        ):
            attempt.state = "withdrawn"
    audit(session, "language.consent_" + body.decision, actor_id=user_id, object_id=row.id)
    session.flush()
    return row


def consent_output(row):
    return dict(id=row.id, decision=row.decision, grant_id=row.grant_id, created_at=row.created_at)


def consent_grants(session, uid, offset, limit):
    # Grants are document-scoped, not version-scoped: never join the catalogue or attempts.
    lock_users(session, uid)
    profile_id = session.scalar(
        select(ParticipantProfile.id).where(ParticipantProfile.user_id == uid)
    )
    if profile_id is None:
        return dict(items=[], next_offset=None)
    rows = list(
        session.execute(
            select(Consent.id, Consent.document_version, Consent.created_at)
            .where(Consent.profile_id == profile_id, Consent.decision == "granted")
            .order_by(Consent.created_at.desc(), Consent.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    )
    page = rows[:limit]
    withdrawn = dict(
        session.execute(
            select(Consent.grant_id, func.min(Consent.created_at))
            .where(
                Consent.profile_id == profile_id,
                Consent.decision == "withdrawn",
                Consent.grant_id.in_([row.id for row in page]),
            )
            .group_by(Consent.grant_id)
        ).all()
    ) if page else {}
    return dict(
        items=[
            dict(
                id=row.id,
                document_version=row.document_version,
                created_at=row.created_at,
                withdrawn_at=withdrawn.get(row.id),
            )
            for row in page
        ],
        next_offset=offset + limit if len(rows) > limit else None,
    )


def owned_attempt(session, uid, attempt_id, *, active=False):
    if not session.scalar(
        select(Attempt.id)
        .join(ParticipantProfile, ParticipantProfile.id == Attempt.profile_id)
        .where(Attempt.id == attempt_id, ParticipantProfile.user_id == uid)
    ):
        fail()
    profile = profile_for(session, uid, active=active)
    attempt = session.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id, Attempt.profile_id == profile.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not attempt:
        fail()
    return attempt


def start(session, settings, uid, body):
    if not settings.language_assessment_authority_workspace_id:
        fail("ASSESSMENT_AUTHORITY_DISABLED", 409)
    profile = profile_for(session, uid)
    request_digest = digest(body.model_dump(mode="json"))
    prior = session.scalar(
        select(Attempt).where(
            Attempt.profile_id == profile.id, Attempt.command_key == body.command_key
        )
    )
    if prior:
        if prior.start_digest != request_digest:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return prior
    require_grant(session, profile.id, body.consent_grant_id)
    version = version_for(session, body.version_id, lock=True)
    if version.state != "approved":
        fail("ASSESSMENT_UNAVAILABLE", 409)
    checked_material(session, version)
    now = utcnow()
    # Starts count across versions; expired starts remain in the rolling counter.
    latest = session.scalar(
        select(Attempt)
        .where(Attempt.profile_id == profile.id, Attempt.language == version.language)
        .order_by(Attempt.sequence.desc())
        .limit(1)
    )
    attempts = list(
        session.scalars(
            select(Attempt)
            .where(
                Attempt.profile_id == profile.id,
                Attempt.language == version.language,
                (Attempt.started_at > now - timedelta(days=30))
                | Attempt.state.in_(["started", "submitted"]),
            )
            .order_by(Attempt.sequence.desc())
            .with_for_update()
        )
    )
    for old in attempts:
        if old.state == "started" and old.deadline_at <= now:
            old.state = "abandoned"
        if old.state == "submitted" and old.retention_until <= now:
            old.state = "abandoned"
    if any(a.state in {"started", "submitted"} for a in attempts):
        fail("ASSESSMENT_IN_PROGRESS", 409)
    policy = version.policy_json
    # A weaker new version must not shorten the preceding start's published cooldown.
    cooldown = policy["cooldown_hours"]
    if latest:
        previous_version = session.get(Version, latest.version_id)
        cooldown = max(cooldown, previous_version.policy_json["cooldown_hours"])
    if latest and latest.started_at + timedelta(hours=cooldown) > now:
        fail("ASSESSMENT_COOLDOWN", 409)
    recent = [a for a in attempts if a.started_at > now - timedelta(days=30)]
    limit = min(
        [
            policy["max_starts_30_days"],
            *[session.get(Version, a.version_id).policy_json["max_starts_30_days"] for a in recent],
        ]
    )
    if len(recent) >= limit:
        fail("ASSESSMENT_ATTEMPT_LIMIT", 409)
    session.flush()
    row = Attempt(
        profile_id=profile.id,
        version_id=version.id,
        language=version.language,
        consent_grant_id=body.consent_grant_id,
        sequence=(latest.sequence + 1 if latest else 1),
        command_key=body.command_key,
        start_digest=request_digest,
        state="started",
        started_at=now,
        deadline_at=now + timedelta(minutes=policy["duration_minutes"]),
        retention_until=now + timedelta(days=policy["retention_days"]),
    )
    session.add(row)
    session.flush()
    audit(session, "language.attempt_started", actor_id=uid, object_id=row.id)
    return row


def submit(session, uid, attempt_id, body):
    attempt = owned_attempt(session, uid, attempt_id, active=True)
    require_grant(session, attempt.profile_id, attempt.consent_grant_id)
    request_digest = digest(body.model_dump(mode="json"))
    if attempt.submission_digest:
        if attempt.submit_key != body.command_key or attempt.submission_digest != request_digest:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return attempt
    if attempt.state != "started" or attempt.deadline_at <= utcnow():
        fail("ASSESSMENT_SUBMISSION_CLOSED", 409)
    version = version_for(session, attempt.version_id)
    tasks = {t["id"]: t for t in version.public_json["tasks"]}
    if set(body.responses) != set(tasks) or any(
        t["kind"] == "single_choice" and body.responses[k] not in {c["id"] for c in t["choices"]}
        for k, t in tasks.items()
    ):
        fail("INVALID_ASSESSMENT_RESPONSES", 422)
    attempt.responses_json = body.responses
    attempt.submit_key, attempt.submission_digest = body.command_key, request_digest
    attempt.submitted_at, attempt.state = utcnow(), "submitted"
    audit(session, "language.attempt_submitted", actor_id=uid, object_id=attempt.id)
    session.flush()
    return attempt


def decisions_for(session, attempt_id):
    return list(
        session.scalars(
            select(Decision).where(Decision.attempt_id == attempt_id).order_by(Decision.round)
        )
    )


def evidence_live(attempt):
    return attempt.purged_at is None and attempt.retention_until > utcnow()


def attempt_output(session, attempt, *, include_evidence=True):
    live = evidence_live(attempt)
    version = version_for(session, attempt.version_id)
    return dict(
        id=attempt.id,
        version_id=attempt.version_id,
        language=attempt.language,
        state=(
            "abandoned"
            if attempt.state == "started" and attempt.deadline_at <= utcnow()
            else attempt.state
        ),
        consent_grant_id=attempt.consent_grant_id,
        sequence=attempt.sequence,
        started_at=attempt.started_at,
        deadline_at=attempt.deadline_at,
        submitted_at=attempt.submitted_at,
        retention_until=attempt.retention_until,
        evidence_available=live,
        tasks=version.public_json["tasks"] if live and include_evidence else None,
        responses=attempt.responses_json if live and include_evidence else None,
        appeal_requested_at=attempt.appeal_requested_at,
        appeal_reason=attempt.appeal_reason if live and include_evidence else None,
        decisions=[
            dict(
                id=d.id,
                round=d.round,
                verdict=d.verdict,
                findings=d.findings_json if live and include_evidence else None,
                rationale=d.rationale if live and include_evidence else None,
                decided_at=d.decided_at,
                expires_at=d.expires_at,
                previous_decision_id=d.previous_decision_id,
            )
            for d in decisions_for(session, attempt.id)
        ],
    )


def appeal(session, uid, attempt_id, body):
    attempt = owned_attempt(session, uid, attempt_id, active=True)
    require_grant(session, attempt.profile_id, attempt.consent_grant_id)
    request_digest = digest(body.model_dump(mode="json"))
    if attempt.appeal_key:
        if attempt.appeal_key != body.command_key or attempt.appeal_digest != request_digest:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return attempt
    decisions = decisions_for(session, attempt.id)
    if (
        len(decisions) != 1
        or decisions[0].decided_at + timedelta(days=30) <= utcnow()
        or not evidence_live(attempt)
    ):
        fail("ASSESSMENT_APPEAL_CLOSED", 409)
    attempt.appeal_key, attempt.appeal_digest = body.command_key, request_digest
    attempt.appeal_reason, attempt.appeal_requested_at = body.reason, utcnow()
    audit(session, "language.appeal_requested", actor_id=uid, object_id=attempt.id)
    session.flush()
    return attempt


def review_attempt(session, settings, wid, uid, attempt_id):
    attempt = session.get(Attempt, attempt_id)
    if not attempt:
        fail()
    profile = session.get(ParticipantProfile, attempt.profile_id)
    authority(session, settings, wid, uid, attempt.language, subject_id=profile.user_id)
    attempt = session.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    session.refresh(profile)
    if profile.status != "active":
        fail("ASSESSMENT_UNAVAILABLE", 409)
    require_grant(session, profile.id, attempt.consent_grant_id)
    if uid == profile.user_id:
        fail("INDEPENDENT_REVIEW_REQUIRED", 403)
    if not evidence_live(attempt) or attempt.state not in {"submitted", "adjudicated"}:
        fail("ASSESSMENT_EVIDENCE_UNAVAILABLE", 409)
    return attempt


def adjudicate(session, settings, wid, uid, attempt_id, body):
    attempt = review_attempt(session, settings, wid, uid, attempt_id)
    decisions = decisions_for(session, attempt.id)
    request_digest = digest(body.model_dump(mode="json"))
    prior = next(
        (d for d in decisions if d.round == body.round or d.command_key == body.command_key), None
    )
    if prior:
        if prior.request_digest != request_digest or prior.reviewer_id != uid:
            fail("IDEMPOTENCY_CONFLICT", 409)
        return attempt
    if body.round == 2 and (
        not attempt.appeal_requested_at or len(decisions) != 1 or decisions[0].reviewer_id == uid
    ):
        fail("INDEPENDENT_APPEAL_REVIEW_REQUIRED", 403)
    if body.round == 1 and attempt.state != "submitted":
        fail("ASSESSMENT_DECISION_CONFLICT", 409)
    version = version_for(session, attempt.version_id)
    checked_material(session, version)
    if not attempt.responses_json:
        fail("ASSESSMENT_EVIDENCE_UNAVAILABLE", 409)
    tasks = {t["id"]: t for t in version.public_json["tasks"]}
    if set(body.findings) != set(tasks) or any(
        set(body.findings[k]) != set(t["criteria"]) for k, t in tasks.items()
    ):
        fail("INVALID_ASSESSMENT_FINDINGS", 422)
    if body.verdict == "qualified" and any(
        v != "met" for criteria in body.findings.values() for v in criteria.values()
    ):
        fail("ASSESSMENT_CRITERIA_NOT_MET", 422)
    now = utcnow()
    decision = Decision(
        attempt_id=attempt.id,
        round=body.round,
        reviewer_id=uid,
        command_key=body.command_key,
        request_digest=request_digest,
        verdict=body.verdict,
        findings_json=body.findings,
        rationale=body.rationale,
        decided_at=now,
        expires_at=now + timedelta(days=version.policy_json["validity_days"])
        if body.verdict == "qualified"
        else None,
        previous_decision_id=decisions[0].id if body.round == 2 else None,
    )
    session.add(decision)
    attempt.state = "adjudicated"
    audit(
        session,
        "language.attempt_adjudicated",
        actor_id=uid,
        object_id=attempt.id,
        verdict=body.verdict,
        round=body.round,
    )
    session.flush()
    return attempt


def current_qualifications(session, profile_id):
    profile = session.get(ParticipantProfile, profile_id)
    if not profile or profile.status != "active":
        return []
    # Pick latest adjudicated attempt first, then its latest round. An appeal to an
    # older attempt cannot resurrect it after a newer final reassessment.
    rows = session.execute(
        select(Attempt, Version, Decision)
        .select_from(Attempt)
        .join(Version, Version.id == Attempt.version_id)
        .join(Decision, Decision.attempt_id == Attempt.id)
        .where(Attempt.profile_id == profile_id)
        .distinct(Attempt.language)
        .order_by(Attempt.language, Attempt.sequence.desc(), Decision.round.desc())
    ).all()
    seen, current = set(), []
    now = utcnow()
    for attempt, version, decision in rows:
        if attempt.language in seen:
            continue
        seen.add(attempt.language)
        if (
            version.synthetic
            or decision.verdict != "qualified"
            or decision.expires_at <= now
            or attempt.state == "withdrawn"
            or not grant_live(session, profile_id, attempt.consent_grant_id)
        ):
            continue
        current.append(
            dict(
                language=attempt.language,
                assessment_id=version.id,
                assessment_version=version.version,
                decision_id=decision.id,
                decided_at=decision.decided_at.isoformat(),
                expires_at=decision.expires_at.isoformat(),
                consent_grant_id=attempt.consent_grant_id,
            )
        )
    return current


def history(session, uid, offset, limit):
    profile = profile_for(session, uid, active=False)
    attempts = list(
        session.scalars(
            select(Attempt)
            .where(Attempt.profile_id == profile.id)
            .order_by(Attempt.created_at.desc(), Attempt.id.desc())
            .offset(offset)
            .limit(limit + 1)
        )
    )
    legacy = list(
        session.scalars(
            select(Qualification)
            .where(Qualification.profile_id == profile.id)
            .order_by(Qualification.id)
            .limit(100)
        )
    )
    return dict(
        current=current_qualifications(session, profile.id),
        attempts=[attempt_output(session, a, include_evidence=False) for a in attempts[:limit]],
        legacy=[
            dict(language=q.language, passed=q.passed, expires_at=q.expires_at) for q in legacy
        ],
        next_offset=offset + limit if len(attempts) > limit else None,
    )


def queue(session, settings, wid, uid, language, offset, limit):
    authority(session, settings, wid, uid, language)
    pending_appeal = (
        select(Decision.id).where(Decision.attempt_id == Attempt.id, Decision.round == 2).exists()
    )
    withdrawn = (
        select(Consent.id)
        .where(Consent.grant_id == Attempt.consent_grant_id, Consent.decision == "withdrawn")
        .exists()
    )
    rows = list(
        session.scalars(
            select(Attempt)
            .join(ParticipantProfile, ParticipantProfile.id == Attempt.profile_id)
            .join(User, User.id == ParticipantProfile.user_id)
            .where(
                Attempt.language == language,
                Attempt.retention_until > utcnow(),
                Attempt.purged_at.is_(None),
                ParticipantProfile.status == "active",
                User.status == "active",
                ~withdrawn,
                (Attempt.state == "submitted")
                | (
                    (Attempt.state == "adjudicated")
                    & Attempt.appeal_requested_at.is_not(None)
                    & ~pending_appeal
                ),
            )
            .order_by(Attempt.submitted_at, Attempt.id)
            .offset(offset)
            .limit(limit + 1)
        )
    )
    return dict(
        items=[
            dict(
                id=a.id,
                version_id=a.version_id,
                language=a.language,
                submitted_at=a.submitted_at,
                appeal_requested_at=a.appeal_requested_at,
            )
            for a in rows[:limit]
        ],
        next_offset=offset + limit if len(rows) > limit else None,
    )
