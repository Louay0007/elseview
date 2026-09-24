"""Durable global account erasure receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "022_account_erasure"
down_revision = "021_privacy_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "privacy_account_erasures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("request_key", sa.Uuid(), nullable=False, unique=True),
        sa.Column("capability_hash", sa.String(64), nullable=False),
        sa.Column("workspace_ids", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("state IN ('pending','completed')", name="ck_account_erasure_state"),
    )


def downgrade():
    op.drop_table("privacy_account_erasures")
