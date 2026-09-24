"""Bounded consented text assessments; no content seeds or legacy conversion."""

from alembic import op

revision = "026_language_assessments"
down_revision = "025_auth_delivery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE language_assessment_versions (\n\tassessment_key VARCHAR(64) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tlanguage VARCHAR(24) NOT NULL, \n\tschema_version INTEGER NOT NULL, \n\tauthor_id UUID NOT NULL, \n\tsynthetic BOOLEAN NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tpublic_json JSONB NOT NULL, \n\tpolicy_json JSONB NOT NULL, \n\tpublic_digest VARCHAR(64) NOT NULL, \n\tcontent_digest VARCHAR(64) NOT NULL, \n\tapproved_by UUID, \n\tapproved_at TIMESTAMP WITH TIME ZONE, \n\treview_reference VARCHAR(128), \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (assessment_key, version), \n\tUNIQUE (id, language), \n\tCONSTRAINT ck_language_version_language CHECK (language IN ('tunisianArabic','formalArabic','french','arabizi')), \n\tCONSTRAINT ck_language_version_state CHECK (state IN ('draft','approved','retired') AND schema_version = 1 AND version > 0), \n\tCONSTRAINT ck_language_version_approval CHECK (state = 'draft' OR (approved_by IS NOT NULL AND approved_by <> author_id AND approved_at IS NOT NULL AND review_reference IS NOT NULL)), \n\tFOREIGN KEY(author_id) REFERENCES users (id), \n\tFOREIGN KEY(approved_by) REFERENCES users (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE language_assessment_keys (\n\tversion_id UUID NOT NULL, \n\tmaterial_json JSONB NOT NULL, \n\tPRIMARY KEY (version_id), \n\tFOREIGN KEY(version_id) REFERENCES language_assessment_versions (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE language_assessment_consents (\n\tprofile_id UUID NOT NULL, \n\tdecision VARCHAR(16) NOT NULL, \n\tdocument_version VARCHAR(16) NOT NULL, \n\tdocument_digest VARCHAR(64) NOT NULL, \n\treceipt_key VARCHAR(128) NOT NULL, \n\trequest_digest VARCHAR(64) NOT NULL, \n\tgrant_id UUID, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (profile_id, receipt_key), \n\tUNIQUE (profile_id, id), \n\tFOREIGN KEY(profile_id, grant_id) REFERENCES language_assessment_consents (profile_id, id), \n\tCONSTRAINT ck_language_consent_scope CHECK ((decision = 'granted' AND grant_id IS NULL) OR (decision = 'withdrawn' AND grant_id IS NOT NULL)), \n\tFOREIGN KEY(profile_id) REFERENCES participant_profiles (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE language_assessment_attempts (\n\tprofile_id UUID NOT NULL, \n\tversion_id UUID NOT NULL, \n\tlanguage VARCHAR(24) NOT NULL, \n\tconsent_grant_id UUID NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tcommand_key VARCHAR(128) NOT NULL, \n\tstart_digest VARCHAR(64) NOT NULL, \n\tsubmit_key VARCHAR(128), \n\tsubmission_digest VARCHAR(64), \n\tstate VARCHAR(16) NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdeadline_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tsubmitted_at TIMESTAMP WITH TIME ZONE, \n\tresponses_json JSONB, \n\tappeal_key VARCHAR(128), \n\tappeal_digest VARCHAR(64), \n\tappeal_reason VARCHAR(2000), \n\tappeal_requested_at TIMESTAMP WITH TIME ZONE, \n\tretention_until TIMESTAMP WITH TIME ZONE NOT NULL, \n\tpurged_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (profile_id, command_key), \n\tUNIQUE (profile_id, language, sequence), \n\tFOREIGN KEY(version_id, language) REFERENCES language_assessment_versions (id, language), \n\tFOREIGN KEY(profile_id, consent_grant_id) REFERENCES language_assessment_consents (profile_id, id), \n\tCONSTRAINT ck_language_attempt_state CHECK (state IN ('started','submitted','adjudicated','abandoned','withdrawn') AND sequence > 0), \n\tFOREIGN KEY(profile_id) REFERENCES participant_profiles (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_language_attempt_queue ON language_assessment_attempts (state, language, submitted_at)"
    )
    op.execute(
        "CREATE INDEX ix_language_attempt_retention ON language_assessment_attempts (retention_until)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_language_active_attempt ON language_assessment_attempts (profile_id, language) WHERE state IN ('started','submitted')"
    )
    op.execute(
        "\nCREATE TABLE language_assessment_decisions (\n\tattempt_id UUID NOT NULL, \n\tround INTEGER NOT NULL, \n\treviewer_id UUID NOT NULL, \n\tcommand_key VARCHAR(128) NOT NULL, \n\trequest_digest VARCHAR(64) NOT NULL, \n\tverdict VARCHAR(24) NOT NULL, \n\tfindings_json JSONB, \n\trationale VARCHAR(2000), \n\tdecided_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE, \n\tprevious_decision_id UUID, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (attempt_id, round), \n\tUNIQUE (attempt_id, command_key), \n\tUNIQUE (attempt_id, id), \n\tFOREIGN KEY(attempt_id, previous_decision_id) REFERENCES language_assessment_decisions (attempt_id, id), \n\tCONSTRAINT ck_language_decision_round CHECK ((round = 1 AND previous_decision_id IS NULL) OR (round = 2 AND previous_decision_id IS NOT NULL)), \n\tCONSTRAINT ck_language_decision_verdict CHECK ((verdict = 'qualified' AND expires_at IS NOT NULL) OR (verdict IN ('not_qualified','inconclusive') AND expires_at IS NULL)), \n\tFOREIGN KEY(attempt_id) REFERENCES language_assessment_attempts (id), \n\tFOREIGN KEY(reviewer_id) REFERENCES users (id)\n)\n\n"
    )


def downgrade():
    # Locks precede the populated guard: no concurrent writer can lose evidence.
    op.execute("LOCK TABLE language_assessment_versions IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE language_assessment_keys IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE language_assessment_consents IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE language_assessment_attempts IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE language_assessment_decisions IN ACCESS EXCLUSIVE MODE")
    op.execute(
        "DO $$ BEGIN IF EXISTS (SELECT 1 FROM language_assessment_versions) OR EXISTS (SELECT 1 FROM language_assessment_keys) OR EXISTS (SELECT 1 FROM language_assessment_consents) OR EXISTS (SELECT 1 FROM language_assessment_attempts) OR EXISTS (SELECT 1 FROM language_assessment_decisions) THEN RAISE EXCEPTION 'Assessment data must be retained; downgrade refused'; END IF; END $$"
    )
    op.drop_table("language_assessment_decisions")
    op.drop_table("language_assessment_attempts")
    op.drop_table("language_assessment_consents")
    op.drop_table("language_assessment_keys")
    op.drop_table("language_assessment_versions")
