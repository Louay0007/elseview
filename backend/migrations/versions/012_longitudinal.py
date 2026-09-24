"""P12 immutable diary series, scheduling and consent-bound recordings."""

from alembic import op

revision = "012_longitudinal"
down_revision = "011_methods"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE schedule_slots (\n\tversion_id UUID NOT NULL, \n\thost_id UUID NOT NULL, \n\tstarts_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tends_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tcapacity INTEGER NOT NULL, \n\tjoin_url TEXT NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tFOREIGN KEY(workspace_id, version_id) REFERENCES study_versions (workspace_id, id), \n\tCHECK (ends_at > starts_at AND capacity BETWEEN 1 AND 100), \n\tFOREIGN KEY(host_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)"
    )
    op.execute("CREATE INDEX ix_schedule_slots_workspace_id ON schedule_slots (workspace_id)")
    op.execute(
        "CREATE TABLE bookings (\n\tslot_id UUID NOT NULL, \n\tsubject_id UUID NOT NULL, \n\trequest_key UUID NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tattendance VARCHAR(16) NOT NULL, \n\tattendance_note TEXT, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (subject_id, request_key), \n\tFOREIGN KEY(workspace_id, slot_id) REFERENCES schedule_slots (workspace_id, id), \n\tCHECK (state IN ('booked','cancelled')), \n\tCHECK (attendance IN ('unknown','attended','absent')), \n\tFOREIGN KEY(subject_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)"
    )
    op.execute("CREATE INDEX ix_bookings_workspace_id ON bookings (workspace_id)")
    op.execute(
        "ALTER TABLE bookings ADD COLUMN attendance_actor_id UUID, ADD COLUMN attendance_at TIMESTAMPTZ, ADD CONSTRAINT fk_booking_attendance_actor FOREIGN KEY (workspace_id, attendance_actor_id) REFERENCES memberships(workspace_id,user_id), ADD CONSTRAINT ck_booking_attendance_attribution CHECK ((attendance = 'unknown' AND attendance_actor_id IS NULL AND attendance_at IS NULL) OR (attendance <> 'unknown' AND attendance_actor_id IS NOT NULL AND attendance_at IS NOT NULL AND attendance_note IS NOT NULL))"
    )
    op.execute(
        "CREATE TABLE diary_occurrences (\n\tbase_session_id UUID NOT NULL, \n\tordinal INTEGER NOT NULL, \n\topens_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdue_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tgrace_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\ttimezone VARCHAR(64) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (base_session_id, ordinal), \n\tFOREIGN KEY(workspace_id, base_session_id) REFERENCES collection_sessions (workspace_id, id) ON DELETE CASCADE, \n\tCHECK (ordinal >= 0 AND opens_at < due_at AND due_at <= grace_at), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)"
    )
    op.execute("CREATE INDEX ix_diary_occurrences_workspace_id ON diary_occurrences (workspace_id)")
    op.execute(
        "CREATE TABLE notifications (\n\tbooking_id UUID NOT NULL, \n\tbooking_revision INTEGER NOT NULL, \n\tjob_id UUID, \n\tdelivered_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (booking_id, booking_revision), \n\tFOREIGN KEY(booking_id) REFERENCES bookings (id), \n\tFOREIGN KEY(job_id) REFERENCES jobs (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)"
    )
    op.execute("CREATE INDEX ix_notifications_workspace_id ON notifications (workspace_id)")
    op.execute(
        "CREATE TABLE recordings (\n\tasset_id UUID NOT NULL, \n\tversion_id UUID NOT NULL, \n\tsubject_id UUID NOT NULL, \n\tconsent_receipt_id UUID NOT NULL, \n\tduration_ms INTEGER NOT NULL, \n\ttranscript_hash VARCHAR(64), \n\trevoked BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (asset_id), \n\tFOREIGN KEY(workspace_id, asset_id) REFERENCES assets (workspace_id, id), \n\tFOREIGN KEY(workspace_id, version_id) REFERENCES study_versions (workspace_id, id), \n\tFOREIGN KEY(subject_id) REFERENCES users (id), \n\tFOREIGN KEY(consent_receipt_id) REFERENCES consent_receipts (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)"
    )
    op.execute("CREATE INDEX ix_recordings_workspace_id ON recordings (workspace_id)")
    op.execute(
        "CREATE TABLE transcript_segments (\n\trecording_id UUID NOT NULL, \n\tordinal INTEGER NOT NULL, \n\tstart_ms INTEGER NOT NULL, \n\tend_ms INTEGER NOT NULL, \n\tspeaker VARCHAR(64) NOT NULL, \n\ttext TEXT NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (recording_id, ordinal), \n\tFOREIGN KEY(workspace_id, recording_id) REFERENCES recordings (workspace_id, id), \n\tCHECK (start_ms >= 0 AND end_ms > start_ms AND ordinal >= 0), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)"
    )
    op.execute(
        "CREATE INDEX ix_transcript_segments_workspace_id ON transcript_segments (workspace_id)"
    )
    op.execute("ALTER TABLE collection_sessions DROP CONSTRAINT uq_collection_candidate")
    op.execute(
        "ALTER TABLE collection_sessions ADD COLUMN diary_occurrence_id UUID REFERENCES diary_occurrences(id) ON DELETE CASCADE"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_collection_candidate_base ON collection_sessions(candidate_id) WHERE diary_occurrence_id IS NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_collection_diary_occurrence ON collection_sessions(diary_occurrence_id) WHERE diary_occurrence_id IS NOT NULL"
    )
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
      ELSIF doc.purpose IN ('ai_processing','accessibility_context','recording') AND NEW.study_version_id IS NOT NULL THEN
        IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.study_version_id
          AND workspace_id=NEW.workspace_id AND state='published' AND locales ? doc.locale) THEN
          RAISE EXCEPTION 'optional consent version mismatch';
        END IF;
      ELSIF NEW.study_version_id IS NOT NULL THEN RAISE EXCEPTION 'consent scope mismatch';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE FUNCTION diary_session_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.diary_occurrence_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM diary_occurrences o JOIN collection_sessions b ON b.id=o.base_session_id
        WHERE o.id=NEW.diary_occurrence_id AND o.workspace_id=NEW.workspace_id
          AND b.candidate_id=NEW.candidate_id AND b.subject_id=NEW.subject_id
          AND b.version_id=NEW.version_id AND b.launch_id=NEW.launch_id
          AND b.diary_occurrence_id IS NULL
      ) THEN RAISE EXCEPTION 'diary session scope mismatch'; END IF;
      IF TG_OP='UPDATE' AND NEW.diary_occurrence_id IS NOT NULL AND OLD.diary_occurrence_id IS DISTINCT FROM NEW.diary_occurrence_id
        THEN RAISE EXCEPTION 'diary occurrence immutable'; END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER diary_session_scope BEFORE INSERT OR UPDATE ON collection_sessions FOR EACH ROW EXECUTE FUNCTION diary_session_scope()"
    )
    op.execute("""CREATE FUNCTION longitudinal_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'longitudinal evidence immutable'; END $$""")
    for table in ("diary_occurrences", "transcript_segments"):
        op.execute(
            f"CREATE TRIGGER longitudinal_immutable BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION longitudinal_immutable()"
        )
    op.execute("""CREATE FUNCTION recording_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM consent_receipts r JOIN consent_documents d ON d.id=r.document_id
        WHERE r.id=NEW.consent_receipt_id AND r.workspace_id=NEW.workspace_id
        AND r.subject_id=NEW.subject_id AND r.study_version_id=NEW.version_id
        AND r.decision='granted' AND d.purpose='recording') THEN
        RAISE EXCEPTION 'recording consent scope mismatch'; END IF;
      IF NEW.duration_ms <= 0 THEN RAISE EXCEPTION 'invalid recording duration'; END IF;
      IF TG_OP='UPDATE' AND (OLD.asset_id<>NEW.asset_id OR OLD.version_id<>NEW.version_id
        OR OLD.subject_id<>NEW.subject_id OR OLD.consent_receipt_id<>NEW.consent_receipt_id
        OR OLD.duration_ms<>NEW.duration_ms OR (OLD.transcript_hash IS NOT NULL
        AND OLD.transcript_hash IS DISTINCT FROM NEW.transcript_hash)) THEN
        RAISE EXCEPTION 'recording binding immutable'; END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER recording_scope BEFORE INSERT OR UPDATE ON recordings FOR EACH ROW EXECUTE FUNCTION recording_scope()"
    )


def downgrade():
    op.execute("DROP TRIGGER recording_scope ON recordings")
    op.execute("DROP FUNCTION recording_scope()")
    for table in ("diary_occurrences", "transcript_segments"):
        op.execute(f"DROP TRIGGER longitudinal_immutable ON {table}")
    op.execute("DROP FUNCTION longitudinal_immutable()")
    op.execute("DROP TRIGGER diary_session_scope ON collection_sessions")
    op.execute("DROP FUNCTION diary_session_scope()")
    # Phase rollback deliberately removes phase-owned occurrence responses;
    # initial participation and financial obligations remain untouched.
    op.execute(
        "UPDATE collection_sessions SET state='erased' WHERE diary_occurrence_id IS NOT NULL"
    )
    for table in (
        "answer_revisions",
        "response_events",
        "interaction_attempts",
        "collection_answers",
    ):
        op.execute(
            f"DELETE FROM {table} WHERE session_id IN (SELECT id FROM collection_sessions WHERE diary_occurrence_id IS NOT NULL)"
        )
    op.execute("DELETE FROM collection_sessions WHERE diary_occurrence_id IS NOT NULL")
    op.execute("DROP INDEX uq_collection_diary_occurrence")
    op.execute("DROP INDEX uq_collection_candidate_base")
    op.execute("ALTER TABLE collection_sessions DROP COLUMN diary_occurrence_id")
    op.execute(
        "ALTER TABLE collection_sessions ADD CONSTRAINT uq_collection_candidate UNIQUE(candidate_id)"
    )
    for table in (
        "transcript_segments",
        "recordings",
        "notifications",
        "diary_occurrences",
        "bookings",
        "schedule_slots",
    ):
        op.drop_table(table)
    # Restore exact P11 optional-purpose policy.
    op.execute("""DO $$ DECLARE source text; BEGIN
      SELECT pg_get_functiondef('study_consent_scope()'::regprocedure) INTO source;
      source := replace(source, '''ai_processing'',''accessibility_context'',''recording''', '''ai_processing'',''accessibility_context''');
      EXECUTE source;
    END $$""")
