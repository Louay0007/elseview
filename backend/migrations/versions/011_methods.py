"""P11 first valid click uniqueness; existing generic event/answer schema retained."""

from alembic import op

revision = "011_methods"
down_revision = "010_ai"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE OR REPLACE FUNCTION study_consent_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE doc consent_documents%ROWTYPE;
    BEGIN
      SELECT * INTO doc FROM consent_documents WHERE id = NEW.document_id;
      IF doc.purpose = 'study' THEN
        IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.study_version_id
          AND workspace_id=NEW.workspace_id AND state='published'
          AND consent_documents ->> doc.locale=doc.id::text) THEN
          RAISE EXCEPTION 'study consent version mismatch';
        END IF;
      ELSIF doc.purpose IN ('ai_processing','accessibility_context') AND NEW.study_version_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.study_version_id
          AND workspace_id=NEW.workspace_id AND state='published' AND locales ? doc.locale) THEN
          RAISE EXCEPTION 'optional consent version mismatch';
        END IF;
      ELSIF NEW.study_version_id IS NOT NULL THEN
        RAISE EXCEPTION 'consent scope mismatch';
      END IF;
      RETURN NEW;
    END $$""")
    op.drop_constraint("ck_document_purpose", "consent_documents", type_="check")
    op.create_check_constraint(
        "ck_document_purpose",
        "consent_documents",
        "purpose IN ('study','recording','ai_processing','private_panel','recontact','accessibility_context')",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_first_click_per_block ON response_events(session_id, block_key) WHERE kind = 'first_click.recorded'"
    )
    # DELETE remains available to the existing privacy erasure lifecycle.
    op.execute("""CREATE FUNCTION first_click_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF OLD.kind = 'first_click.recorded' OR NEW.kind = 'first_click.recorded' THEN
        RAISE EXCEPTION 'first click event is immutable';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER first_click_immutable_guard BEFORE UPDATE ON response_events FOR EACH ROW EXECUTE FUNCTION first_click_immutable()"
    )


def downgrade():
    op.execute("""CREATE OR REPLACE FUNCTION study_consent_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE doc consent_documents%ROWTYPE;
    BEGIN
      SELECT * INTO doc FROM consent_documents WHERE id = NEW.document_id;
      IF doc.purpose = 'study' THEN
        IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.study_version_id
          AND workspace_id=NEW.workspace_id AND state='published'
          AND consent_documents ->> doc.locale=doc.id::text) THEN
          RAISE EXCEPTION 'study consent version mismatch';
        END IF;
      ELSIF NEW.study_version_id IS NOT NULL THEN
        RAISE EXCEPTION 'consent scope mismatch';
      END IF;
      RETURN NEW;
    END $$""")
    # Retain historical receipts while enforcing the older vocabulary for new rows.
    # NOT VALID avoids deleting consent history during a schema rollback.
    op.drop_constraint("ck_document_purpose", "consent_documents", type_="check")
    op.execute(
        "ALTER TABLE consent_documents ADD CONSTRAINT ck_document_purpose CHECK "
        "(purpose IN ('study','recording','ai_processing','private_panel','recontact')) NOT VALID"
    )
    op.execute("DROP TRIGGER first_click_immutable_guard ON response_events")
    op.execute("DROP FUNCTION first_click_immutable()")
    op.execute("DROP INDEX uq_first_click_per_block")
