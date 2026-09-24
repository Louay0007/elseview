"""Source-linked recruitment and explicitly opted-in reminder delivery."""

import sqlalchemy as sa
from alembic import op

revision = "028_notification_delivery"
down_revision = "027_diary_recovery"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notification_preferences",
        sa.Column("email_reminders", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "invitations",
        sa.Column("issued_by", sa.Uuid(), sa.ForeignKey("users.id", name="fk_invitation_issuer")),
    )
    op.create_unique_constraint("uq_invitation_workspace_id", "invitations", ["workspace_id", "id"])
    op.create_unique_constraint(
        "uq_notification_workspace_id", "notifications", ["workspace_id", "id"]
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "recipient_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "issuer_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("invitation_id", sa.Uuid()),
        sa.Column("notification_id", sa.Uuid()),
        sa.Column("occurrence_id", sa.Uuid()),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("privacy_epoch", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(32)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "invitation_id"],
            ["invitations.workspace_id", "invitations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "notification_id"],
            ["notifications.workspace_id", "notifications.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "occurrence_id"],
            ["diary_occurrences.workspace_id", "diary_occurrences.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "state IN ('pending','dispatching','sent','failed','uncertain','cancelled')",
            name="ck_notification_delivery_state",
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_notification_delivery_attempts"),
        sa.CheckConstraint(
            "(purpose = 'recruitment_invite' AND invitation_id IS NOT NULL AND notification_id IS NULL AND occurrence_id IS NULL) OR "
            "(purpose = 'interview_reminder' AND notification_id IS NOT NULL AND invitation_id IS NULL AND occurrence_id IS NULL) OR "
            "(purpose = 'diary_reminder' AND occurrence_id IS NOT NULL AND invitation_id IS NULL AND notification_id IS NULL)",
            name="ck_notification_delivery_source",
        ),
    )
    for column in (
        "workspace_id",
        "recipient_id",
        "issuer_id",
        "invitation_id",
        "notification_id",
        "occurrence_id",
        "state",
    ):
        op.create_index("ix_notification_deliveries_" + column, "notification_deliveries", [column])


def downgrade():
    op.drop_table("notification_deliveries")
    op.drop_constraint("uq_notification_workspace_id", "notifications", type_="unique")
    op.drop_constraint("uq_invitation_workspace_id", "invitations", type_="unique")
    op.drop_column("invitations", "issued_by")
    op.drop_column("notification_preferences", "email_reminders")
