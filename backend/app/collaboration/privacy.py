"""No webhook payload is retained. Erasure removes authored raw comments too."""

from sqlalchemy import delete, or_, select, update

from app.auth.security import utcnow

from .models import (
    APIKey,
    Integration,
    NotificationPreference,
    ReportComment,
    ReportGrant,
    TemplateGrant,
    WebhookDelivery,
)


def invalidate_subject(session, workspace_id, subject_id):
    session.execute(
        update(APIKey)
        .where(APIKey.workspace_id == workspace_id, APIKey.user_id == subject_id)
        .values(revoked_at=utcnow())
    )
    for model in (ReportGrant, TemplateGrant):
        session.execute(
            update(model)
            .where(
                model.workspace_id == workspace_id,
                or_(model.issuer_id == subject_id, model.recipient_id == subject_id),
            )
            .values(revoked=True)
        )
    session.execute(
        update(Integration)
        .where(Integration.workspace_id == workspace_id, Integration.creator_id == subject_id)
        .values(enabled=False)
    )
    session.execute(
        update(WebhookDelivery)
        .where(
            WebhookDelivery.workspace_id == workspace_id, WebhookDelivery.requester_id == subject_id
        )
        .values(state="cancelled")
    )
    # Comments can quote any subject; remove all workspace comments on restriction.
    session.execute(
        update(ReportComment)
        .where(ReportComment.workspace_id == workspace_id)
        .values(restricted=True)
    )


def purge_subject(session, workspace_id, subject_id):
    invalidate_subject(session, workspace_id, subject_id)
    session.execute(delete(ReportComment).where(ReportComment.workspace_id == workspace_id))
    for model, col in (
        (APIKey, APIKey.user_id),
        (NotificationPreference, NotificationPreference.user_id),
    ):
        session.execute(delete(model).where(model.workspace_id == workspace_id, col == subject_id))
    for model in (ReportGrant, TemplateGrant):
        session.execute(
            delete(model).where(
                model.workspace_id == workspace_id,
                or_(model.issuer_id == subject_id, model.recipient_id == subject_id),
            )
        )
    ids = select(Integration.id).where(
        Integration.workspace_id == workspace_id, Integration.creator_id == subject_id
    )
    session.execute(
        delete(WebhookDelivery).where(
            WebhookDelivery.workspace_id == workspace_id,
            or_(
                WebhookDelivery.requester_id == subject_id, WebhookDelivery.integration_id.in_(ids)
            ),
        )
    )
    session.execute(
        delete(Integration).where(
            Integration.workspace_id == workspace_id, Integration.creator_id == subject_id
        )
    )
