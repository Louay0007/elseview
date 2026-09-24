"""Consent-gated AI drafts and conservative dispatch accounting."""

from alembic import op

revision = "010_ai"
down_revision = "009_analytics"
branch_labels = None
depends_on = None


def upgrade():
    # Frozen PostgreSQL DDL: future ORM edits cannot rewrite this migration.
    op.execute("""
CREATE TABLE ai_runs (
	study_id UUID, 
	snapshot_id UUID, 
	requester_id UUID NOT NULL, 
	job_id UUID, 
	command_key VARCHAR(100) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	cache_key VARCHAR(64) NOT NULL, 
	operation VARCHAR(32) NOT NULL, 
	instruction VARCHAR(2000) NOT NULL, 
	privacy_epoch INTEGER NOT NULL, 
	state VARCHAR(24) NOT NULL, 
	config JSONB NOT NULL, 
	coverage JSONB NOT NULL, 
	output JSONB, 
	approved_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ai_command UNIQUE (workspace_id, requester_id, command_key), 
	FOREIGN KEY(study_id) REFERENCES studies (id) ON DELETE SET NULL, 
	FOREIGN KEY(snapshot_id) REFERENCES analysis_snapshots (id) ON DELETE SET NULL, 
	FOREIGN KEY(requester_id) REFERENCES users (id), 
	FOREIGN KEY(job_id) REFERENCES jobs (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);
CREATE INDEX ix_ai_runs_cache_key ON ai_runs (cache_key);
CREATE INDEX ix_ai_runs_workspace_id ON ai_runs (workspace_id);
CREATE TABLE ai_attempts (
	run_id UUID NOT NULL, 
	state VARCHAR(24) NOT NULL, 
	reserved_cost NUMERIC(24, 8) NOT NULL, 
	actual_cost NUMERIC(24, 8), 
	budget_day VARCHAR(10) NOT NULL, 
	request_id VARCHAR(200), 
	usage JSONB, 
	error_code VARCHAR(64), 
	reconciliation VARCHAR(100), 
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ai_attempt_run UNIQUE (run_id), 
	CONSTRAINT ck_ai_cost CHECK (reserved_cost >= 0 AND (actual_cost IS NULL OR actual_cost >= 0)), 
	FOREIGN KEY(run_id) REFERENCES ai_runs (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);
CREATE INDEX ix_ai_attempts_workspace_id ON ai_attempts (workspace_id);
CREATE TABLE ai_evidence (
	run_id UUID NOT NULL, 
	source_id VARCHAR(100) NOT NULL, 
	start INTEGER NOT NULL, 
	"end" INTEGER NOT NULL, 
	quote_hash VARCHAR(64) NOT NULL, 
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(run_id) REFERENCES ai_runs (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);
CREATE INDEX ix_ai_evidence_workspace_id ON ai_evidence (workspace_id);
CREATE TABLE usage_budgets (
	scope VARCHAR(64) NOT NULL, 
	currency VARCHAR(3) NOT NULL, 
	reserved NUMERIC(24, 8) NOT NULL, 
	spent NUMERIC(24, 8) NOT NULL, 
	id UUID NOT NULL, 
	workspace_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_ai_budget UNIQUE (workspace_id, scope, currency), 
	CONSTRAINT ck_ai_budget_nonnegative CHECK (reserved >= 0 AND spent >= 0), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id)
);
CREATE INDEX ix_usage_budgets_workspace_id ON usage_budgets (workspace_id);
    """)
    op.execute("""
    ALTER TABLE ai_runs ADD CONSTRAINT ck_ai_run_state CHECK (state IN ('queued','running','draft','approved','failed','uncertain','invalidated'));
    ALTER TABLE ai_attempts ADD CONSTRAINT ck_ai_attempt_state CHECK (state IN ('reserved','sent','uncertain','settled','released'));
    CREATE FUNCTION ai_scope_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_TABLE_NAME='ai_runs' THEN
        IF TG_OP='INSERT' THEN
          IF NOT EXISTS (SELECT 1 FROM studies WHERE id=NEW.study_id AND workspace_id=NEW.workspace_id AND ai_policy='assisted') THEN RAISE EXCEPTION 'AI study scope'; END IF;
          IF NEW.snapshot_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM analysis_snapshots WHERE id=NEW.snapshot_id AND workspace_id=NEW.workspace_id AND study_id=NEW.study_id AND state='ready') THEN RAISE EXCEPTION 'AI snapshot scope'; END IF;
        ELSE
          IF (NEW.workspace_id,NEW.requester_id,NEW.command_key,NEW.request_hash,NEW.config,NEW.cache_key,NEW.privacy_epoch,NEW.operation) IS DISTINCT FROM (OLD.workspace_id,OLD.requester_id,OLD.command_key,OLD.request_hash,OLD.config,OLD.cache_key,OLD.privacy_epoch,OLD.operation) THEN RAISE EXCEPTION 'AI identity immutable'; END IF;
          IF OLD.state='invalidated' AND NEW.state<>'invalidated' THEN RAISE EXCEPTION 'AI invalidation final'; END IF;
          IF OLD.state IN ('draft','approved') AND NEW.state<>'invalidated' AND NEW.output IS DISTINCT FROM OLD.output THEN RAISE EXCEPTION 'AI result immutable'; END IF;
          IF OLD.state='approved' AND NEW.state NOT IN ('approved','invalidated') THEN RAISE EXCEPTION 'AI approval final'; END IF;
          IF (NEW.study_id,NEW.snapshot_id) IS DISTINCT FROM (OLD.study_id,OLD.snapshot_id) AND NOT (NEW.state='invalidated' AND (NEW.study_id IS NULL OR NEW.study_id=OLD.study_id) AND (NEW.snapshot_id IS NULL OR NEW.snapshot_id=OLD.snapshot_id)) THEN RAISE EXCEPTION 'AI source immutable'; END IF;
          IF NEW.state<>'invalidated' AND (NEW.instruction,NEW.coverage) IS DISTINCT FROM (OLD.instruction,OLD.coverage) THEN RAISE EXCEPTION 'AI input immutable'; END IF;
        END IF;
      ELSE
        IF NOT EXISTS (SELECT 1 FROM ai_runs WHERE id=NEW.run_id AND workspace_id=NEW.workspace_id) THEN RAISE EXCEPTION 'AI child scope'; END IF;
        IF TG_TABLE_NAME='ai_attempts' AND TG_OP='UPDATE' THEN
          IF (NEW.run_id,NEW.workspace_id,NEW.reserved_cost,NEW.budget_day) IS DISTINCT FROM (OLD.run_id,OLD.workspace_id,OLD.reserved_cost,OLD.budget_day) THEN RAISE EXCEPTION 'AI reservation immutable'; END IF;
          IF OLD.state IN ('sent','uncertain','settled','released') AND NEW.state='reserved' OR OLD.state IN ('settled','released') AND NEW.state NOT IN ('settled','released') THEN RAISE EXCEPTION 'AI dispatch cannot reset'; END IF;
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER ai_run_scope BEFORE INSERT OR UPDATE ON ai_runs FOR EACH ROW EXECUTE FUNCTION ai_scope_guard();
    CREATE TRIGGER ai_attempt_scope BEFORE INSERT OR UPDATE ON ai_attempts FOR EACH ROW EXECUTE FUNCTION ai_scope_guard();
    CREATE TRIGGER ai_evidence_scope BEFORE INSERT OR UPDATE ON ai_evidence FOR EACH ROW EXECUTE FUNCTION ai_scope_guard();
    """)


def downgrade():
    for name in ("usage_budgets", "ai_evidence", "ai_attempts", "ai_runs"):
        op.drop_table(name)
    op.execute("DROP FUNCTION ai_scope_guard()")
