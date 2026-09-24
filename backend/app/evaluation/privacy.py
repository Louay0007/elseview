"""P13 privacy hooks; caller holds workspace privacy lock and owns transaction."""

from sqlalchemy import delete, select

from app.common.privacy_models import Asset
from app.evaluation.models import EvaluationAssignment as Assignment
from app.evaluation.models import EvaluationDataset as Dataset
from app.evaluation.models import EvaluationExportReview as ExportReview
from app.evaluation.models import EvaluationItem as Item
from app.evaluation.models import EvaluationOutcome as Outcome


def purge_subject(session, workspace_id, subject_id):
    # Removing one independent original invalidates adjudication and reviewed exports too.
    item_ids = list(
        session.scalars(
            select(Assignment.item_id).where(
                Assignment.workspace_id == workspace_id, Assignment.reviewer_id == subject_id
            )
        )
    )
    dataset_ids = list(
        session.scalars(
            select(Item.dataset_id).where(Item.workspace_id == workspace_id, Item.id.in_(item_ids))
        )
    )
    session.execute(
        delete(ExportReview).where(
            ExportReview.workspace_id == workspace_id, ExportReview.dataset_id.in_(dataset_ids)
        )
    )
    session.execute(
        delete(ExportReview).where(
            ExportReview.workspace_id == workspace_id, ExportReview.reviewer_id == subject_id
        )
    )
    result = session.execute(
        delete(Item).where(Item.workspace_id == workspace_id, Item.id.in_(item_ids))
    )
    # Asset owners may differ from the dataset creator; purge dependent source snapshots.
    assets = set(
        str(x)
        for x in session.scalars(
            select(Asset.id).where(Asset.workspace_id == workspace_id, Asset.owner_id == subject_id)
        )
    )
    asset_datasets = {
        i.dataset_id
        for i in session.scalars(select(Item).where(Item.workspace_id == workspace_id))
        if (i.source.get("asset_ref") or {}).get("asset_id") in assets
    }
    session.execute(
        delete(Dataset).where(Dataset.workspace_id == workspace_id, Dataset.id.in_(asset_datasets))
    )
    # Creator may place personal data in source material. Remove whole owned snapshots.
    owned = session.execute(
        delete(Dataset).where(
            Dataset.workspace_id == workspace_id, Dataset.creator_id == subject_id
        )
    )
    session.flush()
    return result.rowcount + owned.rowcount


def purge_studies(session, workspace_id, study_ids):
    result = session.execute(
        delete(Dataset).where(Dataset.workspace_id == workspace_id, Dataset.study_id.in_(study_ids))
    )
    session.flush()
    return result.rowcount


def subject_data(session, workspace_id, subject_id, limit=100, offset=0):
    rows = session.execute(
        select(Assignment, Outcome)
        .outerjoin(Outcome, Outcome.assignment_id == Assignment.id)
        .where(Assignment.workspace_id == workspace_id, Assignment.reviewer_id == subject_id)
        .order_by(Assignment.id)
        .offset(max(0, offset))
        .limit(min(100, max(1, limit)))
    )
    return [
        {"assignment_id": str(a.id), "kind": a.kind, "outcome": o.body if o else None}
        for a, o in rows
    ]
