"""P01 synthetic metadata only. No research/auth tables until their phases."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_metadata",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("is_synthetic", sa.Boolean, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("is_synthetic IS TRUE", name="ck_metadata_synthetic"),
    )


def downgrade():
    op.drop_table("app_metadata")
