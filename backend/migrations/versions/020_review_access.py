"""First raw disclosure history and fail-closed legacy independence."""

import sqlalchemy as sa
from alembic import op

revision = "020_review_access"
down_revision = "019_privacy_events"
branch_labels = None
depends_on = None


def upgrade():
    # No retrospective attestation: pre-migration assignments remain unchecked.
    op.add_column(
        "evaluation_assignments",
        sa.Column("independence_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "evaluation_raw_exposures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.UniqueConstraint("dataset_id", "actor_id"),
        sa.ForeignKeyConstraint(
            ["workspace_id", "dataset_id"],
            ["evaluation_datasets.workspace_id", "evaluation_datasets.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_evaluation_raw_exposures_workspace_id", "evaluation_raw_exposures", ["workspace_id"]
    )
    op.execute(
        "CREATE TRIGGER evaluation_immutable BEFORE UPDATE ON evaluation_raw_exposures "
        "FOR EACH ROW EXECUTE FUNCTION evaluation_no_update()"
    )


def downgrade():
    op.drop_table("evaluation_raw_exposures")
    op.drop_column("evaluation_assignments", "independence_checked")
