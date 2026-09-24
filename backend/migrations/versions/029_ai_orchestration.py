"""Opt-in bounded AI graphs; never discard charged history on downgrade."""

from alembic import op

revision = "029_ai_orchestration"
down_revision = "028_notification_delivery"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    ALTER TABLE ai_runs ADD CONSTRAINT uq_ai_run_scope UNIQUE(workspace_id,id);
    ALTER TABLE ai_runs DROP CONSTRAINT ck_ai_run_state;
    ALTER TABLE ai_runs ADD CONSTRAINT ck_ai_run_state CHECK(state IN ('queued','running','draft','approved','failed','uncertain','invalidated','cancelled'));
    CREATE TABLE ai_run_inputs (
      id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id),
      created_at timestamptz NOT NULL DEFAULT now(), run_id uuid NOT NULL,
      snapshot_id uuid NOT NULL, role varchar(10) NOT NULL CHECK(role IN ('primary','left','right')),
      binding jsonb NOT NULL CHECK(jsonb_typeof(binding)='object' AND octet_length(binding::text)<=4096),
      CONSTRAINT uq_ai_input_role UNIQUE(run_id,role),
      FOREIGN KEY(workspace_id,run_id) REFERENCES ai_runs(workspace_id,id),
      FOREIGN KEY(workspace_id,snapshot_id) REFERENCES analysis_snapshots(workspace_id,id)
    );
    CREATE INDEX ix_ai_run_inputs_workspace_id ON ai_run_inputs(workspace_id);
    CREATE TABLE ai_steps (
      id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id),
      created_at timestamptz NOT NULL DEFAULT now(), run_id uuid NOT NULL,
      ordinal integer NOT NULL CHECK(ordinal BETWEEN 0 AND 4),
      stage varchar(12) NOT NULL CHECK(stage IN ('map','synthesis')),
      job_id uuid REFERENCES jobs(id), state varchar(12) NOT NULL CHECK(state IN ('pending','sent','complete','stopped')),
      membership jsonb NOT NULL, input_digest varchar(64) NOT NULL,
      result jsonb, result_digest varchar(64),
      CHECK(jsonb_typeof(membership)='object' AND octet_length(membership::text)<=100000 AND (result IS NULL OR (jsonb_typeof(result)='object' AND octet_length(result::text)<=100000))),
      CONSTRAINT uq_ai_step_ordinal UNIQUE(run_id,ordinal),
      FOREIGN KEY(workspace_id,run_id) REFERENCES ai_runs(workspace_id,id)
    );
    CREATE INDEX ix_ai_steps_workspace_id ON ai_steps(workspace_id);
    CREATE TABLE ai_commands (
      id uuid PRIMARY KEY, workspace_id uuid NOT NULL REFERENCES workspaces(id),
      created_at timestamptz NOT NULL DEFAULT now(), run_id uuid NOT NULL,
      requester_id uuid NOT NULL REFERENCES users(id), command_key varchar(100) NOT NULL,
      request_hash varchar(64) NOT NULL,
      CONSTRAINT uq_ai_bound_command UNIQUE(workspace_id,requester_id,command_key),
      FOREIGN KEY(workspace_id,run_id) REFERENCES ai_runs(workspace_id,id)
    );
    CREATE INDEX ix_ai_commands_workspace_id ON ai_commands(workspace_id);
    ALTER TABLE ai_attempts ADD COLUMN step_id uuid REFERENCES ai_steps(id);
    ALTER TABLE ai_attempts DROP CONSTRAINT uq_ai_attempt_run;
    CREATE UNIQUE INDEX uq_ai_attempt_legacy ON ai_attempts(run_id) WHERE step_id IS NULL;
    ALTER TABLE ai_attempts ADD CONSTRAINT uq_ai_attempt_step UNIQUE(step_id);
    CREATE FUNCTION ai_graph_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE r ai_runs; s ai_steps;
    BEGIN
      IF TG_OP='DELETE' THEN
        SELECT * INTO r FROM ai_runs WHERE id=OLD.run_id;
        IF TG_TABLE_NAME='ai_attempts' AND r.config->'depth_profile'->>'revision' IS DISTINCT FROM '2' THEN RETURN OLD; END IF;
        IF TG_TABLE_NAME<>'ai_run_inputs' OR r.state<>'invalidated' THEN RAISE EXCEPTION 'AI history retained'; END IF;
        RETURN OLD;
      END IF;
      SELECT * INTO r FROM ai_runs WHERE id=NEW.run_id AND workspace_id=NEW.workspace_id;
      IF r.id IS NULL THEN RAISE EXCEPTION 'AI graph scope'; END IF;
      IF TG_TABLE_NAME='ai_attempts' THEN
        IF TG_OP='UPDATE' AND NEW.step_id IS DISTINCT FROM OLD.step_id THEN RAISE EXCEPTION 'AI attempt step immutable'; END IF;
        IF NEW.step_id IS NOT NULL THEN
          SELECT * INTO s FROM ai_steps WHERE id=NEW.step_id AND run_id=NEW.run_id AND workspace_id=NEW.workspace_id;
          IF s.id IS NULL THEN RAISE EXCEPTION 'AI attempt step scope'; END IF;
          IF TG_OP='INSERT' THEN
            IF r.state<>'queued' OR NEW.state<>'reserved' THEN RAISE EXCEPTION 'AI attempt initial state'; END IF;
          ELSIF OLD.state IN ('settled','released') AND (NEW.actual_cost,NEW.usage) IS DISTINCT FROM (OLD.actual_cost,OLD.usage) THEN RAISE EXCEPTION 'AI settled charge immutable'; END IF;
        ELSIF r.config->'depth_profile'->>'revision'='2' THEN RAISE EXCEPTION 'AI graph attempt requires step';
        END IF;
        RETURN NEW;
      END IF;
      IF r.config->'depth_profile'->>'revision' IS DISTINCT FROM '2' THEN RAISE EXCEPTION 'AI graph revision'; END IF;
      IF TG_OP='INSERT' THEN
        IF TG_TABLE_NAME<>'ai_commands' AND r.state<>'queued' THEN RAISE EXCEPTION 'AI graph frozen'; END IF;
        IF TG_TABLE_NAME='ai_run_inputs' THEN
          IF NOT EXISTS (SELECT 1 FROM analysis_snapshots WHERE id=NEW.snapshot_id AND workspace_id=NEW.workspace_id AND study_id=r.study_id AND state='ready') THEN RAISE EXCEPTION 'AI input scope'; END IF;
          IF (r.operation='comparison_report' AND NEW.role NOT IN ('left','right')) OR (r.operation<>'comparison_report' AND NEW.role<>'primary') THEN RAISE EXCEPTION 'AI input role'; END IF;
        ELSIF TG_TABLE_NAME='ai_steps' THEN
          IF NEW.ordinal >= (r.config->'depth_profile'->>'max_provider_calls')::integer THEN RAISE EXCEPTION 'AI graph bound'; END IF;
          IF NEW.state<>'pending' OR NEW.result IS NOT NULL OR NEW.result_digest IS NOT NULL THEN RAISE EXCEPTION 'AI step initial state'; END IF;
        ELSIF TG_TABLE_NAME='ai_commands' THEN
          IF NEW.requester_id<>r.requester_id THEN RAISE EXCEPTION 'AI command requester'; END IF;
        END IF;
      ELSE
        IF (NEW.id,NEW.workspace_id,NEW.run_id,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.workspace_id,OLD.run_id,OLD.created_at) THEN RAISE EXCEPTION 'AI graph identity immutable'; END IF;
        IF TG_TABLE_NAME IN ('ai_run_inputs','ai_commands') THEN RAISE EXCEPTION 'AI graph input immutable'; END IF;
        IF (NEW.ordinal,NEW.stage,NEW.input_digest) IS DISTINCT FROM (OLD.ordinal,OLD.stage,OLD.input_digest) THEN RAISE EXCEPTION 'AI step identity immutable'; END IF;
        IF NEW.membership IS DISTINCT FROM OLD.membership AND NOT (r.state='invalidated' AND NEW.membership='{}'::jsonb) THEN RAISE EXCEPTION 'AI membership immutable'; END IF;
        IF OLD.job_id IS NOT NULL AND NEW.job_id IS DISTINCT FROM OLD.job_id THEN RAISE EXCEPTION 'AI job immutable'; END IF;
        IF OLD.state IN ('sent','complete','stopped') AND NEW.state='pending' THEN RAISE EXCEPTION 'AI step cannot reset'; END IF;
        IF OLD.state='complete' AND (NEW.result,NEW.result_digest) IS DISTINCT FROM (OLD.result,OLD.result_digest) AND NOT (r.state='invalidated' AND NEW.result IS NULL AND NEW.result_digest IS NULL) THEN RAISE EXCEPTION 'AI intermediate immutable'; END IF;
      END IF;
      IF TG_TABLE_NAME='ai_steps' THEN
        IF NEW.job_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM jobs WHERE id=NEW.job_id AND workspace_id=NEW.workspace_id AND target_id=NEW.id AND requester_id=r.requester_id AND kind='ai.step') THEN RAISE EXCEPTION 'AI step job scope'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER ai_input_guard BEFORE INSERT OR UPDATE OR DELETE ON ai_run_inputs FOR EACH ROW EXECUTE FUNCTION ai_graph_guard();
    CREATE TRIGGER ai_step_guard BEFORE INSERT OR UPDATE OR DELETE ON ai_steps FOR EACH ROW EXECUTE FUNCTION ai_graph_guard();
    CREATE TRIGGER ai_command_guard BEFORE INSERT OR UPDATE OR DELETE ON ai_commands FOR EACH ROW EXECUTE FUNCTION ai_graph_guard();
    CREATE TRIGGER ai_attempt_graph_guard BEFORE INSERT OR UPDATE OR DELETE ON ai_attempts FOR EACH ROW EXECUTE FUNCTION ai_graph_guard();
    """)


def downgrade():
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM ai_runs WHERE config->'depth_profile'->>'revision'='2') THEN
        RAISE EXCEPTION 'Revision-2 AI history exists; disable creation and reconcile, do not downgrade';
      END IF;
    END $$;
    DROP TRIGGER ai_attempt_graph_guard ON ai_attempts;
    DROP TABLE ai_commands;
    ALTER TABLE ai_attempts DROP CONSTRAINT uq_ai_attempt_step;
    DROP INDEX uq_ai_attempt_legacy;
    ALTER TABLE ai_attempts DROP COLUMN step_id;
    ALTER TABLE ai_attempts ADD CONSTRAINT uq_ai_attempt_run UNIQUE(run_id);
    DROP TABLE ai_steps;
    DROP TABLE ai_run_inputs;
    DROP FUNCTION ai_graph_guard();
    ALTER TABLE ai_runs DROP CONSTRAINT uq_ai_run_scope;
    ALTER TABLE ai_runs DROP CONSTRAINT ck_ai_run_state;
    ALTER TABLE ai_runs ADD CONSTRAINT ck_ai_run_state CHECK(state IN ('queued','running','draft','approved','failed','uncertain','invalidated'));
    """)
