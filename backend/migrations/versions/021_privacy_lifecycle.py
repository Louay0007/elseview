"""Private-contact holds and scoped lifecycle replay identifiers."""

import sqlalchemy as sa
from alembic import op

revision = "021_privacy_lifecycle"
down_revision = "020_review_access"
branch_labels = None
depends_on = None

OLD = "'session_withdraw','session_delete','asset_delete','ai_delete','snapshot_delete','export_delete','share_revoke','consent_revoke'"
NEW = (
    OLD
    + ",'dataset_delete','study_delete','recording_delete','contact_delete','candidate_delete','comment_delete','idempotency_scrub','audit_scrub'"
)


ORIGINAL_EVALUATION_GUARD = "CREATE OR REPLACE FUNCTION evaluation_delete_guard() RETURNS trigger LANGUAGE plpgsql AS $$\n    DECLARE ds uuid; item uuid;\n    BEGIN\n      IF TG_TABLE_NAME='evaluation_identities' THEN\n        RAISE EXCEPTION 'partition identities cannot be deleted';\n      ELSIF TG_TABLE_NAME='evaluation_datasets' THEN ds := OLD.id;\n      ELSIF TG_TABLE_NAME IN ('evaluation_items','evaluation_export_reviews') THEN ds := OLD.dataset_id;\n      ELSIF TG_TABLE_NAME='evaluation_assignments' THEN\n        SELECT dataset_id INTO ds FROM evaluation_items WHERE id=OLD.item_id;\n      ELSE\n        SELECT i.dataset_id INTO ds FROM evaluation_assignments a JOIN evaluation_items i ON i.id=a.item_id WHERE a.id=OLD.assignment_id;\n      END IF;\n      IF ds IS NULL OR NOT EXISTS (SELECT 1 FROM evaluation_datasets WHERE id=ds) THEN RETURN OLD; END IF;\n      IF EXISTS (\n        SELECT 1 FROM privacy_restrictions r WHERE r.workspace_id=OLD.workspace_id AND (\n          r.subject_id IN (SELECT creator_id FROM evaluation_datasets WHERE id=ds)\n          OR r.subject_id IN (SELECT a.reviewer_id FROM evaluation_assignments a JOIN evaluation_items i ON i.id=a.item_id WHERE i.dataset_id=ds)\n          OR r.subject_id IN (SELECT reviewer_id FROM evaluation_export_reviews WHERE dataset_id=ds)\n          OR r.subject_id IN (SELECT a.owner_id FROM assets a JOIN evaluation_items i ON i.source->'asset_ref'->>'asset_id'=a.id::text WHERE i.dataset_id=ds)\n          OR r.subject_id IN (SELECT m.user_id FROM memberships m JOIN studies st ON st.owner_membership_id=m.id JOIN evaluation_datasets d ON d.study_id=st.id WHERE d.id=ds)\n        )\n      ) THEN RETURN OLD; END IF;\n      RAISE EXCEPTION 'evaluation deletion requires privacy restriction or deleted parent';\n    END $$"

LIFECYCLE_EVALUATION_GUARD = "CREATE OR REPLACE FUNCTION evaluation_delete_guard() RETURNS trigger LANGUAGE plpgsql AS $$\n    DECLARE ds uuid; item uuid;\n    BEGIN\n      IF TG_TABLE_NAME='evaluation_identities' THEN\n        RAISE EXCEPTION 'partition identities cannot be deleted';\n      ELSIF TG_TABLE_NAME='evaluation_datasets' THEN ds := OLD.id;\n      ELSIF TG_TABLE_NAME IN ('evaluation_items','evaluation_export_reviews') THEN ds := OLD.dataset_id;\n      ELSIF TG_TABLE_NAME='evaluation_assignments' THEN\n        SELECT dataset_id INTO ds FROM evaluation_items WHERE id=OLD.item_id;\n      ELSE\n        SELECT i.dataset_id INTO ds FROM evaluation_assignments a JOIN evaluation_items i ON i.id=a.item_id WHERE a.id=OLD.assignment_id;\n      END IF;\n      IF ds IS NULL OR NOT EXISTS (SELECT 1 FROM evaluation_datasets WHERE id=ds) THEN RETURN OLD; END IF;\n      IF EXISTS (SELECT 1 FROM privacy_restore_events e WHERE e.workspace_id=OLD.workspace_id\n        AND ((e.action='dataset_delete' AND e.resource_id=ds) OR\n          (e.action='study_delete' AND e.resource_id IN (SELECT study_id FROM evaluation_datasets WHERE id=ds))))\n        THEN RETURN OLD; END IF;\n      IF EXISTS (\n        SELECT 1 FROM privacy_restrictions r WHERE r.workspace_id=OLD.workspace_id AND (\n          r.subject_id IN (SELECT creator_id FROM evaluation_datasets WHERE id=ds)\n          OR r.subject_id IN (SELECT a.reviewer_id FROM evaluation_assignments a JOIN evaluation_items i ON i.id=a.item_id WHERE i.dataset_id=ds)\n          OR r.subject_id IN (SELECT reviewer_id FROM evaluation_export_reviews WHERE dataset_id=ds)\n          OR r.subject_id IN (SELECT a.owner_id FROM assets a JOIN evaluation_items i ON i.source->'asset_ref'->>'asset_id'=a.id::text WHERE i.dataset_id=ds)\n          OR r.subject_id IN (SELECT m.user_id FROM memberships m JOIN studies st ON st.owner_membership_id=m.id JOIN evaluation_datasets d ON d.study_id=st.id WHERE d.id=ds)\n        )\n      ) THEN RETURN OLD; END IF;\n      RAISE EXCEPTION 'evaluation deletion requires privacy restriction or deleted parent';\n    END $$"


ORIGINAL_STUDY_GUARD = "CREATE OR REPLACE FUNCTION study_version_frozen() RETURNS trigger LANGUAGE plpgsql AS $$\n        BEGIN\n            IF TG_OP = 'DELETE' AND EXISTS (\n                SELECT 1 FROM studies s JOIN memberships m ON m.id = s.owner_membership_id\n                JOIN privacy_restrictions p ON p.workspace_id = s.workspace_id AND p.subject_id = m.user_id\n                WHERE s.id = OLD.study_id\n            ) THEN RETURN OLD; END IF;\n            IF OLD.state = 'published' THEN RAISE EXCEPTION 'published version is immutable'; END IF;\n            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;\n            IF (NEW.study_id, NEW.workspace_id, NEW.number) IS DISTINCT FROM (OLD.study_id, OLD.workspace_id, OLD.number) THEN\n                RAISE EXCEPTION 'version identity is immutable';\n            END IF;\n            RETURN NEW;\n        END $$;"
LIFECYCLE_STUDY_GUARD = "CREATE OR REPLACE FUNCTION study_version_frozen() RETURNS trigger LANGUAGE plpgsql AS $$\n        BEGIN\n            IF TG_OP = 'DELETE' AND EXISTS (SELECT 1 FROM privacy_restore_events e\n                WHERE e.workspace_id=OLD.workspace_id AND e.action='study_delete'\n                AND e.resource_id=OLD.study_id) THEN RETURN OLD; END IF;\n            IF TG_OP = 'DELETE' AND EXISTS (\n                SELECT 1 FROM studies s JOIN memberships m ON m.id = s.owner_membership_id\n                JOIN privacy_restrictions p ON p.workspace_id = s.workspace_id AND p.subject_id = m.user_id\n                WHERE s.id = OLD.study_id\n            ) THEN RETURN OLD; END IF;\n            IF OLD.state = 'published' THEN RAISE EXCEPTION 'published version is immutable'; END IF;\n            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;\n            IF (NEW.study_id, NEW.workspace_id, NEW.number) IS DISTINCT FROM (OLD.study_id, OLD.workspace_id, OLD.number) THEN\n                RAISE EXCEPTION 'version identity is immutable';\n            END IF;\n            RETURN NEW;\n        END $$;"


# Only a content-emptying update is permitted; all identifiers/hashes stay fixed.
_SCRUB_GATE = """EXISTS (SELECT 1 FROM privacy_restore_events e WHERE e.workspace_id=OLD.workspace_id
    AND e.action='study_delete' AND e.resource_id=OLD.study_id)
    AND NOT EXISTS (SELECT 1 FROM privacy_legal_holds h WHERE h.workspace_id=OLD.workspace_id AND h.released_at IS NULL)
    AND NOT EXISTS (SELECT 1 FROM privacy_contact_holds h WHERE h.workspace_id=OLD.workspace_id AND h.released_at IS NULL)"""
LIFECYCLE_STUDY_GUARD = LIFECYCLE_STUDY_GUARD.replace(
    "        BEGIN",
    """        BEGIN
    IF TG_OP='UPDATE' AND """
    + _SCRUB_GATE
    + """
      AND NEW.blocks_json='[]'::jsonb AND NEW.rules_json='{}'::jsonb
      AND NEW.consent_documents='{}'::jsonb AND NEW.locales='[]'::jsonb
      AND (to_jsonb(NEW) - ARRAY['blocks_json','rules_json','consent_documents','locales'])
        = (to_jsonb(OLD) - ARRAY['blocks_json','rules_json','consent_documents','locales'])
      THEN RETURN NEW; END IF;
""",
    1,
)

ORIGINAL_TEMPLATE_GUARD = "CREATE OR REPLACE FUNCTION guard_template_instance() RETURNS trigger LANGUAGE plpgsql AS $$\n    BEGIN\n      IF TG_OP = 'UPDATE' THEN RAISE EXCEPTION 'Template provenance is immutable'; END IF;\n      IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.version_id AND workspace_id=NEW.workspace_id AND study_id=NEW.study_id AND state='draft') THEN\n        RAISE EXCEPTION 'Template instance requires matching draft';\n      END IF;\n      RETURN NEW;\n    END $$"
LIFECYCLE_TEMPLATE_GUARD = ORIGINAL_TEMPLATE_GUARD.replace(
    "    BEGIN",
    """    BEGIN
    IF TG_OP='UPDATE' AND """
    + _SCRUB_GATE
    + """
      AND NEW.recipe_snapshot='{}'::jsonb AND NEW.inputs_snapshot='{}'::jsonb
      AND (to_jsonb(NEW) - ARRAY['recipe_snapshot','inputs_snapshot'])
        = (to_jsonb(OLD) - ARRAY['recipe_snapshot','inputs_snapshot'])
      THEN RETURN NEW; END IF;
""",
    1,
)


# A minimized draft is retired as well: the ordinary draft-edit exception cannot
# reintroduce personal content after its identifier-only erasure event.
LIFECYCLE_STUDY_GUARD = LIFECYCLE_STUDY_GUARD.replace(
    "            IF OLD.state = 'published'",
    """            IF TG_OP='UPDATE' AND EXISTS (SELECT 1 FROM privacy_restore_events e
      WHERE e.workspace_id=OLD.workspace_id AND e.action='study_delete' AND e.resource_id=OLD.study_id)
      THEN RAISE EXCEPTION 'Erased study version is retired'; END IF;
            IF OLD.state = 'published'""",
    1,
)
LIFECYCLE_TEMPLATE_GUARD = LIFECYCLE_TEMPLATE_GUARD.replace(
    "      IF TG_OP = 'UPDATE'",
    """      IF TG_OP='INSERT' AND EXISTS (SELECT 1 FROM privacy_restore_events e
      WHERE e.workspace_id=NEW.workspace_id AND e.action='study_delete' AND e.resource_id=NEW.study_id)
      THEN RAISE EXCEPTION 'Erased template source is retired'; END IF;
      IF TG_OP = 'UPDATE'""",
    1,
)


def upgrade():
    op.execute(LIFECYCLE_STUDY_GUARD)
    op.execute(LIFECYCLE_TEMPLATE_GUARD)
    op.execute(LIFECYCLE_EVALUATION_GUARD)
    op.drop_constraint("ck_restore_event_action", "privacy_restore_events", type_="check")
    op.create_check_constraint(
        "ck_restore_event_action", "privacy_restore_events", f"action IN ({NEW})"
    )
    op.create_table(
        "privacy_contact_holds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("review_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("length(reason_code) BETWEEN 1 AND 64", name="ck_contact_hold_reason"),
    )
    op.create_index(
        "ix_privacy_contact_holds_workspace_id", "privacy_contact_holds", ["workspace_id"]
    )
    op.create_index("ix_privacy_contact_holds_contact_id", "privacy_contact_holds", ["contact_id"])


def downgrade():
    op.execute(ORIGINAL_STUDY_GUARD)
    op.execute(ORIGINAL_TEMPLATE_GUARD)
    op.execute(ORIGINAL_EVALUATION_GUARD)
    # Do not discard durable erasure events just to permit schema downgrade.
    op.drop_constraint("ck_restore_event_action", "privacy_restore_events", type_="check")
    # Retain newer replay decisions on downgrade. Old writers cannot add them;
    # old replay rejects the unsupported manifest instead of silently forgetting.
    op.execute(
        f"ALTER TABLE privacy_restore_events ADD CONSTRAINT ck_restore_event_action CHECK (action IN ({OLD})) NOT VALID"
    )
    op.drop_table("privacy_contact_holds")
