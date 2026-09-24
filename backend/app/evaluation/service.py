"""Serialized human-only commands. Caller owns transaction; no provider/network integration."""

import secrets
from copy import deepcopy
from uuid import UUID

from sqlalchemy import select

from app.common.errors import DomainError
from app.common.privacy import authorized_asset, lock_workspace, require_unrestricted
from app.evaluation.models import EvaluationAssignment as Assignment
from app.evaluation.models import EvaluationDataset as Dataset
from app.evaluation.models import EvaluationExportReview as ExportReview
from app.evaluation.models import EvaluationIdentity as Identity
from app.evaluation.models import EvaluationItem as Item
from app.evaluation.models import EvaluationOutcome as Outcome
from app.evaluation.models import EvaluationRawExposure as RawExposure
from app.evaluation.validation import content_identity, digest, validate_outcome
from app.studies.service import authorize


def fail(message="Evaluation command conflicts with immutable state.", status=409):
    raise DomainError(
        "EVALUATION_CONFLICT" if status == 409 else "EVALUATION_INVALID", message, status
    )


def get(session, model, workspace_id, row_id):
    row = session.scalar(
        select(model).where(model.workspace_id == workspace_id, model.id == row_id)
    )
    if not row:
        fail("Resource not found.", 404)
    return row


def independent_eligible(session, ds, reviewer_id):
    from app.auth.models import Membership
    from app.studies.models import Study, StudyGrant

    if reviewer_id == ds.creator_id:
        return False
    member = session.scalar(
        select(Membership).where(
            Membership.workspace_id == ds.workspace_id, Membership.user_id == reviewer_id
        )
    )
    study = session.get(Study, ds.study_id)
    if not member or member.status != "active":
        return False
    if member.role in {"owner", "admin"} or member.id == study.owner_membership_id:
        return False
    grant = session.scalar(
        select(StudyGrant).where(
            StudyGrant.study_id == ds.study_id,
            StudyGrant.membership_id == member.id,
            StudyGrant.revoked_at.is_(None),
        )
    )
    if grant and "raw" in grant.capabilities:
        return False
    return not session.scalar(
        select(RawExposure.id).where(
            RawExposure.dataset_id == ds.id, RawExposure.actor_id == reviewer_id
        )
    )


def safe_independent(session, ds, assignment):
    return assignment.independence_checked and independent_eligible(
        session, ds, assignment.reviewer_id
    )


def record_raw_exposure(session, ds, actor_id):
    # Caller holds workspace lock; disclosure survives subsequent grant revocation.
    if not session.scalar(
        select(RawExposure.id).where(
            RawExposure.dataset_id == ds.id, RawExposure.actor_id == actor_id
        )
    ):
        session.add(RawExposure(workspace_id=ds.workspace_id, dataset_id=ds.id, actor_id=actor_id))
        session.flush()


def dataset_for(session, workspace_id, actor_id, dataset_id, capability="review"):
    lock_workspace(session, workspace_id)
    row = get(session, Dataset, workspace_id, dataset_id)
    authorize(session, workspace_id, actor_id, row.study_id, capability)
    require_unrestricted(session, workspace_id, row.creator_id)
    if capability in {"raw", "export"}:
        record_raw_exposure(session, row, actor_id)
    return row


def create_dataset(session, workspace_id, actor_id, body):
    lock_workspace(session, workspace_id)
    authorize(session, workspace_id, actor_id, body.study_id, "edit")
    if session.scalar(
        select(Dataset.id).where(
            Dataset.workspace_id == workspace_id,
            Dataset.study_id == body.study_id,
            Dataset.key == body.key,
            Dataset.version == body.version,
        )
    ):
        fail()
    row = Dataset(
        workspace_id=workspace_id,
        study_id=body.study_id,
        key=body.key,
        version=body.version,
        creator_id=actor_id,
        rights=body.rights.model_dump(),
        schema=body.schema_.model_dump(),
    )
    session.add(row)
    session.flush()
    identities = set()
    for item in body.items:
        source = item.source.model_dump(mode="json")
        if source.get("asset_ref"):
            asset = authorized_asset(
                session, workspace_id, actor_id, UUID(source["asset_ref"]["asset_id"])
            )
            if (
                asset.media_type != "image/png"
                or asset.purpose != "stimulus"
                or not asset.width
                or not asset.height
            ):
                fail("Ready PNG stimulus required.", 422)
            source.update(
                asset_checksum=asset.checksum, image_width=asset.width, image_height=asset.height
            )
        fingerprint = content_identity(source)
        if fingerprint in identities:
            fail("Duplicate source content.", 422)
        identities.add(fingerprint)
        identity = session.scalar(
            select(Identity).where(
                Identity.workspace_id == workspace_id, Identity.digest == fingerprint
            )
        )
        if identity and identity.partition != item.partition:
            fail("Source identity crosses train/evaluation partition.")
        if identity is None:
            identity = Identity(
                workspace_id=workspace_id, digest=fingerprint, partition=item.partition
            )
            session.add(identity)
            session.flush()
        session.add(
            Item(
                workspace_id=workspace_id,
                dataset_id=row.id,
                identity_id=identity.id,
                key=item.key,
                source=source,
            )
        )
    session.flush()
    return row


def item_assignments(session, item_id):
    return session.scalars(
        select(Assignment)
        .where(Assignment.item_id == item_id)
        .order_by(Assignment.created_at, Assignment.id)
    ).all()


def outcome_for(session, assignment):
    return session.scalar(select(Outcome).where(Outcome.assignment_id == assignment.id))


def assign(session, workspace_id, actor_id, dataset_id, body):
    ds = dataset_for(session, workspace_id, actor_id, dataset_id, "grants")
    authorize(session, workspace_id, body.reviewer_id, ds.study_id, "review")
    if body.kind == "independent" and not independent_eligible(session, ds, body.reviewer_id):
        fail("Independent review requires an unexposed, nonprivileged reviewer.", 403)
    item = get(session, Item, workspace_id, body.item_id)
    if item.dataset_id != ds.id:
        fail("Resource not found.", 404)
    if session.scalar(select(ExportReview.id).where(ExportReview.dataset_id == ds.id)):
        fail("Export reviewed; dataset collection is sealed.")
    assignments = item_assignments(session, item.id)
    if any(a.reviewer_id == body.reviewer_id for a in assignments):
        fail("Each item requires distinct reviewers, including adjudication.")
    independents = [a for a in assignments if a.kind == "independent"]
    if body.kind == "independent" and (
        len(independents) >= 2 or any(a.kind == "adjudication" for a in assignments)
    ):
        fail("Two independent labels maximum.")
    if body.kind == "adjudication" and (
        len(independents) != 2
        or any(not outcome_for(session, a) for a in independents)
        or any(a.kind == "adjudication" for a in assignments)
    ):
        fail("Two completed independent labels precede one adjudication.")
    if body.kind == "adjudication" and any(
        not safe_independent(session, ds, a) for a in independents
    ):
        fail("Independent labels are unsafe.")
    order = [0, 1]
    if secrets.randbits(1):
        order.reverse()
    row = Assignment(
        workspace_id=workspace_id,
        item_id=item.id,
        reviewer_id=body.reviewer_id,
        kind=body.kind,
        candidate_order=order,
        independence_checked=body.kind == "independent",
    )
    session.add(row)
    session.flush()
    return row


def assignment_context(session, workspace_id, actor_id, assignment_id):
    lock_workspace(session, workspace_id)
    a = get(session, Assignment, workspace_id, assignment_id)
    item = get(session, Item, workspace_id, a.item_id)
    ds = dataset_for(session, workspace_id, actor_id, item.dataset_id)
    if a.reviewer_id != actor_id:
        fail("Assignment is private to assigned reviewer.", 403)
    if a.kind == "independent" and not safe_independent(session, ds, a):
        fail("Independent assignment is unsafe or reviewer has been exposed.", 403)
    live_source(session, ds, item)
    return a, item, ds


def live_source(session, ds, item):
    if item.source.get("asset_ref"):
        asset = authorized_asset(
            session, ds.workspace_id, ds.creator_id, UUID(item.source["asset_ref"]["asset_id"])
        )
        if asset.checksum != item.source["asset_checksum"]:
            fail("Source changed.", 409)
        return asset


def remap_body(body, previous_order, current_order):
    result = deepcopy(body)

    def side(value):
        if value not in {"left", "right"}:
            return value
        index = previous_order[0 if value == "left" else 1]
        return "left" if current_order[0] == index else "right"

    result["choice"] = side(result["choice"])
    for rating in result["ratings"]:
        rating["candidate_id"] = side(rating["candidate_id"])
    return result


def projection(session, a, item, ds):
    source = {k: v for k, v in item.source.items() if k != "candidates"}
    if item.source["candidates"]:
        source["candidates"] = [
            {"id": side, "text": item.source["candidates"][index]["text"]}
            for side, index in zip(["left", "right"], a.candidate_order, strict=True)
        ]
    result = {
        "id": str(a.id),
        "dataset_id": str(ds.id),
        "item_id": str(item.id),
        "kind": a.kind,
        "schema": ds.schema,
        "source": source,
        "rights": ds.rights,
        "outcome": None,
    }
    existing = outcome_for(session, a)
    if existing:
        result["outcome"] = existing.body
    if a.kind == "adjudication":
        result["originals"] = [
            {
                "assignment_id": str(other.id),
                "body": remap_body(
                    outcome_for(session, other).body, other.candidate_order, a.candidate_order
                ),
            }
            for other in item_assignments(session, item.id)
            if other.kind == "independent" and outcome_for(session, other)
        ]
    return result


def submit(session, workspace_id, actor_id, assignment_id, body):
    a, item, ds = assignment_context(session, workspace_id, actor_id, assignment_id)
    payload = body.model_dump(mode="json")
    payload["provenance"] = "authenticated_human"
    if ds.schema["task"] == "sandbox":
        payload["transcript_provenance"] = "participant_supplied_unverified"
    existing = outcome_for(session, a)
    if existing:
        if existing.body == payload:
            return existing
        fail("Outcome already submitted with different content.")
    if session.scalar(select(ExportReview.id).where(ExportReview.dataset_id == ds.id)):
        fail("Collection sealed.")
    try:
        validate_outcome(ds.schema, item.source, body)
    except ValueError as exc:
        fail(str(exc), 422)
    row = Outcome(workspace_id=workspace_id, assignment_id=a.id, body=payload)
    session.add(row)
    session.flush()
    return row


def snapshot(session, ds):
    items = []
    for item in session.scalars(select(Item).where(Item.dataset_id == ds.id).order_by(Item.key)):
        live_source(session, ds, item)
        identity = session.get(Identity, item.identity_id)
        labels = []
        for a in item_assignments(session, item.id):
            o = outcome_for(session, a)
            if o and (a.kind != "independent" or safe_independent(session, ds, a)):
                require_unrestricted(session, ds.workspace_id, a.reviewer_id)
                labels.append(
                    {
                        "assignment_id": str(a.id),
                        "kind": a.kind,
                        "candidate_order": a.candidate_order,
                        "body": o.body,
                    }
                )
        items.append(
            {
                "id": str(item.id),
                "key": item.key,
                "source": item.source,
                "content_identity": identity.digest,
                "partition": identity.partition,
                "labels": labels,
            }
        )
    return {
        "dataset_id": str(ds.id),
        "study_id": str(ds.study_id),
        "version": ds.version,
        "schema": ds.schema,
        "rights": ds.rights,
        "items": items,
    }


def report(session, ds):
    data = snapshot(session, ds)
    choices = dict.fromkeys(["candidate_0", "candidate_1", "tie", "both_bad", "cannot_judge"], 0)
    position = {"left": 0, "right": 0}
    agreement = double = sandbox_n = success = infra = 0
    for item in data["items"]:
        labels = [x for x in item["labels"] if x["kind"] == "independent"]
        if len(labels) == 2:
            double += 1

            # Compare semantic answers, never rationale or adjudication against originals.
            def semantic(label):
                b = label["body"]
                choice = b["choice"]
                if choice in {"left", "right"}:
                    choice = label["candidate_order"][0 if choice == "left" else 1]
                return {
                    "annotations": sorted(b["annotations"], key=digest),
                    "choice": choice,
                    "ratings": sorted(
                        [
                            {
                                **r,
                                "candidate_id": str(
                                    label["candidate_order"][
                                        0 if r["candidate_id"] == "left" else 1
                                    ]
                                )
                                if r["candidate_id"] != "source"
                                else "source",
                            }
                            for r in b["ratings"]
                        ],
                        key=digest,
                    ),
                    "outcome": b["outcome"],
                }

            agreement += semantic(labels[0]) == semantic(labels[1])
        for label in labels:
            b = label["body"]
            c = b["choice"]
            if c in {"left", "right"}:
                position[c] += 1
                choices["candidate_" + str(label["candidate_order"][0 if c == "left" else 1])] += 1
            elif c:
                choices[c] += 1
        # Sandbox success is adjudicated human review only, infrastructure kept separate.
        for label in item["labels"]:
            if label["kind"] == "adjudication" and label["body"]["outcome"]:
                o = label["body"]["outcome"]
                infra += o == "infrastructure_failure"
                sandbox_n += o != "infrastructure_failure"
                success += o == "completed"
    judged = sum(choices.values()) - choices["cannot_judge"]
    return {
        "human_only": True,
        "independent_choices": choices,
        "judged_decisions": judged,
        "decisive_decisions": choices["candidate_0"] + choices["candidate_1"],
        "winner": None
        if choices["candidate_0"] == choices["candidate_1"]
        else ("candidate_0" if choices["candidate_0"] > choices["candidate_1"] else "candidate_1"),
        "position_choices": position,
        "independently_double_labeled_items": double,
        "exact_agreement_items": agreement,
        "agreement_is_truth": False,
        "sandbox_reviewed_success": success,
        "sandbox_evaluable_attempts": sandbox_n,
        "sandbox_infrastructure_failures": infra,
    }


def review_export(session, workspace_id, actor_id, dataset_id, body):
    ds = dataset_for(session, workspace_id, actor_id, dataset_id)
    authorize(session, workspace_id, actor_id, ds.study_id, "export")
    data = snapshot(session, ds)
    if not ds.rights["reuse_permission"]:
        fail("Reuse permission required.", 403)
    if not data["items"] or any(
        len([x for x in i["labels"] if x["kind"] == "independent"]) != 2
        or len([x for x in i["labels"] if x["kind"] == "adjudication"]) != 1
        for i in data["items"]
    ):
        fail("Every item requires two originals and reasoned adjudication before export.")
    if session.scalar(select(ExportReview.id).where(ExportReview.dataset_id == ds.id)):
        fail("Already reviewed.")
    row = ExportReview(
        workspace_id=workspace_id,
        dataset_id=ds.id,
        reviewer_id=actor_id,
        reason=body.reason.model_dump(),
        snapshot_digest=digest(data),
    )
    session.add(row)
    session.flush()
    record_raw_exposure(session, ds, actor_id)
    return row


def export(session, workspace_id, actor_id, dataset_id):
    ds = dataset_for(session, workspace_id, actor_id, dataset_id, "export")
    review = session.scalar(select(ExportReview).where(ExportReview.dataset_id == ds.id))
    if review:
        from app.auth.models import User

        require_unrestricted(session, workspace_id, review.reviewer_id)
        approver = session.get(User, review.reviewer_id)
        if not approver or approver.status != "active":
            fail("Export approver unavailable.", 403)
        authorize(session, workspace_id, review.reviewer_id, ds.study_id, "export")
    data = snapshot(session, ds)
    if not review or review.snapshot_digest != digest(data):
        fail("Current complete snapshot must be reviewed before export.")
    return {
        **data,
        "review": {
            "id": str(review.id),
            "reason": review.reason,
            "snapshot_digest": review.snapshot_digest,
        },
        "not_resale_permission": True,
    }
