from alembic import op

revision = "005_study_guards"
down_revision = "005_studies"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TRIGGER consent_document_no_delete BEFORE DELETE ON consent_documents
            FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
        CREATE TRIGGER retention_policy_no_delete BEFORE DELETE ON retention_policies
            FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
        CREATE FUNCTION asset_dimensions_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.state IN ('ready','blocked','purging','purged') AND
                (NEW.width, NEW.height, NEW.duration_ms) IS DISTINCT FROM
                (OLD.width, OLD.height, OLD.duration_ms) THEN
                RAISE EXCEPTION 'validated dimensions are immutable';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER asset_dimensions_immutable BEFORE UPDATE ON assets
            FOR EACH ROW EXECUTE FUNCTION asset_dimensions_frozen();
    """)


def downgrade():
    op.execute("""
        DROP TRIGGER asset_dimensions_immutable ON assets;
        DROP FUNCTION asset_dimensions_frozen();
        DROP TRIGGER retention_policy_no_delete ON retention_policies;
        DROP TRIGGER consent_document_no_delete ON consent_documents;
    """)
