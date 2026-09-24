"""Durable narrowly scoped privacy replay decisions."""

import sqlalchemy as sa
from alembic import op

revision = "019_privacy_events"
down_revision = "018_billing_allowances"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "privacy_restore_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("workspace_id", "action", "resource_id"),
        sa.CheckConstraint(
            "action IN ('session_withdraw','session_delete','asset_delete','ai_delete','snapshot_delete','export_delete','share_revoke','consent_revoke')",
            name="ck_restore_event_action",
        ),
    )
    op.create_index(
        "ix_privacy_restore_events_workspace_id", "privacy_restore_events", ["workspace_id"]
    )


def downgrade():
    op.drop_table("privacy_restore_events")
