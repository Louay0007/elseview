"""Human review and append-only manual compensation accounting."""

from alembic import op

revision = "008_reviews"
down_revision = "007_collection"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE collection_sessions ADD CONSTRAINT uq_collection_session_scope UNIQUE(workspace_id,id)"
    )
    op.execute(
        "\nCREATE TABLE review_cases (\n\tsession_id UUID NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tgeneration INTEGER NOT NULL, \n\tfinal_decision_id UUID, \n\taccepted_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (session_id), \n\tFOREIGN KEY(workspace_id, session_id) REFERENCES collection_sessions (workspace_id, id) ON DELETE CASCADE, \n\tCHECK (state IN ('pending','accepted','rejected','disputed','appealed','erased') AND generation >= 0), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_review_cases_workspace_id ON review_cases (workspace_id)")
    op.execute(
        "\nCREATE TABLE quality_flags (\n\tcase_id UUID NOT NULL, \n\tpolicy VARCHAR(80) NOT NULL, \n\tblock_key VARCHAR(64) NOT NULL, \n\tcode VARCHAR(80) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (case_id, policy, block_key, code), \n\tFOREIGN KEY(workspace_id, case_id) REFERENCES review_cases (workspace_id, id) ON DELETE CASCADE, \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_quality_flags_workspace_id ON quality_flags (workspace_id)")
    op.execute(
        "\nCREATE TABLE review_assignments (\n\tcase_id UUID NOT NULL, \n\treviewer_id UUID NOT NULL, \n\tround INTEGER NOT NULL, \n\tkind VARCHAR(20) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (case_id, round), \n\tUNIQUE (case_id, reviewer_id), \n\tFOREIGN KEY(workspace_id, case_id) REFERENCES review_cases (workspace_id, id) ON DELETE CASCADE, \n\tCHECK (round > 0 AND kind IN ('independent','adjudication','appeal')), \n\tFOREIGN KEY(reviewer_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_review_assignments_workspace_id ON review_assignments (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE review_decisions (\n\tassignment_id UUID NOT NULL, \n\tverdict VARCHAR(16) NOT NULL, \n\trationale VARCHAR(2000) NOT NULL, \n\tevidence JSONB NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (assignment_id), \n\tFOREIGN KEY(workspace_id, assignment_id) REFERENCES review_assignments (workspace_id, id) ON DELETE CASCADE, \n\tCHECK (verdict IN ('accepted','rejected') AND length(trim(rationale)) > 0 AND (verdict != 'rejected' OR jsonb_array_length(evidence) > 0)), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_review_decisions_workspace_id ON review_decisions (workspace_id)")
    op.execute(
        "\nCREATE TABLE appeals (\n\tcase_id UUID NOT NULL, \n\treason VARCHAR(2000) NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tcommand_key UUID NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (case_id), \n\tFOREIGN KEY(workspace_id, case_id) REFERENCES review_cases (workspace_id, id) ON DELETE CASCADE, \n\tCHECK (length(trim(reason)) > 0 AND state IN ('open','upheld','overturned')), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_appeals_workspace_id ON appeals (workspace_id)")
    op.execute(
        "\nCREATE TABLE financial_retention_policies (\n\tsettled_days INTEGER NOT NULL, \n\trationale VARCHAR(1000) NOT NULL, \n\treviewed_by UUID NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tCHECK (settled_days >= 0 AND settled_days <= 36500 AND length(trim(rationale)) > 0), \n\tFOREIGN KEY(reviewed_by) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_financial_retention_policies_workspace_id ON financial_retention_policies (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE reward_records (\n\tsource_key VARCHAR(100) NOT NULL, \n\tsubject_id UUID, \n\tamount_millimes BIGINT NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tretention_policy_id UUID NOT NULL, \n\tsettled_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, source_key), \n\tFOREIGN KEY(workspace_id, retention_policy_id) REFERENCES financial_retention_policies (workspace_id, id), \n\tCHECK (amount_millimes > 0 AND amount_millimes <= 1000000000000 AND currency = 'TND' AND state IN ('earned','paid')), \n\tFOREIGN KEY(subject_id) REFERENCES users (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_reward_records_workspace_id ON reward_records (workspace_id)")
    op.execute(
        "\nCREATE TABLE ledger_accounts (\n\tcode VARCHAR(24) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, code), \n\tCHECK (currency = 'TND' AND code IN ('expense','payable','manual_cash')), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_ledger_accounts_workspace_id ON ledger_accounts (workspace_id)")
    op.execute(
        "\nCREATE TABLE ledger_transactions (\n\tcommand_key VARCHAR(160) NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\treversal_of UUID, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, command_key), \n\tUNIQUE (reversal_of), \n\tFOREIGN KEY(workspace_id, reversal_of) REFERENCES ledger_transactions (workspace_id, id), \n\tCHECK (currency = 'TND'), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_ledger_transactions_workspace_id ON ledger_transactions (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE ledger_entries (\n\ttransaction_id UUID NOT NULL, \n\taccount_id UUID NOT NULL, \n\tamount_millimes BIGINT NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, transaction_id) REFERENCES ledger_transactions (workspace_id, id), \n\tFOREIGN KEY(workspace_id, account_id) REFERENCES ledger_accounts (workspace_id, id), \n\tCHECK (amount_millimes != 0 AND amount_millimes BETWEEN -1000000000000 AND 1000000000000), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_ledger_entries_workspace_id ON ledger_entries (workspace_id)")
    op.execute(
        "\nCREATE TABLE payout_records (\n\treward_id UUID NOT NULL, \n\tcommand_key UUID NOT NULL, \n\texternal_reference VARCHAR(120) NOT NULL, \n\tevidence VARCHAR(1000) NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\ttransaction_id UUID, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, external_reference), \n\tUNIQUE (workspace_id, command_key), \n\tFOREIGN KEY(workspace_id, reward_id) REFERENCES reward_records (workspace_id, id), \n\tCHECK (state IN ('recorded','failed','reversed') AND length(trim(evidence)) > 0), \n\tFOREIGN KEY(transaction_id) REFERENCES ledger_transactions (id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_payout_records_workspace_id ON payout_records (workspace_id)")
    op.execute(r"""
CREATE UNIQUE INDEX uq_payout_live ON payout_records(reward_id) WHERE state='recorded';
CREATE FUNCTION reviews_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable review or journal record'; END $$;
CREATE TRIGGER ledger_accounts_immutable BEFORE UPDATE OR DELETE ON ledger_accounts FOR EACH ROW EXECUTE FUNCTION reviews_immutable();
CREATE TRIGGER ledger_transactions_immutable BEFORE UPDATE OR DELETE ON ledger_transactions FOR EACH ROW EXECUTE FUNCTION reviews_immutable();
CREATE TRIGGER ledger_entries_immutable BEFORE UPDATE OR DELETE ON ledger_entries FOR EACH ROW EXECUTE FUNCTION reviews_immutable();
CREATE TRIGGER financial_policy_immutable BEFORE UPDATE OR DELETE ON financial_retention_policies FOR EACH ROW EXECUTE FUNCTION reviews_immutable();

CREATE FUNCTION reviews_journal_insert() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE tx ledger_transactions; account ledger_accounts;
BEGIN
 SELECT * INTO tx FROM ledger_transactions WHERE id=NEW.transaction_id FOR UPDATE;
 SELECT * INTO account FROM ledger_accounts WHERE id=NEW.account_id;
 IF tx.workspace_id IS DISTINCT FROM NEW.workspace_id OR account.workspace_id IS DISTINCT FROM NEW.workspace_id OR account.currency IS DISTINCT FROM tx.currency THEN RAISE EXCEPTION 'journal scope/currency mismatch'; END IF;
 IF NOT EXISTS(SELECT 1 FROM ledger_transactions WHERE id=NEW.transaction_id AND xmin::text=pg_current_xact_id()::text) THEN RAISE EXCEPTION 'cannot append to historical posting'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER journal_insert BEFORE INSERT ON ledger_entries FOR EACH ROW EXECUTE FUNCTION reviews_journal_insert();

CREATE FUNCTION reviews_journal_balance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE tid uuid; n integer; total numeric; original uuid;
BEGIN
 IF TG_TABLE_NAME='ledger_transactions' THEN tid=NEW.id; ELSE tid=NEW.transaction_id; END IF;
 SELECT count(*),sum(amount_millimes) INTO n,total FROM ledger_entries WHERE transaction_id=tid;
 IF n < 2 OR total IS DISTINCT FROM 0::numeric THEN RAISE EXCEPTION 'journal must balance'; END IF;
 SELECT reversal_of INTO original FROM ledger_transactions WHERE id=tid;
 IF original IS NOT NULL THEN
   IF EXISTS(SELECT 1 FROM ledger_transactions t JOIN reward_records r ON t.workspace_id=r.workspace_id AND t.command_key='earn:'||r.id::text WHERE t.id=original) THEN RAISE EXCEPTION 'earned obligation reversal unsupported'; END IF;
   IF EXISTS(SELECT 1 FROM payout_records p WHERE p.transaction_id=original AND p.state<>'reversed') THEN RAISE EXCEPTION 'payment reversal requires matching payment state'; END IF;
   IF EXISTS(SELECT 1 FROM ledger_transactions WHERE id=original AND reversal_of IS NOT NULL) THEN RAISE EXCEPTION 'cannot reverse a reversal'; END IF;
   IF EXISTS(SELECT account_id FROM ledger_entries WHERE transaction_id IN (tid,original) GROUP BY account_id HAVING sum(amount_millimes) <> 0) THEN RAISE EXCEPTION 'reversal must negate original accounts'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER journal_balanced_tx AFTER INSERT ON ledger_transactions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION reviews_journal_balance();
CREATE CONSTRAINT TRIGGER journal_balanced_entry AFTER INSERT ON ledger_entries DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION reviews_journal_balance();

CREATE FUNCTION reviews_assignment_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE subject uuid; source_state text;
BEGIN
 IF TG_OP='DELETE' THEN
  IF EXISTS(SELECT 1 FROM review_cases WHERE id=OLD.case_id) THEN RAISE EXCEPTION 'assignments retained until research purge'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'immutable assignment'; END IF;
 SELECT s.subject_id,s.state INTO subject,source_state FROM review_cases c JOIN collection_sessions s ON s.id=c.session_id WHERE c.id=NEW.case_id AND c.workspace_id=NEW.workspace_id;
 IF subject IS NULL OR subject=NEW.reviewer_id OR source_state <> 'submitted' THEN RAISE EXCEPTION 'self review or unavailable source'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER assignment_guard BEFORE INSERT OR UPDATE OR DELETE ON review_assignments FOR EACH ROW EXECUTE FUNCTION reviews_assignment_guard();

CREATE FUNCTION reviews_decision_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN
  IF EXISTS(SELECT 1 FROM review_assignments WHERE id=OLD.assignment_id) THEN RAISE EXCEPTION 'decisions retained until research purge'; END IF;
  RETURN OLD;
 END IF;
 IF TG_OP='UPDATE' THEN RAISE EXCEPTION 'immutable decision'; END IF;
 IF NOT EXISTS(SELECT 1 FROM review_assignments a JOIN review_cases c ON c.id=a.case_id JOIN collection_sessions s ON s.id=c.session_id WHERE a.id=NEW.assignment_id AND a.workspace_id=NEW.workspace_id AND s.state='submitted' AND a.reviewer_id<>s.subject_id) THEN RAISE EXCEPTION 'invalid decision source'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER decision_guard BEFORE INSERT OR UPDATE OR DELETE ON review_decisions FOR EACH ROW EXECUTE FUNCTION reviews_decision_guard();

CREATE FUNCTION reviews_reward_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'earned obligations cannot be deleted'; END IF;
 IF (to_jsonb(NEW)-'state'-'settled_at'-'subject_id') IS DISTINCT FROM (to_jsonb(OLD)-'state'-'settled_at'-'subject_id') THEN RAISE EXCEPTION 'immutable obligation'; END IF;
 IF NEW.subject_id IS DISTINCT FROM OLD.subject_id THEN
  IF NEW.subject_id IS NOT NULL OR OLD.state<>'paid' OR OLD.settled_at IS NULL OR NOT EXISTS(SELECT 1 FROM financial_retention_policies p WHERE p.id=OLD.retention_policy_id AND OLD.settled_at + make_interval(days=>p.settled_days)<=now()) THEN RAISE EXCEPTION 'preserve unsettled beneficiary'; END IF;
 END IF;
 IF NEW.state='earned' AND NEW.subject_id IS NULL THEN RAISE EXCEPTION 'cannot reopen minimized beneficiary'; END IF;
 IF (NEW.state='paid') IS DISTINCT FROM (NEW.settled_at IS NOT NULL) THEN RAISE EXCEPTION 'settlement time mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reward_guard BEFORE UPDATE OR DELETE ON reward_records FOR EACH ROW EXECUTE FUNCTION reviews_reward_guard();

CREATE FUNCTION reviews_payout_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'payment history retained'; END IF;
 IF TG_OP='UPDATE' AND ((to_jsonb(NEW)-'state') IS DISTINCT FROM (to_jsonb(OLD)-'state') OR NOT(OLD.state='recorded' AND NEW.state='reversed')) THEN RAISE EXCEPTION 'only payment reversal permitted'; END IF;
 IF (NEW.state='failed') IS DISTINCT FROM (NEW.transaction_id IS NULL) THEN RAISE EXCEPTION 'failed payments cannot post'; END IF;
 IF NEW.transaction_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ledger_transactions t WHERE t.id=NEW.transaction_id AND t.workspace_id=NEW.workspace_id AND t.reversal_of IS NULL) THEN RAISE EXCEPTION 'payment posting scope'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER payout_guard BEFORE INSERT OR UPDATE OR DELETE ON payout_records FOR EACH ROW EXECUTE FUNCTION reviews_payout_guard();

CREATE FUNCTION reviews_settlement_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE rid uuid; reward reward_records; live_count integer; net numeric;
BEGIN
 IF TG_TABLE_NAME='reward_records' THEN rid=NEW.id; ELSE rid=NEW.reward_id; END IF;
 SELECT * INTO reward FROM reward_records WHERE id=rid;
 SELECT count(*) INTO live_count FROM payout_records WHERE reward_id=rid AND state='recorded';
 IF (reward.state='paid' AND live_count<>1) OR (reward.state='earned' AND live_count<>0) THEN RAISE EXCEPTION 'full settlement state mismatch'; END IF;
 IF NOT EXISTS(SELECT 1 FROM ledger_transactions t JOIN ledger_entries e ON e.transaction_id=t.id JOIN ledger_accounts a ON a.id=e.account_id WHERE t.workspace_id=reward.workspace_id AND t.command_key='earn:'||rid::text AND a.code='payable' GROUP BY t.id HAVING sum(e.amount_millimes)=-reward.amount_millimes) THEN RAISE EXCEPTION 'obligation needs full earning journal'; END IF;
 IF EXISTS(SELECT 1 FROM payout_records p WHERE p.reward_id=rid AND p.transaction_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=p.transaction_id AND a.code='payable' GROUP BY e.transaction_id HAVING sum(e.amount_millimes)=reward.amount_millimes)) THEN RAISE EXCEPTION 'partial or incorrect payment posting'; END IF;
 IF EXISTS(SELECT 1 FROM payout_records p JOIN ledger_transactions t ON t.reversal_of=p.transaction_id WHERE p.reward_id=rid AND p.state<>'reversed') THEN RAISE EXCEPTION 'reversed posting cannot remain recorded'; END IF;
 IF EXISTS(SELECT 1 FROM payout_records p WHERE p.reward_id=rid AND p.state='reversed' AND NOT EXISTS(SELECT 1 FROM ledger_transactions t WHERE t.reversal_of=p.transaction_id)) THEN RAISE EXCEPTION 'payment reversal needs journal'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER reward_settlement AFTER INSERT OR UPDATE ON reward_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION reviews_settlement_guard();
CREATE CONSTRAINT TRIGGER payout_settlement AFTER INSERT OR UPDATE ON payout_records DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION reviews_settlement_guard();
""")

    op.execute(r"""
CREATE FUNCTION reviews_case_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE verdict text; assignment_kind text; case_ref uuid; votes integer; distinct_votes integer;
BEGIN
 IF TG_OP='INSERT' THEN
  IF NEW.state<>'pending' OR NEW.generation<>0 OR NEW.final_decision_id IS NOT NULL THEN RAISE EXCEPTION 'new review must be pending'; END IF;
  RETURN NEW;
 END IF;
 IF NEW.workspace_id<>OLD.workspace_id OR NEW.session_id<>OLD.session_id OR NEW.id<>OLD.id OR NEW.generation<OLD.generation THEN RAISE EXCEPTION 'immutable case identity/generation'; END IF;
 IF NEW.state IS DISTINCT FROM OLD.state AND NEW.generation<=OLD.generation THEN RAISE EXCEPTION 'review change needs generation'; END IF;
 IF NEW.state IN ('accepted','rejected') THEN
  SELECT d.verdict,a.kind,a.case_id INTO verdict,assignment_kind,case_ref FROM review_decisions d JOIN review_assignments a ON a.id=d.assignment_id WHERE d.id=NEW.final_decision_id;
  IF case_ref IS DISTINCT FROM NEW.id OR verdict IS DISTINCT FROM NEW.state THEN RAISE EXCEPTION 'final outcome requires own human decision'; END IF;
  IF assignment_kind='independent' THEN
   SELECT count(*),count(DISTINCT d.verdict) INTO votes,distinct_votes FROM review_decisions d JOIN review_assignments a ON a.id=d.assignment_id WHERE a.case_id=NEW.id AND a.kind='independent';
   IF votes<>2 OR distinct_votes<>1 THEN RAISE EXCEPTION 'independent consensus requires two votes'; END IF;
  END IF;
  IF NEW.state='accepted' AND NEW.accepted_at IS NULL THEN RAISE EXCEPTION 'accepted time required'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER review_case_guard BEFORE INSERT OR UPDATE ON review_cases FOR EACH ROW EXECUTE FUNCTION reviews_case_guard();
""")


def downgrade():
    for name in (
        "payout_records",
        "ledger_entries",
        "ledger_transactions",
        "ledger_accounts",
        "reward_records",
        "financial_retention_policies",
        "appeals",
        "review_decisions",
        "review_assignments",
        "quality_flags",
        "review_cases",
    ):
        op.execute("DROP TABLE " + name + " CASCADE")
    for name in (
        "reviews_case_guard",
        "reviews_immutable",
        "reviews_journal_insert",
        "reviews_journal_balance",
        "reviews_assignment_guard",
        "reviews_decision_guard",
        "reviews_reward_guard",
        "reviews_payout_guard",
        "reviews_settlement_guard",
    ):
        op.execute("DROP FUNCTION " + name + "()")
    op.execute("ALTER TABLE collection_sessions DROP CONSTRAINT uq_collection_session_scope")
