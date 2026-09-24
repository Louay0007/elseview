"""Immutable human evaluation datasets, assignments and outcomes.

Revision ID: 013_evaluation
Revises: 012_longitudinal
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "013_evaluation"
down_revision = "012_longitudinal"
branch_labels = None
depends_on = None


def scoped():
    return [
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id", pg.UUID(as_uuid=True), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def fk(local, remote):
    return sa.ForeignKeyConstraint(
        ["workspace_id", local], [remote + ".workspace_id", remote + ".id"], ondelete="CASCADE"
    )


def upgrade():
    op.create_table(
        "evaluation_datasets",
        *scoped(),
        sa.Column("study_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("creator_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rights", pg.JSONB, nullable=False),
        sa.Column("schema", pg.JSONB, nullable=False),
        sa.UniqueConstraint("workspace_id", "id"),
        sa.UniqueConstraint("workspace_id", "study_id", "key", "version"),
        fk("study_id", "studies"),
        sa.CheckConstraint("version > 0"),
    )
    op.create_table(
        "evaluation_identities",
        *scoped(),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("partition", sa.String(16), nullable=False),
        sa.UniqueConstraint("workspace_id", "id"),
        sa.UniqueConstraint("workspace_id", "digest"),
        sa.CheckConstraint("partition IN ('train','evaluation')"),
    )
    op.create_table(
        "evaluation_items",
        *scoped(),
        sa.Column("dataset_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("source", pg.JSONB, nullable=False),
        sa.UniqueConstraint("workspace_id", "id"),
        sa.UniqueConstraint("dataset_id", "key"),
        fk("dataset_id", "evaluation_datasets"),
        sa.ForeignKeyConstraint(
            ["workspace_id", "identity_id"],
            ["evaluation_identities.workspace_id", "evaluation_identities.id"],
        ),
    )
    op.create_table(
        "evaluation_assignments",
        *scoped(),
        sa.Column("item_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("candidate_order", pg.JSONB, nullable=False),
        sa.UniqueConstraint("workspace_id", "id"),
        sa.UniqueConstraint("item_id", "reviewer_id"),
        fk("item_id", "evaluation_items"),
        sa.CheckConstraint("kind IN ('independent','adjudication')"),
    )
    op.create_table(
        "evaluation_outcomes",
        *scoped(),
        sa.Column("assignment_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("body", pg.JSONB, nullable=False),
        sa.UniqueConstraint("assignment_id"),
        fk("assignment_id", "evaluation_assignments"),
    )
    op.create_table(
        "evaluation_export_reviews",
        *scoped(),
        sa.Column("dataset_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", pg.JSONB, nullable=False),
        sa.Column("snapshot_digest", sa.String(64), nullable=False),
        sa.UniqueConstraint("dataset_id"),
        fk("dataset_id", "evaluation_datasets"),
    )
    op.execute(
        """CREATE FUNCTION evaluation_no_update() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'evaluation snapshots are immutable'; END $$"""
    )
    for table in (
        "evaluation_datasets",
        "evaluation_identities",
        "evaluation_items",
        "evaluation_assignments",
        "evaluation_outcomes",
        "evaluation_export_reviews",
    ):
        op.create_index("ix_" + table + "_workspace_id", table, ["workspace_id"])
        op.execute(
            f"CREATE TRIGGER evaluation_immutable BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION evaluation_no_update()"
        )
    op.execute(
        "CREATE UNIQUE INDEX uq_evaluation_adjudication ON evaluation_assignments(item_id) WHERE kind='adjudication'"
    )
    op.execute("""CREATE FUNCTION evaluation_human_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE n integer;
    BEGIN
      PERFORM 1 FROM evaluation_items WHERE id=NEW.item_id FOR UPDATE;
      IF NEW.kind='independent' THEN
        SELECT count(*) INTO n FROM evaluation_assignments WHERE item_id=NEW.item_id AND kind='independent';
        IF n >= 2 THEN RAISE EXCEPTION 'two independent labels maximum'; END IF;
      ELSE
        SELECT count(*) INTO n FROM evaluation_assignments a JOIN evaluation_outcomes o ON o.assignment_id=a.id WHERE a.item_id=NEW.item_id AND a.kind='independent';
        IF n != 2 THEN RAISE EXCEPTION 'adjudication requires two originals'; END IF;
      END IF;
      IF NEW.candidate_order NOT IN ('[0,1]'::jsonb,'[1,0]'::jsonb) THEN RAISE EXCEPTION 'invalid blind order'; END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER evaluation_human BEFORE INSERT ON evaluation_assignments FOR EACH ROW EXECUTE FUNCTION evaluation_human_guard()"
    )
    op.create_check_constraint(
        "evaluation_human_outcome",
        "evaluation_outcomes",
        "body->>'provenance' = 'authenticated_human'",
    )

    op.execute("""CREATE FUNCTION evaluation_delete_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE ds uuid; item uuid;
    BEGIN
      IF TG_TABLE_NAME='evaluation_identities' THEN
        RAISE EXCEPTION 'partition identities cannot be deleted';
      ELSIF TG_TABLE_NAME='evaluation_datasets' THEN ds := OLD.id;
      ELSIF TG_TABLE_NAME IN ('evaluation_items','evaluation_export_reviews') THEN ds := OLD.dataset_id;
      ELSIF TG_TABLE_NAME='evaluation_assignments' THEN
        SELECT dataset_id INTO ds FROM evaluation_items WHERE id=OLD.item_id;
      ELSE
        SELECT i.dataset_id INTO ds FROM evaluation_assignments a JOIN evaluation_items i ON i.id=a.item_id WHERE a.id=OLD.assignment_id;
      END IF;
      IF ds IS NULL OR NOT EXISTS (SELECT 1 FROM evaluation_datasets WHERE id=ds) THEN RETURN OLD; END IF;
      IF EXISTS (
        SELECT 1 FROM privacy_restrictions r WHERE r.workspace_id=OLD.workspace_id AND (
          r.subject_id IN (SELECT creator_id FROM evaluation_datasets WHERE id=ds)
          OR r.subject_id IN (SELECT a.reviewer_id FROM evaluation_assignments a JOIN evaluation_items i ON i.id=a.item_id WHERE i.dataset_id=ds)
          OR r.subject_id IN (SELECT reviewer_id FROM evaluation_export_reviews WHERE dataset_id=ds)
          OR r.subject_id IN (SELECT a.owner_id FROM assets a JOIN evaluation_items i ON i.source->'asset_ref'->>'asset_id'=a.id::text WHERE i.dataset_id=ds)
          OR r.subject_id IN (SELECT m.user_id FROM memberships m JOIN studies st ON st.owner_membership_id=m.id JOIN evaluation_datasets d ON d.study_id=st.id WHERE d.id=ds)
        )
      ) THEN RETURN OLD; END IF;
      RAISE EXCEPTION 'evaluation deletion requires privacy restriction or deleted parent';
    END $$""")
    for table in (
        "evaluation_datasets",
        "evaluation_items",
        "evaluation_assignments",
        "evaluation_outcomes",
        "evaluation_export_reviews",
        "evaluation_identities",
    ):
        op.execute(
            f"CREATE TRIGGER evaluation_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION evaluation_delete_guard()"
        )


def downgrade():
    for table in (
        "evaluation_export_reviews",
        "evaluation_outcomes",
        "evaluation_assignments",
        "evaluation_items",
        "evaluation_identities",
        "evaluation_datasets",
    ):
        op.drop_table(table)
    op.execute("DROP FUNCTION evaluation_human_guard()")
    op.execute("DROP FUNCTION evaluation_no_update()")
    op.execute("DROP FUNCTION evaluation_delete_guard()")
