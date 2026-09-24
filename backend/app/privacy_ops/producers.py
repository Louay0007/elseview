"""Remaining producers; scoped erasure does not destroy another tenant's identity."""

from sqlalchemy import select

from app.auth.security import utcnow


def purge_subject(session, workspace_id, subject_id):
    from app.auth.models import AuditEvent, User, WorkspaceInvite
    from app.common.idempotency import IdempotencyRecord

    # Jobs retain UUIDs/allowlisted status only; epoch/source checks fence workers.
    # Do not mutate Job rows under workspace lock (worker lock order is reverse).
    for row in session.scalars(
        select(IdempotencyRecord).where(IdempotencyRecord.workspace_id == workspace_id)
    ):
        row.response = None
        row.expires_at = utcnow()
    for row in session.scalars(select(AuditEvent).where(AuditEvent.workspace_id == workspace_id)):
        row.details = {}
    user = session.get(User, subject_id)
    if user:
        for invite in session.scalars(
            select(WorkspaceInvite).where(
                WorkspaceInvite.workspace_id == workspace_id, WorkspaceInvite.email == user.email
            )
        ):
            invite.email = str(invite.id) + "@erased.invalid"
            invite.revoked_at = utcnow()
    # Global identity/public-panel data are outside a workspace erasure's authority.
    # Their separate account/panel lifecycle must not silently affect other tenants.
    from app.collaboration.privacy import purge_subject as purge_collaboration

    purge_collaboration(session, workspace_id, subject_id)
