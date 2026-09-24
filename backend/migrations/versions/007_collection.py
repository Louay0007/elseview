"""Resumable participant collection."""

from alembic import op

revision = "007_collection"
down_revision = "006_recruiting"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE collection_sessions (\n\tcandidate_id UUID NOT NULL, \n\tsubject_id UUID NOT NULL, \n\tversion_id UUID NOT NULL, \n\tlaunch_id UUID NOT NULL, \n\tconsent_receipt_id UUID, \n\tcapability_hash VARCHAR(64) NOT NULL, \n\tstart_hash VARCHAR(64) NOT NULL, \n\tlocale VARCHAR(35) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\trevision INTEGER NOT NULL, \n\tlast_sequence INTEGER NOT NULL, \n\tassignments JSONB NOT NULL, \n\tsubmitted_snapshot JSONB, \n\tsubmitted_at TIMESTAMP WITH TIME ZONE, \n\tquality_job_id UUID, \n\tquality_summary JSONB, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_collection_candidate UNIQUE (candidate_id), \n\tCONSTRAINT uq_collection_capability UNIQUE (capability_hash), \n\tFOREIGN KEY(workspace_id, version_id) REFERENCES study_versions (workspace_id, id), \n\tFOREIGN KEY(workspace_id, launch_id, candidate_id) REFERENCES candidates (workspace_id, launch_id, id), \n\tFOREIGN KEY(workspace_id, launch_id) REFERENCES launches (workspace_id, id), \n\tCONSTRAINT ck_collection_state CHECK (state IN ('active','submitted','withdrawn','erased')), \n\tCONSTRAINT ck_collection_revision CHECK (revision >= 0 AND last_sequence >= -1), \n\tFOREIGN KEY(candidate_id) REFERENCES candidates (id), \n\tFOREIGN KEY(subject_id) REFERENCES users (id), \n\tFOREIGN KEY(launch_id) REFERENCES launches (id), \n\tFOREIGN KEY(consent_receipt_id) REFERENCES consent_receipts (id), \n\tFOREIGN KEY(quality_job_id) REFERENCES jobs (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_collection_sessions_workspace_id ON collection_sessions (workspace_id)"
    )
    op.execute("CREATE INDEX ix_collection_sessions_subject_id ON collection_sessions (subject_id)")
    op.execute(
        "\nCREATE TABLE collection_answers (\n\tid UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tblock_key VARCHAR(64) NOT NULL, \n\toccurrence INTEGER NOT NULL, \n\tcurrent_revision INTEGER NOT NULL, \n\tfinal_revision INTEGER, \n\tactive BOOLEAN NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_answer_session_id UNIQUE (session_id, id), \n\tCONSTRAINT uq_collection_answer UNIQUE (session_id, block_key, occurrence), \n\tFOREIGN KEY(session_id) REFERENCES collection_sessions (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_collection_answers_session_id ON collection_answers (session_id)")
    op.execute(
        "\nCREATE TABLE answer_revisions (\n\tid UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tanswer_id UUID NOT NULL, \n\trevision INTEGER NOT NULL, \n\tclient_event_id UUID NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tpayload JSONB NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tvalue JSONB, \n\treason_code VARCHAR(24), \n\treceipt JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT fk_revision_answer_session FOREIGN KEY (session_id, answer_id) REFERENCES collection_answers (session_id, id), \n\tCONSTRAINT uq_answer_revision UNIQUE (answer_id, revision), \n\tCONSTRAINT uq_answer_client_event UNIQUE (session_id, client_event_id), \n\tCONSTRAINT ck_answer_revision CHECK (revision > 0), \n\tFOREIGN KEY(session_id) REFERENCES collection_sessions (id), \n\tFOREIGN KEY(answer_id) REFERENCES collection_answers (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE response_events (\n\tid UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tblock_key VARCHAR(64), \n\tclient_event_id UUID, \n\tsequence INTEGER, \n\tkind VARCHAR(64) NOT NULL, \n\tprovenance VARCHAR(24) NOT NULL, \n\tpayload JSONB NOT NULL, \n\treceived_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_response_client_event UNIQUE (session_id, client_event_id), \n\tCONSTRAINT uq_response_sequence UNIQUE (session_id, sequence), \n\tCONSTRAINT ck_event_provenance CHECK (provenance IN ('client_observed','server_created')), \n\tFOREIGN KEY(session_id) REFERENCES collection_sessions (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_response_events_session_id ON response_events (session_id)")
    op.execute(
        "\nCREATE TABLE interaction_attempts (\n\tid UUID NOT NULL, \n\tsession_id UUID NOT NULL, \n\tblock_key VARCHAR(64) NOT NULL, \n\tstate VARCHAR(24) NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tended_at TIMESTAMP WITH TIME ZONE, \n\tvisible_ms INTEGER, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_interaction_attempt UNIQUE (session_id, block_key), \n\tFOREIGN KEY(session_id) REFERENCES collection_sessions (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE FUNCTION collection_session_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nBEGIN\n IF (NEW.workspace_id, NEW.candidate_id, NEW.subject_id, NEW.version_id, NEW.launch_id, NEW.capability_hash, NEW.start_hash, NEW.locale) IS DISTINCT FROM (OLD.workspace_id, OLD.candidate_id, OLD.subject_id, OLD.version_id, OLD.launch_id, OLD.capability_hash, OLD.start_hash, OLD.locale) THEN RAISE EXCEPTION 'session identity is immutable'; END IF;\n IF NEW.state <> OLD.state AND NOT ((OLD.state = 'active' AND NEW.state IN ('submitted','withdrawn','erased')) OR (OLD.state = 'submitted' AND NEW.state IN ('withdrawn','erased')) OR (OLD.state = 'withdrawn' AND NEW.state = 'erased')) THEN RAISE EXCEPTION 'invalid session transition'; END IF;\n IF NEW.state <> 'erased' AND NEW.assignments IS DISTINCT FROM OLD.assignments THEN RAISE EXCEPTION 'assignments immutable'; END IF;\n IF OLD.state = 'submitted' AND NEW.state NOT IN ('withdrawn','erased') AND (NEW.submitted_snapshot, NEW.submitted_at, NEW.revision) IS DISTINCT FROM (OLD.submitted_snapshot, OLD.submitted_at, OLD.revision) THEN RAISE EXCEPTION 'submission immutable'; END IF;\n RETURN NEW;\nEND $$;\nCREATE TRIGGER collection_session_frozen BEFORE UPDATE ON collection_sessions FOR EACH ROW EXECUTE FUNCTION collection_session_guard();\nCREATE FUNCTION collection_fact_guard() RETURNS trigger LANGUAGE plpgsql AS $$\nDECLARE parent_state text;\nBEGIN\n IF TG_OP = 'INSERT' THEN\n SELECT state INTO parent_state FROM collection_sessions WHERE id = NEW.session_id FOR SHARE;\n IF parent_state = 'active' THEN RETURN NEW; END IF;\n IF TG_TABLE_NAME = 'response_events' AND parent_state = 'submitted' THEN\n IF NEW.kind = 'session.submitted' AND NEW.provenance = 'server_created' AND NEW.client_event_id IS NULL AND NEW.sequence IS NULL AND NEW.payload = '{}'::jsonb AND NOT EXISTS (SELECT 1 FROM response_events WHERE session_id = NEW.session_id AND kind = 'session.submitted') THEN RETURN NEW; END IF;\n END IF;\n RAISE EXCEPTION 'final facts immutable';\n END IF;\n SELECT state INTO parent_state FROM collection_sessions WHERE id = OLD.session_id;\n IF TG_OP = 'DELETE' AND parent_state = 'erased' THEN RETURN OLD; END IF;\n IF TG_TABLE_NAME IN ('answer_revisions','response_events') THEN RAISE EXCEPTION 'collection facts append only'; END IF;\n IF parent_state <> 'active' THEN RAISE EXCEPTION 'final facts immutable'; END IF;\n IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'facts require privacy erasure'; END IF;\n RETURN NEW;\nEND $$;\nCREATE TRIGGER answer_revision_frozen BEFORE INSERT OR UPDATE OR DELETE ON answer_revisions FOR EACH ROW EXECUTE FUNCTION collection_fact_guard();\nCREATE TRIGGER response_event_frozen BEFORE INSERT OR UPDATE OR DELETE ON response_events FOR EACH ROW EXECUTE FUNCTION collection_fact_guard();\nCREATE TRIGGER answer_final_frozen BEFORE INSERT OR UPDATE OR DELETE ON collection_answers FOR EACH ROW EXECUTE FUNCTION collection_fact_guard();\nCREATE TRIGGER interaction_final_frozen BEFORE INSERT OR UPDATE OR DELETE ON interaction_attempts FOR EACH ROW EXECUTE FUNCTION collection_fact_guard();\n"
    )


def downgrade():
    op.drop_table("interaction_attempts")
    op.drop_table("response_events")
    op.drop_table("answer_revisions")
    op.drop_table("collection_answers")
    op.drop_table("collection_sessions")
    op.execute("DROP FUNCTION collection_fact_guard(); DROP FUNCTION collection_session_guard();")
