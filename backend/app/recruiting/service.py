"""Recruitment transactions. Callers own commit; workspace -> launch -> cells lock order.

Contact import intentionally retains only workspace HMACs, not recoverable addresses.
Delivery is manual in development. Reward values are development commitments, not payouts.
"""

import hashlib
import hmac
import json
from datetime import timedelta

from sqlalchemy import delete, func, select

from app.auth.models import Membership, User
from app.auth.security import new_secret, token_hash, utcnow
from app.auth.service import require_workspace
from app.common.errors import DomainError
from app.common.privacy import get_scoped, lock_workspace, require_unrestricted
from app.common.privacy_models import ConsentDocument
from app.recruiting.models import (
    Candidate,
    Invitation,
    PanelConsent,
    ParticipantProfile,
    PrivateContact,
    PrivateContactConsent,
    Qualification,
    QuotaCell,
    RecruitmentConfig,
    Reservation,
    ReservationCell,
    ScreenerResult,
)
from app.recruiting.schemas import Attributes
from app.studies.models import Launch, Study, StudyVersion
from app.studies.service import authorize

PANEL_DOCUMENT = (
    "Elseview development panel opt-in v1: optional research invitations; withdraw at any time."
)
PANEL_DIGEST = hashlib.sha256(PANEL_DOCUMENT.encode()).hexdigest()


def fail(code="NOT_FOUND", status=404):
    raise DomainError(code, "Recruitment request cannot be completed.", status)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def matches(attributes, filters):
    age = attributes.get("age")
    if filters.get("min_age") is not None and (age is None or age < filters["min_age"]):
        return False
    if filters.get("max_age") is not None and (age is None or age > filters["max_age"]):
        return False
    if filters.get("device") and filters["device"] not in attributes.get("devices", []):
        return False
    if filters.get("language") and filters["language"] not in attributes.get("languages", []):
        return False
    if filters.get("verified_language") and filters["verified_language"] not in attributes.get(
        "verified_languages", []
    ):
        return False
    return True


def panel_update(session, user_id, body):
    if body.presented_digest != PANEL_DIGEST or body.document_version != "1":
        fail("CONSENT_DOCUMENT_MISMATCH", 409)
    session.scalar(select(User).where(User.id == user_id).with_for_update())
    profile = session.scalar(
        select(ParticipantProfile).where(ParticipantProfile.user_id == user_id)
    )
    if profile is None:
        if body.decision != "granted":
            fail("OPT_IN_REQUIRED", 409)
        profile = ParticipantProfile(user_id=user_id)
        session.add(profile)
        session.flush()
    previous = session.scalar(
        select(PanelConsent).where(
            PanelConsent.profile_id == profile.id, PanelConsent.receipt_key == body.receipt_key
        )
    )
    if previous:
        if previous.request_digest != digest(body.model_dump()):
            fail("IDEMPOTENCY_CONFLICT", 409)
        return profile
    profile.status = "active" if body.decision == "granted" else "withdrawn"
    profile.attributes_json = body.attributes.model_dump() if body.decision == "granted" else {}
    session.add(
        PanelConsent(
            profile_id=profile.id,
            decision=body.decision,
            document_version="1",
            document_digest=PANEL_DIGEST,
            request_digest=digest(body.model_dump()),
            receipt_key=body.receipt_key,
        )
    )
    session.flush()
    return profile


def contact_hash(secret, workspace_id, email):
    email = email.strip().casefold()
    if (
        len(email) > 254
        or email.count("@") != 1
        or any(c.isspace() for c in email)
        or "." not in email.rsplit("@", 1)[1]
    ):
        fail("INVALID_CONTACT", 422)
    return hmac.new(
        secret.encode(), f"private-contact:{workspace_id}:{email}".encode(), hashlib.sha256
    ).hexdigest()


def import_contacts(session, settings, workspace_id, user_id, body):
    lock_workspace(session, workspace_id)
    require_workspace(session, user_id, workspace_id, "privacy.manage")
    doc = get_scoped(session, ConsentDocument, workspace_id, body.document_id)
    if doc.purpose != "private_panel":
        fail("CONSENT_PURPOSE", 422)
    if body.retention_until.tzinfo is None or body.retention_until <= utcnow():
        fail("INVALID_RETENTION", 422)
    if set(body.mapping) - {"email", "age", "devices", "languages"} or "email" not in body.mapping:
        fail("INVALID_MAPPING", 422)
    planned = []
    seen = set()
    duplicates = 0
    for row in body.rows:
        if body.mapping["email"] not in row:
            fail("INVALID_MAPPING", 422)
        hashed = contact_hash(
            settings.secret_key.get_secret_value(), workspace_id, row[body.mapping["email"]]
        )
        attrs = {}
        try:
            for key, column in body.mapping.items():
                if key == "email" or not row.get(column):
                    continue
                attrs[key] = (
                    int(row[column])
                    if key == "age"
                    else [x.strip() for x in row[column].split(",")]
                )
            attrs = Attributes.model_validate(attrs).model_dump()
        except (ValueError, TypeError):
            fail("INVALID_ATTRIBUTES", 422)
        existing = session.scalar(
            select(PrivateContact.id).where(
                PrivateContact.workspace_id == workspace_id,
                PrivateContact.contact_lookup_hash == hashed,
            )
        )
        if existing or hashed in seen:
            duplicates += 1
            if body.duplicate_policy == "reject":
                fail("DUPLICATE_CONTACT", 409)
            continue
        seen.add(hashed)
        planned.append((hashed, attrs))
    ids = []
    if not body.preview:
        for hashed, attrs in planned:
            contact = PrivateContact(
                workspace_id=workspace_id,
                contact_lookup_hash=hashed,
                attributes_json=attrs,
                source=body.source,
                retention_until=body.retention_until,
            )
            session.add(contact)
            session.flush()
            ids.append(str(contact.id))
            session.add(
                PrivateContactConsent(
                    workspace_id=workspace_id,
                    contact_id=contact.id,
                    document_id=doc.id,
                    decision="granted",
                    receipt_key="import:" + str(contact.id),
                )
            )
    return {
        "preview": body.preview,
        "accepted": len(planned),
        "duplicates": duplicates,
        "contact_ids": ids,
        "delivery": "manual_capability_only",
    }


def lock_launch(session, workspace_id, launch_id):
    workspace = lock_workspace(session, workspace_id)
    if workspace.status != "active":
        fail("LAUNCH_UNAVAILABLE", 409)
    launch = session.scalar(
        select(Launch)
        .where(Launch.workspace_id == workspace_id, Launch.id == launch_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if launch is None:
        fail()
    if launch.state != "ready":
        fail("LAUNCH_UNAVAILABLE", 409)
    version = get_scoped(session, StudyVersion, workspace_id, launch.version_id)
    if version.state != "published":
        fail("LAUNCH_UNAVAILABLE", 409)
    study = get_scoped(session, Study, workspace_id, version.study_id)
    owner = get_scoped(session, Membership, workspace_id, study.owner_membership_id)
    owner_user = session.scalar(
        select(User)
        .where(User.id == owner.user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    session.refresh(study)
    session.refresh(owner)
    if (
        study.status != "ready"
        or owner.status != "active"
        or not owner_user
        or owner_user.status != "active"
        or not owner_user.verified_at
    ):
        fail("LAUNCH_UNAVAILABLE", 409)
    require_unrestricted(session, workspace_id, owner.user_id)
    return launch, version


def manage_launch(session, workspace_id, user_id, launch_id):
    launch, version = lock_launch(session, workspace_id, launch_id)
    authorize(session, workspace_id, user_id, version.study_id, "publish")
    return launch, version


def config_for(session, workspace_id, launch_id):
    config = session.scalar(
        select(RecruitmentConfig).where(
            RecruitmentConfig.workspace_id == workspace_id, RecruitmentConfig.launch_id == launch_id
        )
    )
    if config is None:
        fail("RECRUITMENT_NOT_CONFIGURED", 409)
    return config


def configure(session, workspace_id, user_id, launch_id, body):
    manage_launch(session, workspace_id, user_id, launch_id)
    if session.scalar(select(RecruitmentConfig.id).where(RecruitmentConfig.launch_id == launch_id)):
        fail("CONFIG_FROZEN", 409)
    config = RecruitmentConfig(
        workspace_id=workspace_id,
        launch_id=launch_id,
        capacity=body.capacity,
        budget_millimes=body.budget_millimes,
        reward_millimes=body.reward_millimes,
        hold_seconds=body.hold_seconds,
        filters_json=body.filters.model_dump(),
        screener_json={k: v.model_dump() for k, v in body.screeners.items()},
        screening_policy=body.screening_policy,
    )
    session.add(config)
    for cell in body.quotas:
        session.add(
            QuotaCell(
                workspace_id=workspace_id,
                launch_id=launch_id,
                capacity=cell.capacity,
                filters_json=cell.filters.model_dump(),
            )
        )
    session.flush()
    return config


def source_attributes(session, workspace_id, kind, source_id):
    if kind == "public":
        profile = session.get(ParticipantProfile, source_id)
        if not profile or profile.status != "active":
            fail("SOURCE_UNAVAILABLE", 409)
        user = session.scalar(select(User).where(User.id == profile.user_id).with_for_update())
        session.refresh(profile)
        if profile.status != "active":
            fail("SOURCE_UNAVAILABLE", 409)
        if not user or user.status != "active" or not user.verified_at:
            fail("SOURCE_UNAVAILABLE", 409)
        receipt = session.scalar(
            select(PanelConsent)
            .where(PanelConsent.profile_id == profile.id)
            .order_by(PanelConsent.created_at.desc(), PanelConsent.id.desc())
            .limit(1)
        )
        if not receipt or receipt.decision != "granted":
            fail("SOURCE_UNAVAILABLE", 409)
        attrs = dict(profile.attributes_json)
        attrs["verified_languages"] = list(
            session.scalars(
                select(Qualification.language).where(
                    Qualification.profile_id == profile.id,
                    Qualification.passed.is_(True),
                    Qualification.expires_at > utcnow(),
                )
            )
        )
        return attrs, profile.user_id
    if kind != "private":
        fail("INVALID_SOURCE", 422)
    contact = get_scoped(session, PrivateContact, workspace_id, source_id)
    receipt = session.scalar(
        select(PrivateContactConsent)
        .where(
            PrivateContactConsent.workspace_id == workspace_id,
            PrivateContactConsent.contact_id == contact.id,
        )
        .order_by(PrivateContactConsent.created_at.desc(), PrivateContactConsent.id.desc())
        .limit(1)
    )
    if (
        contact.status != "active"
        or contact.retention_until <= utcnow()
        or not receipt
        or receipt.decision != "granted"
    ):
        fail("SOURCE_UNAVAILABLE", 409)
    return dict(contact.attributes_json), None


def issue_invitation(session, workspace_id, user_id, launch_id, body):
    manage_launch(session, workspace_id, user_id, launch_id)
    config = config_for(session, workspace_id, launch_id)
    attrs, subject = source_attributes(session, workspace_id, body.source_kind, body.source_id)
    if subject:
        require_unrestricted(session, workspace_id, subject)
    if not matches(attrs, config.filters_json):
        fail("INELIGIBLE", 409)
    candidate = session.scalar(
        select(Candidate).where(
            Candidate.workspace_id == workspace_id,
            Candidate.launch_id == launch_id,
            Candidate.source_kind == body.source_kind,
            Candidate.source_id == body.source_id,
        )
    )
    if candidate:
        fail("ALREADY_INVITED", 409)
    if subject and session.scalar(
        select(Candidate.id).where(
            Candidate.workspace_id == workspace_id,
            Candidate.launch_id == launch_id,
            Candidate.subject_id == subject,
        )
    ):
        fail("ALREADY_PARTICIPATING", 409)
    candidate = Candidate(
        workspace_id=workspace_id,
        launch_id=launch_id,
        subject_id=subject,
        source_kind=body.source_kind,
        source_id=body.source_id,
        attributes_json=attrs,
        status="invited" if config.screener_json else "eligible",
    )
    session.add(candidate)
    session.flush()
    raw = new_secret()
    invite = Invitation(
        workspace_id=workspace_id,
        candidate_id=candidate.id,
        token_hash=token_hash(raw),
        expires_at=utcnow() + timedelta(seconds=body.expires_seconds),
    )
    session.add(invite)
    session.flush()
    return invite, candidate, raw


def validate_source(session, candidate):
    if candidate.subject_id:
        subject = session.scalar(
            select(User)
            .where(User.id == candidate.subject_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not subject or subject.status != "active" or not subject.verified_at:
            fail("SOURCE_UNAVAILABLE", 409)
        require_unrestricted(session, candidate.workspace_id, candidate.subject_id)
    if candidate.status == "withdrawn" or candidate.source_id is None:
        fail("PARTICIPANT_WITHDRAWN", 403)
    source_attributes(session, candidate.workspace_id, candidate.source_kind, candidate.source_id)


def resolve_invitation(session, raw_token, *, redeem=False):
    if not raw_token or len(raw_token) > 512:
        fail("INVALID_INVITATION", 401)
    invite = session.scalar(
        select(Invitation).where(Invitation.token_hash == token_hash(raw_token))
    )
    if not invite:
        fail("INVALID_INVITATION", 401)
    candidate = get_scoped(session, Candidate, invite.workspace_id, invite.candidate_id)
    launch, version = lock_launch(session, candidate.workspace_id, candidate.launch_id)
    session.refresh(invite)
    session.refresh(candidate)
    if invite.revoked_at or invite.expires_at <= utcnow() or (redeem and invite.redeemed_at):
        fail("INVALID_INVITATION", 401)
    validate_source(session, candidate)
    if redeem:
        invite.redeemed_at = utcnow()
    return invite, candidate, launch, version


def screen(session, raw_token, answers):
    invite, candidate, launch, version = resolve_invitation(session, raw_token)
    if invite.redeemed_at:
        fail("INVITATION_USED", 409)
    config = config_for(session, candidate.workspace_id, launch.id)
    rules = config.screener_json
    if set(answers) != set(rules) or any(
        value not in rules[key]["options"] for key, value in answers.items()
    ):
        fail("INVALID_SCREENER", 422)
    prior = session.scalar(
        select(ScreenerResult).where(ScreenerResult.candidate_id == candidate.id)
    )
    request_digest = digest(answers)
    if prior:
        if prior.request_digest != request_digest:
            fail("SCREENER_FROZEN", 409)
        return prior.eligible
    eligible = all(answers[key] in rule["eligible_options"] for key, rule in rules.items())
    session.add(
        ScreenerResult(
            workspace_id=candidate.workspace_id,
            candidate_id=candidate.id,
            request_digest=request_digest,
            rules_digest=digest(rules),
            eligible=eligible,
        )
    )
    candidate.status = "eligible" if eligible else "screened_out"
    session.flush()
    return eligible


def expire_holds(session, workspace_id, launch_id):
    for hold in session.scalars(
        select(Reservation)
        .where(
            Reservation.workspace_id == workspace_id,
            Reservation.launch_id == launch_id,
            Reservation.state == "held",
            Reservation.expires_at <= utcnow(),
        )
        .with_for_update()
    ):
        hold.state = "expired"
    session.flush()


def reserve_candidate(session, candidate_id, workspace_id):
    candidate = get_scoped(session, Candidate, workspace_id, candidate_id)
    lock_launch(session, workspace_id, candidate.launch_id)
    session.refresh(candidate)
    validate_source(session, candidate)
    if candidate.subject_id is None:
        fail("VERIFIED_IDENTITY_REQUIRED", 403)
    if candidate.status != "eligible":
        fail("NOT_ELIGIBLE", 409)
    config = config_for(session, workspace_id, candidate.launch_id)
    cells = list(
        session.scalars(
            select(QuotaCell)
            .where(
                QuotaCell.workspace_id == workspace_id, QuotaCell.launch_id == candidate.launch_id
            )
            .order_by(QuotaCell.id)
            .with_for_update()
        )
    )
    expire_holds(session, workspace_id, candidate.launch_id)
    old = session.scalar(
        select(Reservation).where(
            Reservation.workspace_id == workspace_id, Reservation.candidate_id == candidate.id
        )
    )
    if old:
        if old.state in ("held", "consumed"):
            return old
        fail("RESERVATION_CLOSED", 409)
    active = list(
        session.scalars(
            select(Reservation).where(
                Reservation.workspace_id == workspace_id,
                Reservation.launch_id == candidate.launch_id,
                Reservation.state.in_(["held", "consumed"]),
            )
        )
    )
    if len(active) >= config.capacity:
        fail("CAPACITY_FULL", 409)
    if sum(r.reward_millimes for r in active) + config.reward_millimes > config.budget_millimes:
        fail("BUDGET_EXHAUSTED", 409)
    applicable = [c for c in cells if matches(candidate.attributes_json, c.filters_json)]
    for cell in applicable:
        used = session.scalar(
            select(func.count())
            .select_from(ReservationCell)
            .join(Reservation, Reservation.id == ReservationCell.reservation_id)
            .where(ReservationCell.cell_id == cell.id, Reservation.state.in_(["held", "consumed"]))
        )
        if used >= cell.capacity:
            fail("QUOTA_FULL", 409)
    reservation = Reservation(
        workspace_id=workspace_id,
        launch_id=candidate.launch_id,
        candidate_id=candidate.id,
        reward_millimes=config.reward_millimes,
        expires_at=utcnow() + timedelta(seconds=config.hold_seconds),
    )
    session.add(reservation)
    session.flush()
    for cell in applicable:
        session.add(
            ReservationCell(
                workspace_id=workspace_id,
                launch_id=candidate.launch_id,
                reservation_id=reservation.id,
                cell_id=cell.id,
            )
        )
    session.flush()
    return reservation


def validate_candidate(session, workspace_id, candidate_id, *, submitted=False):
    candidate = get_scoped(session, Candidate, workspace_id, candidate_id)
    launch, version = lock_launch(session, workspace_id, candidate.launch_id)
    session.refresh(candidate)
    validate_source(session, candidate)
    reservation = session.scalar(
        select(Reservation)
        .where(Reservation.workspace_id == workspace_id, Reservation.candidate_id == candidate_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not reservation or candidate.status != "eligible":
        fail("RESERVATION_REQUIRED", 409)
    if reservation.state == "consumed" and submitted:
        return candidate, launch, version, reservation
    if reservation.state != "held" or reservation.expires_at <= utcnow():
        fail("RESERVATION_EXPIRED", 409)
    return candidate, launch, version, reservation


def consume_reservation(session, workspace_id, candidate_id):
    *_, reservation = validate_candidate(session, workspace_id, candidate_id, submitted=True)
    reservation.state = "consumed"
    session.flush()
    return reservation


def access_summary(session, workspace_id, subject_id):
    candidates = list(
        session.scalars(
            select(Candidate).where(
                Candidate.workspace_id == workspace_id, Candidate.subject_id == subject_id
            )
        )
    )
    return {
        "candidates": [
            {"id": str(c.id), "launch_id": str(c.launch_id), "status": c.status} for c in candidates
        ]
    }


def erase_subject(session, workspace_id, subject_id):
    # Called under the privacy workspace lock. Preserve anonymous capacity/reward accounting.
    candidates = list(
        session.scalars(
            select(Candidate).where(
                Candidate.workspace_id == workspace_id, Candidate.subject_id == subject_id
            )
        )
    )
    for candidate in candidates:
        if candidate.source_kind == "private" and candidate.source_id:
            contact = get_scoped(session, PrivateContact, workspace_id, candidate.source_id)
            contact.attributes_json = {}
            contact.source = "erased"
            contact.status = "withdrawn"
        candidate.attributes_json = {}
        candidate.source_id = None
        candidate.status = "withdrawn"
        for invite in session.scalars(
            select(Invitation).where(Invitation.candidate_id == candidate.id)
        ):
            invite.revoked_at = utcnow()
        for hold in session.scalars(
            select(Reservation).where(
                Reservation.candidate_id == candidate.id, Reservation.state == "held"
            )
        ):
            hold.state = "released"
        session.execute(delete(ScreenerResult).where(ScreenerResult.candidate_id == candidate.id))
    contact = session.scalar(
        select(PrivateContact).where(
            PrivateContact.workspace_id == workspace_id, PrivateContact.id == subject_id
        )
    )
    if contact:
        contact.attributes_json = {}
        contact.source = "erased"
        contact.status = "withdrawn"
    return {"candidates_erased": len(candidates)}


def bind_invitation(session, settings, raw_token, user_id):
    invite, candidate, launch, version = resolve_invitation(session, raw_token)
    user = session.get(User, user_id)
    if not user or user.status != "active" or not user.verified_at:
        fail("VERIFIED_IDENTITY_REQUIRED", 403)
    if candidate.subject_id is not None and candidate.subject_id != user_id:
        fail("INVITATION_IDENTITY_MISMATCH", 403)
    if candidate.source_kind == "private":
        contact = get_scoped(session, PrivateContact, candidate.workspace_id, candidate.source_id)
        expected = contact_hash(
            settings.secret_key.get_secret_value(), candidate.workspace_id, user.email
        )
        if not hmac.compare_digest(contact.contact_lookup_hash, expected):
            fail("INVITATION_IDENTITY_MISMATCH", 403)
    require_unrestricted(session, candidate.workspace_id, user_id)
    duplicate = session.scalar(
        select(Candidate.id).where(
            Candidate.workspace_id == candidate.workspace_id,
            Candidate.launch_id == candidate.launch_id,
            Candidate.subject_id == user_id,
            Candidate.id != candidate.id,
        )
    )
    if duplicate:
        fail("ALREADY_PARTICIPATING", 409)
    candidate.subject_id = user_id
    session.flush()
    return invite, candidate, launch, version


purge_subject = erase_subject


def erase_launches(session, workspace_id, launch_ids):
    candidate_ids = select(Candidate.id).where(
        Candidate.workspace_id == workspace_id, Candidate.launch_id.in_(launch_ids)
    )
    for model in (Invitation, ScreenerResult):
        session.execute(
            delete(model).where(
                model.workspace_id == workspace_id, model.candidate_id.in_(candidate_ids)
            )
        )
    for model in (ReservationCell, Reservation, QuotaCell, Candidate, RecruitmentConfig):
        session.execute(
            delete(model).where(model.workspace_id == workspace_id, model.launch_id.in_(launch_ids))
        )


def release_reservation(session, workspace_id, candidate_id):
    candidate = get_scoped(session, Candidate, workspace_id, candidate_id)
    lock_workspace(session, workspace_id)
    reservation = session.scalar(
        select(Reservation)
        .where(Reservation.workspace_id == workspace_id, Reservation.candidate_id == candidate.id)
        .with_for_update()
    )
    if reservation and reservation.state == "held":
        reservation.state = "released"
    session.flush()
    return reservation


ASSESSMENTS = {
    "fr": [
        ("Choisissez le pluriel de « cheval ».", ["chevals", "chevaux"], "chevaux"),
        ("Complétez : Nous ___ ici.", ["sommes", "sont"], "sommes"),
    ],
    "en": [
        ("Choose the plural of child.", ["childs", "children"], "children"),
        ("Complete: They ___ here.", ["is", "are"], "are"),
    ],
    "ar": [
        ("اختر جمع كتاب", ["كتب", "كاتب"], "كتب"),
        ("أكمل: نحن ___ هنا", ["موجودون", "موجود"], "موجودون"),
    ],
}


def assess_language(session, user_id, body):
    session.scalar(select(User).where(User.id == user_id).with_for_update())
    profile = session.scalar(
        select(ParticipantProfile).where(ParticipantProfile.user_id == user_id)
    )
    if not profile or profile.status != "active":
        fail("OPT_IN_REQUIRED", 409)
    existing = session.scalar(
        select(Qualification).where(
            Qualification.profile_id == profile.id,
            Qualification.language == body.language,
            Qualification.assessment_version == body.assessment_version,
        )
    )
    if existing:
        fail("ASSESSMENT_ALREADY_TAKEN", 409)
    questions = ASSESSMENTS[body.language]
    if any(answer not in q[1] for answer, q in zip(body.answers, questions, strict=True)):
        fail("INVALID_ANSWER", 422)
    result = Qualification(
        profile_id=profile.id,
        language=body.language,
        assessment_version=body.assessment_version,
        passed=all(answer == q[2] for answer, q in zip(body.answers, questions, strict=True)),
        expires_at=utcnow() + timedelta(days=90),
    )
    session.add(result)
    session.flush()
    return result


def suppress_contact(session, workspace_id, contact_id):
    lock_workspace(session, workspace_id)
    contact = get_scoped(session, PrivateContact, workspace_id, contact_id)
    contact.status = "suppressed"
    for candidate in session.scalars(
        select(Candidate).where(
            Candidate.workspace_id == workspace_id,
            Candidate.source_kind == "private",
            Candidate.source_id == contact.id,
        )
    ):
        candidate.status = "withdrawn"
        release_reservation(session, workspace_id, candidate.id)
    return contact


def recruit_public(session, workspace_id, user_id, launch_id, body):
    """Select a bounded panel window internally; never return global directory identifiers."""
    from app.recruiting.schemas import InviteBody

    manage_launch(session, workspace_id, user_id, launch_id)
    config = config_for(session, workspace_id, launch_id)
    profiles = list(
        session.scalars(
            select(ParticipantProfile)
            .where(ParticipantProfile.status == "active")
            .order_by(ParticipantProfile.user_id)
            .limit(500)
        )
    )
    results = []
    for profile in profiles:
        if len(results) >= body.count:
            break
        prior = session.scalar(
            select(Candidate.id).where(
                Candidate.workspace_id == workspace_id,
                Candidate.launch_id == launch_id,
                Candidate.subject_id == profile.user_id,
            )
        )
        if prior:
            continue
        try:
            attrs, subject = source_attributes(session, workspace_id, "public", profile.id)
            require_unrestricted(session, workspace_id, subject)
        except DomainError:
            continue
        if not matches(attrs, config.filters_json) or not matches(attrs, body.filters.model_dump()):
            continue
        invitation, candidate, raw = issue_invitation(
            session,
            workspace_id,
            user_id,
            launch_id,
            InviteBody(
                source_kind="public", source_id=profile.id, expires_seconds=body.expires_seconds
            ),
        )
        results.append(
            {
                "candidate_id": str(candidate.id),
                "invitation_id": str(invitation.id),
                "invitation_token": raw,
                "expires_at": invitation.expires_at,
            }
        )
    return {
        "items": results,
        "issued": len(results),
        "availability_guaranteed": False,
        "delivery": "manual",
    }
