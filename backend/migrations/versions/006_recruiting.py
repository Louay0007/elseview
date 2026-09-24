"""Purpose-separated recruiting and atomic development capacity commitments."""

from alembic import op

revision = "006_recruiting"
down_revision = "005_study_guards"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_launch_scope", "launches", ["workspace_id", "id"])
    op.execute(
        "\nCREATE TABLE participant_profiles (\n\tuser_id UUID NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tattributes_json JSONB NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT ck_profile_status CHECK (status IN ('active','paused','withdrawn')), \n\tUNIQUE (user_id), \n\tFOREIGN KEY(user_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE private_contacts (\n\tcontact_lookup_hash VARCHAR(64) NOT NULL, \n\tattributes_json JSONB NOT NULL, \n\tsource VARCHAR(200) NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tretention_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, contact_lookup_hash), \n\tCONSTRAINT ck_private_status CHECK (status IN ('active','suppressed','withdrawn')), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_private_contacts_workspace_id ON private_contacts (workspace_id)")
    op.execute(
        "\nCREATE TABLE panel_consents (\n\tprofile_id UUID NOT NULL, \n\tdecision VARCHAR(16) NOT NULL, \n\tdocument_version VARCHAR(64) NOT NULL, \n\tdocument_digest VARCHAR(64) NOT NULL, \n\trequest_digest VARCHAR(64) NOT NULL, \n\treceipt_key VARCHAR(128) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (profile_id, receipt_key), \n\tCONSTRAINT ck_panel_consent CHECK (decision IN ('granted','withdrawn') AND char_length(document_digest)=64), \n\tFOREIGN KEY(profile_id) REFERENCES participant_profiles (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE private_contact_consents (\n\tcontact_id UUID NOT NULL, \n\tdocument_id UUID NOT NULL, \n\tdecision VARCHAR(16) NOT NULL, \n\treceipt_key VARCHAR(128) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, contact_id) REFERENCES private_contacts (workspace_id, id), \n\tFOREIGN KEY(workspace_id, document_id) REFERENCES consent_documents (workspace_id, id), \n\tUNIQUE (workspace_id, contact_id, receipt_key), \n\tCONSTRAINT ck_private_consent CHECK (decision IN ('granted','withdrawn')), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_private_contact_consents_workspace_id ON private_contact_consents (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE qualifications (\n\tprofile_id UUID NOT NULL, \n\tlanguage VARCHAR(35) NOT NULL, \n\tassessment_version VARCHAR(64) NOT NULL, \n\tpassed BOOLEAN NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (profile_id, language, assessment_version), \n\tFOREIGN KEY(profile_id) REFERENCES participant_profiles (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE candidates (\n\tlaunch_id UUID NOT NULL, \n\tsubject_id UUID, \n\tsource_kind VARCHAR(16) NOT NULL, \n\tsource_id UUID, \n\tattributes_json JSONB NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, launch_id, id), \n\tUNIQUE (workspace_id, launch_id, subject_id), \n\tUNIQUE (workspace_id, launch_id, source_kind, source_id), \n\tFOREIGN KEY(workspace_id, launch_id) REFERENCES launches (workspace_id, id), \n\tCONSTRAINT ck_candidate_state CHECK (source_kind IN ('public','private') AND status IN ('invited','eligible','screened_out','withdrawn')), \n\tFOREIGN KEY(subject_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_candidates_workspace_id ON candidates (workspace_id)")
    op.execute(
        "\nCREATE TABLE quota_cells (\n\tlaunch_id UUID NOT NULL, \n\tcapacity INTEGER NOT NULL, \n\tfilters_json JSONB NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, launch_id, id), \n\tFOREIGN KEY(workspace_id, launch_id) REFERENCES launches (workspace_id, id), \n\tCONSTRAINT ck_quota_capacity CHECK (capacity > 0), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_quota_cells_workspace_id ON quota_cells (workspace_id)")
    op.execute(
        "\nCREATE TABLE recruitment_configs (\n\tlaunch_id UUID NOT NULL, \n\tcapacity INTEGER NOT NULL, \n\tbudget_millimes INTEGER NOT NULL, \n\treward_millimes INTEGER NOT NULL, \n\thold_seconds INTEGER NOT NULL, \n\tfilters_json JSONB NOT NULL, \n\tscreener_json JSONB NOT NULL, \n\tscreening_policy VARCHAR(32) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, launch_id), \n\tFOREIGN KEY(workspace_id, launch_id) REFERENCES launches (workspace_id, id), \n\tCONSTRAINT ck_recruitment_limits CHECK (capacity > 0 AND budget_millimes >= 0 AND reward_millimes >= 0 AND hold_seconds BETWEEN 60 AND 86400), \n\tCONSTRAINT ck_screen_policy CHECK (screening_policy = 'uncompensated_disclosed'), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_recruitment_configs_workspace_id ON recruitment_configs (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE invitations (\n\tcandidate_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tredeemed_at TIMESTAMP WITH TIME ZONE, \n\trevoked_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, candidate_id) REFERENCES candidates (workspace_id, id), \n\tUNIQUE (token_hash), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_invitations_workspace_id ON invitations (workspace_id)")
    op.execute(
        "\nCREATE TABLE reservations (\n\tlaunch_id UUID NOT NULL, \n\tcandidate_id UUID NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\treward_millimes INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, launch_id, id), \n\tUNIQUE (workspace_id, candidate_id), \n\tFOREIGN KEY(workspace_id, launch_id, candidate_id) REFERENCES candidates (workspace_id, launch_id, id), \n\tCONSTRAINT ck_reservation_state CHECK (state IN ('held','consumed','released','expired') AND reward_millimes >= 0), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_reservations_workspace_id ON reservations (workspace_id)")
    op.execute(
        "\nCREATE TABLE screener_results (\n\tcandidate_id UUID NOT NULL, \n\trequest_digest VARCHAR(64) NOT NULL, \n\trules_digest VARCHAR(64) NOT NULL, \n\teligible BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, candidate_id), \n\tFOREIGN KEY(workspace_id, candidate_id) REFERENCES candidates (workspace_id, id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_screener_results_workspace_id ON screener_results (workspace_id)")
    op.execute(
        "\nCREATE TABLE reservation_cells (\n\tlaunch_id UUID NOT NULL, \n\treservation_id UUID NOT NULL, \n\tcell_id UUID NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (reservation_id, cell_id), \n\tFOREIGN KEY(workspace_id, launch_id, reservation_id) REFERENCES reservations (workspace_id, launch_id, id), \n\tFOREIGN KEY(workspace_id, launch_id, cell_id) REFERENCES quota_cells (workspace_id, launch_id, id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_reservation_cells_workspace_id ON reservation_cells (workspace_id)")

    op.execute("""
        CREATE FUNCTION recruiting_candidate_frozen() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.workspace_id, NEW.launch_id, NEW.source_kind) IS DISTINCT FROM
               (OLD.workspace_id, OLD.launch_id, OLD.source_kind) OR
               (OLD.subject_id IS NOT NULL AND NEW.subject_id IS DISTINCT FROM OLD.subject_id) OR
               (NEW.source_id IS DISTINCT FROM OLD.source_id AND NEW.source_id IS NOT NULL) OR
               (NEW.attributes_json IS DISTINCT FROM OLD.attributes_json AND
                NOT (NEW.status = 'withdrawn' AND NEW.attributes_json = '{}'::jsonb)) THEN
                RAISE EXCEPTION 'candidate recruitment snapshot is immutable';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER recruiting_candidate_frozen BEFORE UPDATE ON candidates
        FOR EACH ROW EXECUTE FUNCTION recruiting_candidate_frozen();
        CREATE FUNCTION recruiting_reservation_transition() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF (NEW.workspace_id, NEW.launch_id, NEW.candidate_id, NEW.reward_millimes) IS DISTINCT FROM
               (OLD.workspace_id, OLD.launch_id, OLD.candidate_id, OLD.reward_millimes) OR
               (OLD.state <> 'held' AND NEW.state <> OLD.state) THEN
                RAISE EXCEPTION 'reservation settlement is immutable';
            END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER recruiting_reservation_transition BEFORE UPDATE ON reservations
        FOR EACH ROW EXECUTE FUNCTION recruiting_reservation_transition();
        CREATE TRIGGER panel_consent_immutable BEFORE UPDATE OR DELETE ON panel_consents
        FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
        CREATE TRIGGER private_consent_immutable BEFORE UPDATE OR DELETE ON private_contact_consents
        FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
        CREATE TRIGGER recruiting_config_immutable BEFORE UPDATE ON recruitment_configs
        FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
        CREATE TRIGGER recruiting_quota_immutable BEFORE UPDATE ON quota_cells
        FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
        CREATE TRIGGER screener_immutable BEFORE UPDATE ON screener_results
        FOR EACH ROW EXECUTE FUNCTION privacy_immutable();
    """)


def downgrade():
    op.execute(
        "DROP TRIGGER IF EXISTS recruiting_reservation_transition ON reservations; DROP FUNCTION IF EXISTS recruiting_reservation_transition(); DROP TRIGGER IF EXISTS recruiting_candidate_frozen ON candidates; DROP FUNCTION IF EXISTS recruiting_candidate_frozen();"
    )
    op.drop_table("reservation_cells")
    op.drop_table("screener_results")
    op.drop_table("reservations")
    op.drop_table("invitations")
    op.drop_table("recruitment_configs")
    op.drop_table("quota_cells")
    op.drop_table("candidates")
    op.drop_table("qualifications")
    op.drop_table("private_contact_consents")
    op.drop_table("panel_consents")
    op.drop_table("private_contacts")
    op.drop_table("participant_profiles")

    op.drop_constraint("uq_launch_scope", "launches", type_="unique")
