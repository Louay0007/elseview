"""Versioned, bounded single-use stimulus preparation."""

import sqlalchemy as sa
from alembic import op

revision = "024_exposure_preparation"
down_revision = "023_report_formats"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "interaction_attempts",
        sa.Column("protocol_version", sa.Integer(), nullable=False, server_default="1"),
    )
    for name in ("prepared_at", "preparation_expires_at", "asset_claimed_at"):
        op.add_column("interaction_attempts", sa.Column(name, sa.DateTime(timezone=True)))
    op.add_column("interaction_attempts", sa.Column("preparation_hash", sa.String(64)))
    op.alter_column("interaction_attempts", "started_at", nullable=True, server_default=None)
    op.create_check_constraint(
        "ck_attempt_protocol", "interaction_attempts", "protocol_version IN (1, 2)"
    )


def downgrade():
    # Checking under ALTER TABLE's lock also prevents a concurrent V2 insert.
    # Retained V2 attempts (including final facts) cannot lose their provenance.
    op.create_check_constraint(
        "ck_attempt_rollback_requires_legacy", "interaction_attempts", "protocol_version = 1"
    )
    op.alter_column(
        "interaction_attempts", "started_at", nullable=False, server_default=sa.text("now()")
    )
    op.drop_constraint("ck_attempt_protocol", "interaction_attempts", type_="check")
    for name in ("preparation_hash", "asset_claimed_at", "preparation_expires_at", "prepared_at"):
        op.drop_column("interaction_attempts", name)
    op.drop_constraint("ck_attempt_rollback_requires_legacy", "interaction_attempts", type_="check")
    op.drop_column("interaction_attempts", "protocol_version")
