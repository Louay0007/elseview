"""Bounded immutable analysis, reports, and revocable shares."""

from alembic import op

revision = "009_analytics"
down_revision = "008_reviews"
branch_labels = None
depends_on = None


def upgrade():
    # Tables use explicit local metadata definitions; no changes to applied migrations.
    from app.analytics.models import (
        AnalysisSnapshot,
        Export,
        Report,
        ReportShare,
        ReportVersion,
        SnapshotSource,
    )

    for model in (AnalysisSnapshot, SnapshotSource, Report, ReportVersion, Export, ReportShare):
        model.__table__.create(op.get_bind())
    op.execute("""
    CREATE FUNCTION analytics_snapshot_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        IF OLD.state <> 'invalidated' THEN RAISE EXCEPTION 'invalidate before purging snapshot'; END IF;
        RETURN OLD;
      END IF;
      IF TG_OP = 'INSERT' THEN
        IF NEW.state <> 'building' THEN RAISE EXCEPTION 'snapshot must start building'; END IF;
        IF NOT EXISTS (SELECT 1 FROM study_versions WHERE id=NEW.version_id AND study_id=NEW.study_id AND workspace_id=NEW.workspace_id AND state='published') THEN RAISE EXCEPTION 'snapshot version mismatch'; END IF;
        RETURN NEW;
      END IF;
      IF (NEW.id, NEW.workspace_id, NEW.study_id, NEW.version_id, NEW.created_at) IS DISTINCT FROM (OLD.id, OLD.workspace_id, OLD.study_id, OLD.version_id, OLD.created_at) THEN RAISE EXCEPTION 'snapshot identity immutable'; END IF;
      IF OLD.state = 'building' AND NEW.state IN ('building','ready') THEN
        IF NEW.state='ready' AND NEW.source_count <> (SELECT count(*) FROM snapshot_sources WHERE snapshot_id=NEW.id) THEN RAISE EXCEPTION 'snapshot manifest incomplete'; END IF;
        RETURN NEW;
      END IF;
      IF NEW.state NOT IN ('ready','invalidated') OR (OLD.state='invalidated' AND NEW.state <> 'invalidated') OR (NEW.source_count,NEW.consent_epoch,NEW.definition_digest,NEW.manifest_digest,NEW.metrics) IS DISTINCT FROM (OLD.source_count,OLD.consent_epoch,OLD.definition_digest,OLD.manifest_digest,OLD.metrics) THEN RAISE EXCEPTION 'snapshot immutable'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER analytics_snapshot_frozen BEFORE INSERT OR UPDATE OR DELETE ON analysis_snapshots FOR EACH ROW EXECUTE FUNCTION analytics_snapshot_guard();
    CREATE FUNCTION analytics_source_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE parent_state text; parent_version uuid; ref record;
    BEGIN
      IF TG_OP='INSERT' THEN
        SELECT state,version_id INTO parent_state,parent_version FROM analysis_snapshots WHERE id=NEW.snapshot_id AND workspace_id=NEW.workspace_id FOR SHARE;
        IF parent_state <> 'building' THEN RAISE EXCEPTION 'source manifest frozen'; END IF;
        IF NOT EXISTS (SELECT 1 FROM collection_sessions WHERE id=NEW.session_id AND workspace_id=NEW.workspace_id AND version_id=parent_version) THEN RAISE EXCEPTION 'source scope mismatch'; END IF;
        IF NEW.consent_receipt_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM consent_receipts c JOIN collection_sessions s ON s.id=NEW.session_id WHERE c.id=NEW.consent_receipt_id AND c.id=s.consent_receipt_id AND c.workspace_id=NEW.workspace_id AND c.subject_id=s.subject_id AND c.study_version_id=parent_version) THEN RAISE EXCEPTION 'source receipt mismatch'; END IF;
        IF NEW.exclusion_reason='included' THEN
          IF NOT EXISTS (SELECT 1 FROM collection_sessions s JOIN review_cases r ON r.session_id=s.id AND r.workspace_id=s.workspace_id WHERE s.id=NEW.session_id AND s.state='submitted' AND r.state='accepted' AND r.final_decision_id::text=NEW.decision->>'decision_id' AND r.generation=(NEW.decision->>'version')::integer) THEN RAISE EXCEPTION 'source acceptance mismatch'; END IF;
          FOR ref IN SELECT key,value FROM jsonb_each_text(NEW.revisions) LOOP
            IF NOT EXISTS (SELECT 1 FROM answer_revisions a JOIN collection_sessions s ON s.id=a.session_id WHERE a.id=ref.value::uuid AND a.session_id=NEW.session_id AND a.answer_id::text=s.submitted_snapshot->ref.key->>'answer_id' AND a.revision=(s.submitted_snapshot->ref.key->>'revision')::integer) THEN RAISE EXCEPTION 'source revision mismatch'; END IF;
          END LOOP;
          IF (SELECT count(*) FROM jsonb_object_keys(NEW.revisions)) <> (SELECT count(*) FROM collection_sessions s, jsonb_object_keys(s.submitted_snapshot) WHERE s.id=NEW.session_id) THEN RAISE EXCEPTION 'source revision manifest incomplete'; END IF;
        END IF;
        RETURN NEW;
      END IF;
      IF TG_OP='DELETE' AND EXISTS (SELECT 1 FROM analysis_snapshots WHERE id=OLD.snapshot_id AND state='invalidated') THEN RETURN OLD; END IF;
      RAISE EXCEPTION 'source immutable';
    END $$;
    CREATE TRIGGER analytics_source_frozen BEFORE INSERT OR UPDATE OR DELETE ON snapshot_sources FOR EACH ROW EXECUTE FUNCTION analytics_source_guard();
    CREATE FUNCTION analytics_report_version_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='INSERT' THEN
        IF NEW.state <> 'draft' OR NEW.approved_at IS NOT NULL THEN RAISE EXCEPTION 'report starts draft'; END IF;
        IF NOT EXISTS (SELECT 1 FROM reports r JOIN analysis_snapshots a ON a.study_id=r.study_id AND a.workspace_id=r.workspace_id WHERE r.id=NEW.report_id AND a.id=NEW.snapshot_id AND a.state='ready' AND r.workspace_id=NEW.workspace_id AND NEW.number=r.revision) THEN RAISE EXCEPTION 'report source mismatch'; END IF;
        RETURN NEW;
      END IF;
      IF (NEW.id,NEW.workspace_id,NEW.report_id,NEW.snapshot_id,NEW.number,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.workspace_id,OLD.report_id,OLD.snapshot_id,OLD.number,OLD.created_at) THEN RAISE EXCEPTION 'report immutable'; END IF;
      IF OLD.state='invalidated' AND NEW.state<>'invalidated' OR OLD.state='approved' AND NEW.state='draft' THEN RAISE EXCEPTION 'report transition invalid'; END IF;
      IF NEW.state='approved' AND (NEW.approved_at IS NULL OR NOT EXISTS (SELECT 1 FROM analysis_snapshots WHERE id=NEW.snapshot_id AND state='ready')) THEN RAISE EXCEPTION 'report approval invalid'; END IF;
      IF OLD.approved_at IS NOT NULL AND NEW.approved_at IS DISTINCT FROM OLD.approved_at THEN RAISE EXCEPTION 'approval immutable'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER analytics_report_version_frozen BEFORE INSERT OR UPDATE ON report_versions FOR EACH ROW EXECUTE FUNCTION analytics_report_version_guard();
    CREATE FUNCTION analytics_share_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='INSERT' THEN
        IF NOT EXISTS (SELECT 1 FROM report_versions WHERE id=NEW.report_version_id AND workspace_id=NEW.workspace_id AND state='approved') THEN RAISE EXCEPTION 'share requires approval'; END IF;
        IF NEW.expires_at > NEW.created_at + interval '30 days' THEN RAISE EXCEPTION 'share expiry exceeds limit'; END IF;
      ELSE
        IF (NEW.id,NEW.workspace_id,NEW.report_version_id,NEW.issuer_id,NEW.token_hash,NEW.expires_at,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.workspace_id,OLD.report_version_id,OLD.issuer_id,OLD.token_hash,OLD.expires_at,OLD.created_at) OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at) THEN RAISE EXCEPTION 'share immutable or revoked'; END IF;
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER analytics_share_frozen BEFORE INSERT OR UPDATE ON report_shares FOR EACH ROW EXECUTE FUNCTION analytics_share_guard();
    CREATE FUNCTION analytics_report_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF (NEW.id,NEW.workspace_id,NEW.study_id,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.workspace_id,OLD.study_id,OLD.created_at) OR NEW.revision <> OLD.revision + 1 THEN RAISE EXCEPTION 'report identity or revision immutable'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER analytics_report_frozen BEFORE UPDATE ON reports FOR EACH ROW EXECUTE FUNCTION analytics_report_guard();
    CREATE FUNCTION analytics_export_guard() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF (NEW.id,NEW.workspace_id,NEW.report_version_id,NEW.format,NEW.scope,NEW.created_at) IS DISTINCT FROM (OLD.id,OLD.workspace_id,OLD.report_version_id,OLD.format,OLD.scope,OLD.created_at) OR (OLD.state='invalidated' AND NEW.state<>'invalidated') THEN RAISE EXCEPTION 'export immutable'; END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER analytics_export_frozen BEFORE UPDATE ON exports FOR EACH ROW EXECUTE FUNCTION analytics_export_guard();
    """)


def downgrade():
    for name in (
        "report_shares",
        "exports",
        "report_versions",
        "reports",
        "snapshot_sources",
        "analysis_snapshots",
    ):
        op.drop_table(name)
    for name in (
        "analytics_report_guard",
        "analytics_export_guard",
        "analytics_share_guard",
        "analytics_report_version_guard",
        "analytics_source_guard",
        "analytics_snapshot_guard",
    ):
        op.execute("DROP FUNCTION IF EXISTS " + name + "()")
