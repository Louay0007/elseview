"""Immutable versioned recipe provenance; shared study/response tables remain authoritative."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "014_templates"
down_revision = "013_evaluation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "template_instances",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("study_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("template_key", sa.String(64), nullable=False),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column("recipe_hash", sa.String(64), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("recipe_snapshot", pg.JSONB, nullable=False),
        sa.Column("inputs_snapshot", pg.JSONB, nullable=False),
        sa.UniqueConstraint("workspace_id", "id"),
        sa.UniqueConstraint("version_id"),
        sa.ForeignKeyConstraint(
            ["workspace_id", "study_id"], ["studies.workspace_id", "studies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "version_id"],
            ["study_versions.workspace_id", "study_versions.id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "template_version > 0 AND recipe_hash ~ '^[0-9a-f]{64}$' AND configuration_hash ~ '^[0-9a-f]{64}$'"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(recipe_snapshot) = 'object' AND jsonb_typeof(inputs_snapshot) = 'object'"
        ),
    )
    op.create_index("ix_template_instances_workspace_id", "template_instances", ["workspace_id"])
    op.execute("""CREATE FUNCTION guard_template_instance() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'UPDATE' THEN RAISE EXCEPTION 'Template provenance is immutable'; END IF;
      IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.version_id AND workspace_id=NEW.workspace_id AND study_id=NEW.study_id AND state='draft') THEN
        RAISE EXCEPTION 'Template instance requires matching draft';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER template_instance_guard BEFORE INSERT OR UPDATE ON template_instances FOR EACH ROW EXECUTE FUNCTION guard_template_instance()"
    )


def downgrade():
    op.drop_table("template_instances")
    op.execute("DROP FUNCTION guard_template_instance()")
