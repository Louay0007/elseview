"""Auth-scoped durable mail; no recipient or raw capability storage."""

import sqlalchemy as sa
from alembic import op

revision = "025_auth_delivery"
down_revision = "024_exposure_preparation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_id", sa.Uuid(), sa.ForeignKey("one_time_tokens.id", ondelete="CASCADE")),
        sa.Column(
            "invite_id", sa.Uuid(), sa.ForeignKey("workspace_invites.id", ondelete="CASCADE")
        ),
        sa.Column("purpose", sa.String(24), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(32)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "run_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("lease_token", sa.Uuid()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('pending','dispatching','sent','failed','uncertain','cancelled')",
            name="ck_auth_delivery_state",
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="ck_auth_delivery_attempts"),
        sa.CheckConstraint(
            "(purpose IN ('verify','reset') AND token_id IS NOT NULL AND invite_id IS NULL) OR (purpose = 'workspace_invite' AND invite_id IS NOT NULL AND token_id IS NULL)",
            name="ck_auth_delivery_scope",
        ),
    )
    for column in ("state", "token_id", "invite_id"):
        op.create_index("ix_auth_deliveries_" + column, "auth_deliveries", [column])


def downgrade():
    op.drop_table("auth_deliveries")
