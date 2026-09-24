"""Allow revision-fenced capability rotation only for unchanged active diary sessions."""

from alembic import op

revision = "027_diary_recovery"
down_revision = "026_language_assessments"
branch_labels = None
depends_on = None


def guard(allow_recovery):
    capability_guard = (
        """
        IF OLD.diary_occurrence_id IS NULL OR OLD.state <> 'active'
          OR NEW.revision <> OLD.revision + 1
          OR (to_jsonb(NEW) - 'capability_hash' - 'revision')
             IS DISTINCT FROM (to_jsonb(OLD) - 'capability_hash' - 'revision')
        THEN RAISE EXCEPTION 'invalid diary capability rotation'; END IF;
        """
        if allow_recovery
        else "RAISE EXCEPTION 'session identity is immutable';"
    )
    op.execute(f"""CREATE OR REPLACE FUNCTION collection_session_guard()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF (NEW.workspace_id, NEW.candidate_id, NEW.subject_id, NEW.version_id,
          NEW.launch_id, NEW.start_hash, NEW.locale)
        IS DISTINCT FROM
         (OLD.workspace_id, OLD.candidate_id, OLD.subject_id, OLD.version_id,
          OLD.launch_id, OLD.start_hash, OLD.locale)
        THEN RAISE EXCEPTION 'session identity is immutable'; END IF;
      IF NEW.capability_hash IS DISTINCT FROM OLD.capability_hash THEN
        {capability_guard}
      END IF;
      IF NEW.state <> OLD.state AND NOT (
        (OLD.state = 'active' AND NEW.state IN ('submitted','withdrawn','erased')) OR
        (OLD.state = 'submitted' AND NEW.state IN ('withdrawn','erased')) OR
        (OLD.state = 'withdrawn' AND NEW.state = 'erased'))
        THEN RAISE EXCEPTION 'invalid session transition'; END IF;
      IF NEW.state <> 'erased' AND NEW.assignments IS DISTINCT FROM OLD.assignments
        THEN RAISE EXCEPTION 'assignments immutable'; END IF;
      IF OLD.state = 'submitted' AND NEW.state NOT IN ('withdrawn','erased') AND
        (NEW.submitted_snapshot, NEW.submitted_at, NEW.revision) IS DISTINCT FROM
        (OLD.submitted_snapshot, OLD.submitted_at, OLD.revision)
        THEN RAISE EXCEPTION 'submission immutable'; END IF;
      RETURN NEW;
    END $$""")


def upgrade():
    guard(True)


def downgrade():
    # Keep the current capability and evidence; merely disable further rotations.
    guard(False)
