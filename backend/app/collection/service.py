"""All operations participate in the caller transaction; capability secrets are never stored."""

import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.auth.security import utcnow
from app.collection.models import (
    Answer,
    AnswerRevision,
    CollectionSession,
    InteractionAttempt,
    ResponseEvent,
)
from app.common.errors import DomainError
from app.common.privacy import consent_granted, lock_workspace, require_unrestricted
from app.common.privacy_models import ConsentDocument, ConsentReceipt
from app.studies import methods
from app.studies.models import StudyVersion


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()
    ).hexdigest()


def fail(code, message, status=409):
    raise DomainError(code, message, status)


def start(session, body, actor_id, settings):
    from app.recruiting.service import bind_invitation, reserve_candidate

    invitation, candidate, launch, version = bind_invitation(
        session, settings, body.invitation_token, actor_id
    )
    if candidate.subject_id != actor_id:
        fail("INVITATION_IDENTITY_MISMATCH", "Invitation belongs to another participant.", 403)
    request_hash = digest(body.model_dump(mode="json"))
    existing = session.scalar(
        select(CollectionSession).where(
            CollectionSession.candidate_id == candidate.id,
            CollectionSession.diary_occurrence_id.is_(None),
        )
    )
    if existing:
        if existing.start_hash != request_hash:
            fail("START_CONFLICT", "Participation already started with different input.")
        return resume(session, authorize(session, existing.id, body.capability))
    document = session.get(ConsentDocument, body.document_id)
    if (
        body.locale not in version.locales
        or version.consent_documents.get(body.locale) != str(body.document_id)
        or not document
        or document.workspace_id != candidate.workspace_id
        or document.purpose != "study"
        or document.digest != body.presented_digest
    ):
        fail("CONSENT_MISMATCH", "Consent must match the published study and language.")
    require_unrestricted(session, candidate.workspace_id, candidate.subject_id)
    reservation = reserve_candidate(session, candidate.id, candidate.workspace_id)
    receipt = ConsentReceipt(
        workspace_id=candidate.workspace_id,
        subject_id=candidate.subject_id,
        document_id=document.id,
        study_version_id=version.id,
        receipt_key="collection:" + str(candidate.id),
        decision="granted",
        presented_digest=document.digest,
        created_at=utcnow(),
    )
    session.add(receipt)
    session.flush()
    assignments = {}
    for raw in version.blocks_json:
        block = methods.parse_block(raw)
        if block.type in {"survey.single", "survey.multi"} and block.config.randomize_options:
            order = [option.id for option in block.config.options]
            secrets.SystemRandom().shuffle(order)
            assignments[block.block_key] = {"order": order, "algorithm": "uniform_permutation_v1"}
        if block.type == "preference":
            order = [variant.id for variant in block.config.variants]
            secrets.SystemRandom().shuffle(order)
            assignments[block.block_key] = {
                "id": str(uuid4()),
                "order": order,
                "algorithm": "uniform_permutation_v1",
            }
    row = CollectionSession(
        workspace_id=candidate.workspace_id,
        candidate_id=candidate.id,
        subject_id=candidate.subject_id,
        version_id=version.id,
        launch_id=launch.id,
        consent_receipt_id=receipt.id,
        capability_hash=digest(body.capability),
        start_hash=request_hash,
        locale=body.locale,
        expires_at=min(reservation.expires_at, utcnow() + timedelta(days=7)),
        assignments=assignments,
    )
    session.add(row)
    invitation.redeemed_at = utcnow()
    session.flush()
    from app.billing.service import reserve_response

    reserve_response(session, row.workspace_id, row.id)
    server_event(session, row, "session.started")
    return resume(session, row)


def authorize(session, session_id, capability, *, allow_withdrawn=False):
    hint = session.get(CollectionSession, session_id)
    if not hint or not hmac.compare_digest(hint.capability_hash, digest(capability)):
        fail("INVALID_CAPABILITY", "Session capability is invalid.", 404)
    lock_workspace(session, hint.workspace_id)
    row = session.scalar(
        select(CollectionSession)
        .where(CollectionSession.id == session_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row.expires_at <= utcnow() or (row.state in {"withdrawn", "erased"} and not allow_withdrawn):
        fail("CAPABILITY_EXPIRED", "This session is no longer available.", 403)
    if not allow_withdrawn:
        if row.diary_occurrence_id is not None:
            from app.longitudinal.models import DiaryOccurrence

            occurrence = session.get(DiaryOccurrence, row.diary_occurrence_id)
            base = session.get(CollectionSession, occurrence.base_session_id)
            if (
                base.state != "submitted"
                or base.subject_id != row.subject_id
                or base.version_id != row.version_id
            ):
                fail("DIARY_SCOPE_MISMATCH", "Diary participation unavailable.", 403)
            if (
                row.state != "submitted"
                and not occurrence.opens_at <= utcnow() < occurrence.grace_at
            ):
                fail("DIARY_WINDOW_CLOSED", "Diary reporting window is closed.")
        from app.recruiting.service import validate_candidate

        validate_candidate(
            session,
            row.workspace_id,
            row.candidate_id,
            submitted=row.state == "submitted" or row.diary_occurrence_id is not None,
        )
        receipt = session.get(ConsentReceipt, row.consent_receipt_id)
        if not consent_granted(
            session, row.workspace_id, row.subject_id, "study", receipt.document_id, row.version_id
        ):
            fail("CONSENT_REQUIRED", "Study consent is no longer granted.", 403)
    return row


def definition(session, row):
    version = session.get(StudyVersion, row.version_id)
    return version, [methods.parse_block(raw) for raw in version.blocks_json]


def current_answers(session, row):
    result = {}
    for answer in session.scalars(
        select(Answer).where(Answer.session_id == row.id, Answer.active.is_(True))
    ):
        revision = session.scalar(
            select(AnswerRevision).where(
                AnswerRevision.answer_id == answer.id,
                AnswerRevision.revision == answer.current_revision,
            )
        )
        result[answer.block_key] = (answer, revision)
    return result


def path(blocks, answers):
    """Only accepted prefix plus its next block are reachable; no speculative hidden answers."""
    positions = {block.block_key: i for i, block in enumerate(blocks)}
    reachable = []
    key = blocks[0].block_key if blocks else None
    accepted = {}
    while key is not None:
        reachable.append(key)
        if key not in answers:
            return reachable, key
        accepted[key] = answers[key]
        key = methods.next_key(blocks, positions[key], accepted)
    return reachable, None


def project(row, block, attempt=None):
    result = block.model_dump(mode="json")
    result.pop("branches", None)
    result["prompt"] = result["prompt"][row.locale]
    config = result["config"]
    if block.type in {"survey.single", "survey.multi"} and block.config.randomize_options:
        order = row.assignments[block.block_key]["order"]
        options = {option["id"]: option for option in config["options"]}
        config["options"] = [options[key] for key in order]
    for option in config.get("options", []):
        option["label"] = option["label"][row.locale]
    if block.type == "preference":
        assignment = row.assignments[block.block_key]
        variants = {v["id"]: v for v in config["variants"]}
        config["variants"] = [variants[key] for key in assignment["order"]]
        for variant in config["variants"]:
            variant["label"] = variant["label"][row.locale]
        result["assignment_id"] = assignment["id"]
    if "endpoint_labels" in config:
        config["endpoint_labels"] = {k: v[row.locale] for k, v in config["endpoint_labels"].items()}
    if block.type == "five_second":
        # Stimulus appears once, only in the explicit attempt-start receipt.
        config.pop("asset_ref", None)
        result["attempt_id"] = str(attempt.id) if attempt else None
        result["attempt_state"] = attempt.state if attempt else "not_started"
    if block.type == "prototype.task":
        config["target"].pop("authorization_ref", None)
    return methods.advanced.project(result, row.locale)


def resume(session, row):
    _, blocks = definition(session, row)
    current = current_answers(session, row)
    reachable, next_block = path(blocks, {k: v[1].payload for k, v in current.items()})
    block = next((b for b in blocks if b.block_key == next_block), None)
    attempt = (
        session.scalar(
            select(InteractionAttempt).where(
                InteractionAttempt.session_id == row.id, InteractionAttempt.block_key == next_block
            )
        )
        if block
        else None
    )
    projected = project(row, block, attempt) if block and row.state == "active" else None
    if projected and block.type == "accessibility.issue":
        projected["context_consent_granted"] = consent_granted(
            session,
            row.workspace_id,
            row.subject_id,
            "accessibility_context",
            study_version_id=row.version_id,
        )
    if projected and block.type == "first_click":
        latched = first_click(session, row.id, block.block_key)
        projected["first_click"] = latched.payload["metadata"] if latched else None
    return {
        "session_id": str(row.id),
        "occurrence_id": str(row.diary_occurrence_id) if row.diary_occurrence_id else None,
        "version_id": str(row.version_id),
        "state": row.state,
        "revision": row.revision,
        "saved": True,
        "last_sequence": row.last_sequence,
        "block": projected,
        "answers": {
            key: {"revision": answer.current_revision, "answer": revision.payload}
            for key, (answer, revision) in current.items()
            if key in reachable
        },
        "complete": next_block is None,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
    }


def server_event(session, row, kind):
    session.add(
        ResponseEvent(session_id=row.id, kind=kind, provenance="server_created", payload={})
    )


def require_active(row, version_id):
    if row.version_id != version_id:
        fail("VERSION_MISMATCH", "Session is pinned to another study version.")
    if row.state != "active":
        fail("SESSION_FINAL", "Final answers cannot be changed.")


def first_click(session, session_id, block_key):
    return session.scalar(
        select(ResponseEvent).where(
            ResponseEvent.session_id == session_id,
            ResponseEvent.block_key == block_key,
            ResponseEvent.kind == "first_click.recorded",
        )
    )


def save_answer(session, row, block_key, body):
    if body.occurrence_id is not None and body.occurrence_id != row.diary_occurrence_id:
        fail("DIARY_SCOPE_MISMATCH", "Wrong diary occurrence.")
    request_hash = digest({"block_key": block_key, **body.model_dump(mode="json")})
    prior = session.scalar(
        select(AnswerRevision).where(
            AnswerRevision.session_id == row.id,
            AnswerRevision.client_event_id == body.client_event_id,
        )
    )
    if prior:
        if prior.request_hash != request_hash:
            fail("IDEMPOTENCY_CONFLICT", "Client event was used with different input.")
        return prior.receipt
    require_active(row, body.version_id or row.version_id)
    version, blocks = definition(session, row)
    current = current_answers(session, row)
    reachable, _ = path(blocks, {k: v[1].payload for k, v in current.items()})
    if block_key not in reachable:
        fail("UNREACHABLE_BLOCK", "Block is not on the accepted path.")
    answer = session.scalar(
        select(Answer).where(Answer.session_id == row.id, Answer.block_key == block_key)
    )
    if body.expected_revision != (answer.current_revision if answer else 0):
        fail("REVISION_CONFLICT", "Saved answer changed; resume before retrying.")
    block = next(b for b in blocks if b.block_key == block_key)
    attempt = session.scalar(
        select(InteractionAttempt).where(
            InteractionAttempt.session_id == row.id, InteractionAttempt.block_key == block_key
        )
    )
    try:
        payload = methods.validate_answer(
            block,
            body.answer,
            [row.locale],
            row.assignments.get(block_key, {}).get("id"),
            str(attempt.id) if attempt else None,
        )
        if block.type == "accessibility.issue" and payload["status"] == "responded":
            if any(
                i.get("context") is not None for i in payload["value"]["issues"]
            ) and not consent_granted(
                session,
                row.workspace_id,
                row.subject_id,
                "accessibility_context",
                study_version_id=row.version_id,
            ):
                raise ValueError("Separate accessibility context consent required")
        if block.type == "first_click":
            latched = first_click(session, row.id, block_key)
            if payload["status"] == "responded" and (
                not latched or payload["value"] != latched.payload["metadata"]
            ):
                raise ValueError("Answer must match the first recorded click")
            if latched and payload["status"] != "responded":
                raise ValueError("Recorded first click cannot be discarded")
        if block.type == "five_second" and payload["status"] == "responded":
            if not attempt or attempt.state == "started":
                raise ValueError("Exposure must finish first")
            value = payload["value"]
            if value["visible_ms"] != attempt.visible_ms or value["interrupted"] != (
                attempt.state == "interrupted"
            ):
                raise ValueError("Exposure timing does not match")
    except (ValueError, TypeError):
        fail("INVALID_ANSWER", "Answer does not match the block contract.", 422)
    if answer is None:
        answer = Answer(session_id=row.id, block_key=block_key, current_revision=0)
        session.add(answer)
        session.flush()
    answer.current_revision += 1
    answer.active = True
    row.revision += 1
    payloads = {k: v[1].payload for k, v in current.items()}
    payloads[block_key] = payload
    new_path, _ = path(blocks, payloads)
    invalidated = []
    for key, (downstream, _) in current.items():
        if key not in new_path:
            downstream.active = False
            invalidated.append(key)
    receipt = {
        "saved": True,
        "block_key": block_key,
        "revision": answer.current_revision,
        "session_revision": row.revision,
        "client_event_id": str(body.client_event_id),
        "invalidated": invalidated,
    }
    session.add(
        AnswerRevision(
            session_id=row.id,
            answer_id=answer.id,
            revision=answer.current_revision,
            client_event_id=body.client_event_id,
            request_hash=request_hash,
            payload=payload,
            status=payload["status"],
            value=payload["value"],
            reason_code=payload["reason_code"],
            receipt=receipt,
        )
    )
    if block.type in {"accessibility.issue", "language.review"}:
        session.add(
            ResponseEvent(
                session_id=row.id,
                block_key=block_key,
                kind="issue.submitted"
                if block.type == "accessibility.issue"
                else "language_review.submitted",
                provenance="server_created",
                payload={"answer_id": str(answer.id), "status": payload["status"]},
            )
        )
    session.flush()
    return receipt


def start_attempt(session, row, block_key):
    require_active(row, row.version_id)
    _, blocks = definition(session, row)
    current = current_answers(session, row)
    _, key = path(blocks, {k: v[1].payload for k, v in current.items()})
    if key != block_key:
        fail("UNREACHABLE_BLOCK", "Only the current block may be exposed.")
    block = next(b for b in blocks if b.block_key == key)
    if block.type != "five_second":
        fail("INVALID_ATTEMPT", "This method does not support exposure attempts.", 422)
    prior = session.scalar(
        select(InteractionAttempt).where(
            InteractionAttempt.session_id == row.id, InteractionAttempt.block_key == key
        )
    )
    if prior:
        return {
            "attempt_id": str(prior.id),
            "state": prior.state,
            "replay": True,
            "asset_ref": None,
        }
    attempt = InteractionAttempt(session_id=row.id, block_key=key)
    session.add(attempt)
    session.flush()
    return {
        "attempt_id": str(attempt.id),
        "state": attempt.state,
        "replay": False,
        "asset_ref": block.config.asset_ref.model_dump(mode="json"),
        "exposure_ms": 5000,
    }


def batch_events(session, row, body):
    require_active(row, body.version_id)
    _, blocks = definition(session, row)
    current = current_answers(session, row)
    reachable, _ = path(blocks, {k: v[1].payload for k, v in current.items()})
    accepted = []
    for item in body.events:
        block = next((b for b in blocks if b.block_key == item.block_key), None)
        if not block:
            fail("INVALID_EVENT", "Unknown event block.", 422)
        attempt = session.scalar(
            select(InteractionAttempt).where(
                InteractionAttempt.session_id == row.id,
                InteractionAttempt.block_key == item.block_key,
            )
        )
        try:
            event = methods.validate_event(block, item.event, str(attempt.id) if attempt else None)
        except (ValueError, TypeError):
            fail("INVALID_EVENT", "Event does not match the method contract.", 422)
        event_id = UUID(event["client_event_id"])
        prior = session.scalar(
            select(ResponseEvent).where(
                ResponseEvent.session_id == row.id, ResponseEvent.client_event_id == event_id
            )
        )
        if prior:
            if prior.payload != event or prior.block_key != item.block_key:
                fail("IDEMPOTENCY_CONFLICT", "Event ID already used.")
            accepted.append(str(event_id))
            continue
        if item.block_key not in reachable or event["sequence"] != row.last_sequence + 1:
            fail("EVENT_SEQUENCE_CONFLICT", "Retry from the last acknowledged sequence.")
        previous = session.scalar(
            select(ResponseEvent)
            .where(
                ResponseEvent.session_id == row.id,
                ResponseEvent.block_key == item.block_key,
                ResponseEvent.provenance == "client_observed",
            )
            .order_by(ResponseEvent.sequence.desc())
            .limit(1)
        )
        if previous and event["elapsed_ms"] < previous.payload["elapsed_ms"]:
            fail("EVENT_TIME_CONFLICT", "Client elapsed time cannot move backwards within a block.")
        if event["kind"] == "tree.node_visited":
            last_visit = session.scalar(
                select(ResponseEvent)
                .where(
                    ResponseEvent.session_id == row.id,
                    ResponseEvent.block_key == item.block_key,
                    ResponseEvent.kind == "tree.node_visited",
                )
                .order_by(ResponseEvent.sequence.desc())
                .limit(1)
            )
            node_id = event["metadata"]["node_id"]
            nodes = {node.id: node for node in block.config.nodes}
            if last_visit:
                previous_id = last_visit.payload["metadata"]["node_id"]
                adjacent = (
                    nodes[node_id].parent_id == previous_id
                    or nodes[previous_id].parent_id == node_id
                )
                if not adjacent:
                    fail(
                        "INVALID_TREE_TRANSITION", "Navigation must follow parent-child links.", 422
                    )
            elif node_id != block.config.root_id:
                fail("INVALID_TREE_TRANSITION", "Navigation must start at the root.", 422)
        if event["kind"] == "first_click.recorded" and item.block_key in current:
            fail("FIRST_CLICK_FINAL", "This task has already been answered.")
        if event["kind"] == "first_click.recorded" and first_click(session, row.id, item.block_key):
            fail("FIRST_CLICK_FINAL", "The first valid click is already recorded.")
        if block.type == "five_second":
            if not attempt:
                fail("INVALID_ATTEMPT", "Start an exposure attempt first.")
            if event["kind"] in {"exposure.ended", "exposure.interrupted", "visibility.changed"}:
                interrupted = (
                    event["kind"] == "exposure.interrupted"
                    or event["metadata"].get("visibility") == "hidden"
                )
                if interrupted or event["kind"] == "exposure.ended":
                    if attempt.state != "started":
                        fail("ATTEMPT_FINAL", "Exposure timing is already final.")
                    attempt.visible_ms = event["elapsed_ms"]
                    attempt.state = "interrupted" if interrupted else "completed"
                    attempt.ended_at = utcnow()
            elif event["kind"] == "exposure.started" and attempt.state != "started":
                fail("ATTEMPT_FINAL", "Exposure cannot restart.")
        session.add(
            ResponseEvent(
                session_id=row.id,
                block_key=item.block_key,
                client_event_id=event_id,
                sequence=event["sequence"],
                kind=event["kind"],
                provenance="client_observed",
                payload=event,
            )
        )
        row.last_sequence = event["sequence"]
        session.flush()
        accepted.append(str(event_id))
    return {"saved": True, "accepted": accepted, "last_sequence": row.last_sequence}


def submit(session, row, body):
    if body.occurrence_id is not None and body.occurrence_id != row.diary_occurrence_id:
        fail("DIARY_SCOPE_MISMATCH", "Wrong diary occurrence.")
    if body.version_id != row.version_id:
        fail("VERSION_MISMATCH", "Wrong study version.")
    if row.state == "submitted":
        return {
            "submitted": True,
            "session_id": str(row.id),
            "quality_job_id": str(row.quality_job_id),
        }
    require_active(row, body.version_id)
    if body.expected_revision != row.revision:
        fail("REVISION_CONFLICT", "Resume before submitting changed responses.")
    _, blocks = definition(session, row)
    current = current_answers(session, row)
    reachable, next_block = path(blocks, {k: v[1].payload for k, v in current.items()})
    if next_block is not None:
        fail("INCOMPLETE_SESSION", "Answer or explicitly skip every reachable block.")
    from app.recruiting.service import consume_reservation

    if row.diary_occurrence_id is None:
        consume_reservation(session, row.workspace_id, row.candidate_id)
    row.submitted_snapshot = {
        key: {"answer_id": str(current[key][0].id), "revision": current[key][0].current_revision}
        for key in reachable
    }
    for key in reachable:
        current[key][0].final_revision = current[key][0].current_revision
    session.flush()
    row.state, row.submitted_at = "submitted", utcnow()
    session.flush()
    from app.billing.service import consume_response

    consume_response(session, row.workspace_id, row.id)
    from app.collection.quality import enqueue_quality

    row.quality_job_id = enqueue_quality(session, row).id
    server_event(session, row, "session.submitted")
    session.flush()
    return {"submitted": True, "session_id": str(row.id), "quality_job_id": str(row.quality_job_id)}
