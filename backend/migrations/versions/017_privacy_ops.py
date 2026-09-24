"""Reviewed privacy operations and restore tombstones."""

import sqlalchemy as sa
from alembic import op

revision = "017_privacy_ops"
down_revision = "016_collaboration"
branch_labels = None
depends_on = None


def upgrade():
    for name, columns, constraints in [
        (
            "privacy_legal_holds",
            [
                sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("purpose", sa.String(32), nullable=False),
                sa.Column("reason", sa.Text(), nullable=False),
                sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("review_deadline", sa.DateTime(timezone=True), nullable=False),
                sa.Column("released_at", sa.DateTime(timezone=True)),
            ],
            [sa.CheckConstraint("length(reason) BETWEEN 1 AND 2000", name="ck_hold_reason")],
        ),
        (
            "privacy_reviewed_retention",
            [
                sa.Column("purpose", sa.String(32), nullable=False),
                sa.Column("version", sa.Integer(), nullable=False),
                sa.Column("days", sa.Integer(), nullable=False),
                sa.Column("reason", sa.Text(), nullable=False),
                sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("review_deadline", sa.DateTime(timezone=True), nullable=False),
            ],
            [
                sa.UniqueConstraint("workspace_id", "purpose", "version"),
                sa.CheckConstraint(
                    "days BETWEEN 1 AND 3650 AND version > 0", name="ck_reviewed_retention_days"
                ),
            ],
        ),
        (
            "privacy_tombstones",
            [
                sa.Column("subject_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("purpose", sa.String(32), nullable=False),
            ],
            [
                sa.UniqueConstraint("workspace_id", "subject_id", "purpose"),
                sa.CheckConstraint(
                    "purpose IN ('erasure','restriction')", name="ck_tombstone_purpose"
                ),
            ],
        ),
    ]:
        op.create_table(
            name,
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            *columns,
            *constraints,
        )
        op.create_index("ix_" + name + "_workspace_id", name, ["workspace_id"])
        if name != "privacy_reviewed_retention":
            op.create_index("ix_" + name + "_subject_id", name, ["subject_id"])


def downgrade():
    for name in ["privacy_tombstones", "privacy_reviewed_retention", "privacy_legal_holds"]:
        op.drop_table(name)
