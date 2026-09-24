"""Commercial snapshots and guards atop the P08 journal."""

from alembic import op

revision = "015_billing"
down_revision = "014_templates"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE billing_plan_versions (\n\tkey VARCHAR(80) NOT NULL, \n\tversion INTEGER NOT NULL, \n\tsnapshot JSONB NOT NULL, \n\treviewed_by UUID NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, key, version), \n\tCHECK (version > 0), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_billing_plan_versions_workspace_id ON billing_plan_versions (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE billing_subscriptions (\n\tplan_id UUID NOT NULL, \n\tstarts_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tends_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcancelled_at TIMESTAMP WITH TIME ZONE, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tFOREIGN KEY(workspace_id, plan_id) REFERENCES billing_plan_versions (workspace_id, id), \n\tCHECK (ends_at > starts_at), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_billing_subscriptions_workspace_id ON billing_subscriptions (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE billing_grants (\n\tsubscription_id UUID NOT NULL, \n\tsource_id UUID NOT NULL, \n\tkind VARCHAR(24) NOT NULL, \n\tunits INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tFOREIGN KEY(workspace_id, subscription_id) REFERENCES billing_subscriptions (workspace_id, id), \n\tUNIQUE (workspace_id, source_id), \n\tCHECK (kind IN ('publication','response','ai_addon','specialist') AND units > 0 AND units <= 1000000), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_billing_grants_workspace_id ON billing_grants (workspace_id)")
    op.execute(
        "\nCREATE TABLE billing_usage (\n\tsubscription_id UUID NOT NULL, \n\tsource_id UUID NOT NULL, \n\tkind VARCHAR(24) NOT NULL, \n\tstate VARCHAR(16) NOT NULL, \n\tnet BIGINT NOT NULL, \n\ttax BIGINT NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tFOREIGN KEY(workspace_id, subscription_id) REFERENCES billing_subscriptions (workspace_id, id), \n\tUNIQUE (workspace_id, kind, source_id), \n\tCHECK (kind IN ('publication','response','ai_addon','specialist') AND state IN ('reserved','consumed','released')), \n\tCHECK (net >= 0 AND tax >= 0 AND net + tax <= 1000000000000), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_billing_usage_workspace_id ON billing_usage (workspace_id)")
    op.execute(
        "\nCREATE TABLE billing_invoices (\n\tsubscription_id UUID NOT NULL, \n\tcommand_id UUID NOT NULL, \n\tcredit_of UUID, \n\ttransaction_id UUID NOT NULL, \n\tsnapshot JSONB NOT NULL, \n\tnet BIGINT NOT NULL, \n\ttax BIGINT NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tUNIQUE (workspace_id, command_id), \n\tFOREIGN KEY(workspace_id, subscription_id) REFERENCES billing_subscriptions (workspace_id, id), \n\tFOREIGN KEY(workspace_id, transaction_id) REFERENCES ledger_transactions (workspace_id, id), \n\tFOREIGN KEY(workspace_id, credit_of) REFERENCES billing_invoices (workspace_id, id), \n\tUNIQUE (credit_of), \n\tCHECK (net >= 0 AND tax >= 0 AND net + tax > 0 AND net + tax <= 1000000000000), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_billing_invoices_workspace_id ON billing_invoices (workspace_id)")
    op.execute(
        "\nCREATE TABLE billing_invoice_lines (\n\tinvoice_id UUID NOT NULL, \n\tusage_id UUID NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(workspace_id, invoice_id) REFERENCES billing_invoices (workspace_id, id), \n\tFOREIGN KEY(workspace_id, usage_id) REFERENCES billing_usage (workspace_id, id), \n\tUNIQUE (usage_id), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_billing_invoice_lines_workspace_id ON billing_invoice_lines (workspace_id)"
    )
    op.execute(
        "\nCREATE TABLE billing_customer_payments (\n\tinvoice_id UUID NOT NULL, \n\ttransaction_id UUID NOT NULL, \n\tcommand_id UUID NOT NULL, \n\treversal_of UUID, \n\treference VARCHAR(120) NOT NULL, \n\tevidence_digest VARCHAR(64) NOT NULL, \n\tamount BIGINT NOT NULL, \n\tid UUID NOT NULL, \n\tworkspace_id UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (workspace_id, id), \n\tFOREIGN KEY(workspace_id, invoice_id) REFERENCES billing_invoices (workspace_id, id), \n\tFOREIGN KEY(workspace_id, transaction_id) REFERENCES ledger_transactions (workspace_id, id), \n\tFOREIGN KEY(workspace_id, reversal_of) REFERENCES billing_customer_payments (workspace_id, id), \n\tUNIQUE (reversal_of), \n\tUNIQUE (workspace_id, command_id), \n\tUNIQUE (workspace_id, reference), \n\tCHECK (amount > 0 AND amount <= 1000000000000), \n\tFOREIGN KEY(workspace_id) REFERENCES workspaces (id)\n)\n\n"
    )
    op.execute(
        "CREATE INDEX ix_billing_customer_payments_workspace_id ON billing_customer_payments (workspace_id)"
    )
    op.execute("ALTER TABLE billing_invoices ADD UNIQUE(transaction_id)")
    op.execute("ALTER TABLE billing_customer_payments ADD UNIQUE(transaction_id)")
    op.execute(r"""
DO $$ DECLARE c text; BEGIN
 FOR c IN SELECT conname FROM pg_constraint WHERE conrelid='ledger_accounts'::regclass AND contype='c' LOOP
 EXECUTE format('ALTER TABLE ledger_accounts DROP CONSTRAINT %I',c);
 END LOOP;
END $$;
ALTER TABLE ledger_accounts ADD CONSTRAINT billing_account_codes CHECK(currency='TND' AND code IN ('expense','payable','manual_cash','customer_receivable','billing_revenue','billing_tax'));
CREATE FUNCTION billing_plan_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r jsonb; k text; v numeric;
BEGIN
 r=NEW.snapshot;
 IF length(coalesce(r->>'supplier_reference',''))=0 OR length(coalesce(r->>'customer_reference',''))=0 OR length(coalesce(r->>'tax_reference',''))=0 THEN RAISE EXCEPTION 'invoice identity references required'; END IF;
 IF r->>'currency' IS DISTINCT FROM 'TND' OR r->>'exponent' IS DISTINCT FROM '3' OR r->>'rounding' IS DISTINCT FROM 'half_up' OR r->>'payment_policy' IS DISTINCT FROM 'full_settlement_only' OR length(coalesce(r->>'reviewed_rules_reference',''))=0 THEN RAISE EXCEPTION 'reviewed rules required'; END IF;
 FOREACH k IN ARRAY ARRAY['tax_numerator','tax_denominator','retention_days','budget','operational_limit'] LOOP
 IF jsonb_typeof(r->k) IS DISTINCT FROM 'number' OR (r->>k) !~ '^\d+$' THEN RAISE EXCEPTION 'integer rule required'; END IF;
 END LOOP;
 IF (r->>'tax_numerator')::numeric NOT BETWEEN 0 AND 1000000 OR (r->>'tax_denominator')::numeric NOT BETWEEN 1 AND 1000000 OR (r->>'retention_days')::numeric NOT BETWEEN 0 AND 36500 OR (r->>'budget')::numeric NOT BETWEEN 0 AND 1000000000000 OR (r->>'operational_limit')::numeric NOT BETWEEN 1 AND 1000000 THEN RAISE EXCEPTION 'invalid bounds'; END IF;
 FOREACH k IN ARRAY ARRAY['publication','response','ai_addon','specialist'] LOOP
 IF jsonb_typeof(r->'rates'->k->'price') IS DISTINCT FROM 'number' OR jsonb_typeof(r->'rates'->k->'quota') IS DISTINCT FROM 'number' OR (r->'rates'->k->>'price') !~ '^\d+$' OR (r->'rates'->k->>'quota') !~ '^\d+$' THEN RAISE EXCEPTION 'finite rate required'; END IF;
 IF jsonb_typeof(r->'rates'->k->'included_units') IS DISTINCT FROM 'number' OR (r->'rates'->k->>'included_units') !~ '^\d+$' OR (r->'rates'->k->>'included_units')::numeric NOT BETWEEN 0 AND (r->'rates'->k->>'quota')::numeric THEN RAISE EXCEPTION 'finite allowance required'; END IF;
 v=(r->'rates'->k->>'price')::numeric;
 IF v NOT BETWEEN 0 AND 1000000000000 OR (r->'rates'->k->>'quota')::numeric NOT BETWEEN 0 AND 1000000 OR v+floor((2*v*(r->>'tax_numerator')::numeric+(r->>'tax_denominator')::numeric)/(2*(r->>'tax_denominator')::numeric))>1000000000000 THEN RAISE EXCEPTION 'invalid rate'; END IF;
 END LOOP;
 IF NOT EXISTS(SELECT 1 FROM memberships WHERE workspace_id=NEW.workspace_id AND user_id=NEW.reviewed_by AND status='active' AND role IN ('owner','admin')) THEN RAISE EXCEPTION 'reviewer required'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER billing_plan_review BEFORE INSERT ON billing_plan_versions FOR EACH ROW EXECUTE FUNCTION billing_plan_guard();
CREATE FUNCTION billing_subscription_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 PERFORM 1 FROM workspaces WHERE id=NEW.workspace_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN
 IF (to_jsonb(NEW)-'cancelled_at') IS DISTINCT FROM (to_jsonb(OLD)-'cancelled_at') OR OLD.cancelled_at IS NOT NULL OR NEW.cancelled_at IS NULL OR NEW.cancelled_at < CURRENT_TIMESTAMP THEN RAISE EXCEPTION 'immutable subscription period'; END IF;
 ELSE
 IF NEW.cancelled_at IS NOT NULL OR EXISTS(SELECT 1 FROM billing_subscriptions s WHERE s.workspace_id=NEW.workspace_id AND NEW.starts_at<least(s.ends_at,coalesce(s.cancelled_at,s.ends_at)) AND s.starts_at<NEW.ends_at) THEN RAISE EXCEPTION 'overlapping subscription'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER billing_subscription_period BEFORE INSERT OR UPDATE ON billing_subscriptions FOR EACH ROW EXECUTE FUNCTION billing_subscription_guard();
CREATE TRIGGER billing_subscription_retained BEFORE DELETE ON billing_subscriptions FOR EACH ROW EXECUTE FUNCTION reviews_immutable();
CREATE FUNCTION billing_usage_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE sub billing_subscriptions; r jsonb; n bigint; extra bigint; total numeric; operational bigint; price numeric; tax numeric;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=NEW.workspace_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN
 IF (to_jsonb(NEW)-'state') IS DISTINCT FROM (to_jsonb(OLD)-'state') OR OLD.state<>'reserved' OR NEW.state NOT IN ('consumed','released') THEN RAISE EXCEPTION 'invalid usage transition'; END IF;
 RETURN NEW;
 END IF;
 SELECT * INTO sub FROM billing_subscriptions WHERE id=NEW.subscription_id AND workspace_id=NEW.workspace_id;
 IF sub.id IS NULL OR CURRENT_TIMESTAMP<sub.starts_at OR CURRENT_TIMESTAMP>=sub.ends_at OR sub.cancelled_at IS NOT NULL OR NEW.state<>'reserved' THEN RAISE EXCEPTION 'inactive subscription'; END IF;
 SELECT snapshot INTO r FROM billing_plan_versions WHERE id=sub.plan_id;
 SELECT count(*) FILTER(WHERE u.kind=NEW.kind),count(*),coalesce(sum(u.net+u.tax),0) INTO n,operational,total FROM billing_usage u WHERE u.subscription_id=sub.id AND u.state<>'released';
 SELECT coalesce(sum(units),0) INTO extra FROM billing_grants WHERE subscription_id=sub.id AND kind=NEW.kind;
 IF NEW.kind<>'specialist' THEN extra=extra+(r->'rates'->NEW.kind->>'quota')::bigint; END IF;
 price=CASE WHEN n<(r->'rates'->NEW.kind->>'included_units')::bigint THEN 0 ELSE (r->'rates'->NEW.kind->>'price')::numeric END;
 tax=floor((2*price*(r->>'tax_numerator')::numeric+(r->>'tax_denominator')::numeric)/(2*(r->>'tax_denominator')::numeric));
 IF NEW.net<>price OR NEW.tax<>tax OR n>=extra OR operational>=(r->>'operational_limit')::bigint OR total+NEW.net+NEW.tax>(r->>'budget')::numeric THEN RAISE EXCEPTION 'quota budget or rate violation'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER billing_usage_transition BEFORE INSERT OR UPDATE ON billing_usage FOR EACH ROW EXECUTE FUNCTION billing_usage_guard();
CREATE TRIGGER billing_usage_retained BEFORE DELETE ON billing_usage FOR EACH ROW EXECUTE FUNCTION reviews_immutable();
CREATE FUNCTION billing_finance_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE inv billing_invoices; original billing_invoices; pay billing_customer_payments; tx ledger_transactions; n numeric; t numeric; expected_sign int;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=NEW.workspace_id FOR UPDATE;
 IF TG_TABLE_NAME='billing_invoice_lines' THEN
 SELECT * INTO inv FROM billing_invoices WHERE id=NEW.invoice_id;
 IF NOT EXISTS(SELECT 1 FROM billing_invoices WHERE id=inv.id AND xmin::text=pg_current_xact_id()::text) OR inv.credit_of IS NOT NULL OR NOT EXISTS(SELECT 1 FROM billing_usage u WHERE u.id=NEW.usage_id AND u.subscription_id=inv.subscription_id AND u.state='consumed') THEN RAISE EXCEPTION 'invalid invoice source'; END IF;
 RETURN NEW;
 END IF;
 SELECT * INTO tx FROM ledger_transactions WHERE id=NEW.transaction_id AND workspace_id=NEW.workspace_id;
 IF tx.id IS NULL OR NOT EXISTS(SELECT 1 FROM ledger_transactions WHERE id=tx.id AND xmin::text=pg_current_xact_id()::text) THEN RAISE EXCEPTION 'fresh journal required'; END IF;
 IF TG_TABLE_NAME='billing_invoices' THEN
 inv=NEW; expected_sign=1;
 IF inv.credit_of IS NOT NULL THEN
 SELECT * INTO original FROM billing_invoices WHERE id=inv.credit_of AND workspace_id=inv.workspace_id;
 IF original.credit_of IS NOT NULL OR inv.net<>original.net OR inv.tax<>original.tax OR inv.snapshot<>original.snapshot OR inv.subscription_id<>original.subscription_id OR tx.reversal_of IS DISTINCT FROM original.transaction_id THEN RAISE EXCEPTION 'invalid credit'; END IF;
 IF EXISTS(SELECT 1 FROM billing_customer_payments p WHERE p.invoice_id=original.id AND p.reversal_of IS NULL AND NOT EXISTS(SELECT 1 FROM billing_customer_payments x WHERE x.reversal_of=p.id)) THEN RAISE EXCEPTION 'reverse payment before credit'; END IF;
 expected_sign=-1;
 ELSE
 SELECT coalesce(sum(u.net),0),coalesce(sum(u.tax),0) INTO n,t FROM billing_invoice_lines l JOIN billing_usage u ON u.id=l.usage_id WHERE l.invoice_id=inv.id;
 IF n<>inv.net OR t<>inv.tax OR tx.reversal_of IS NOT NULL OR inv.snapshot IS DISTINCT FROM (SELECT p.snapshot FROM billing_subscriptions s JOIN billing_plan_versions p ON p.id=s.plan_id WHERE s.id=inv.subscription_id) THEN RAISE EXCEPTION 'invoice totals or snapshot mismatch'; END IF;
 END IF;
 IF EXISTS(SELECT 1 FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=tx.id AND a.code NOT IN ('customer_receivable','billing_revenue','billing_tax')) THEN RAISE EXCEPTION 'wrong invoice accounts'; END IF;
 IF (SELECT coalesce(sum(e.amount_millimes),0) FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=tx.id AND a.code='customer_receivable')<>(inv.net+inv.tax)*expected_sign OR (SELECT coalesce(sum(e.amount_millimes),0) FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=tx.id AND a.code='billing_revenue')<>-inv.net*expected_sign OR (SELECT coalesce(sum(e.amount_millimes),0) FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=tx.id AND a.code='billing_tax')<>-inv.tax*expected_sign THEN RAISE EXCEPTION 'invoice journal mismatch'; END IF;
 ELSE
 SELECT * INTO inv FROM billing_invoices WHERE id=NEW.invoice_id;
 expected_sign=1;
 IF NEW.reversal_of IS NOT NULL THEN
 SELECT * INTO pay FROM billing_customer_payments WHERE id=NEW.reversal_of;
 IF pay.reversal_of IS NOT NULL OR NEW.amount<>pay.amount OR NEW.invoice_id<>pay.invoice_id OR tx.reversal_of IS DISTINCT FROM pay.transaction_id THEN RAISE EXCEPTION 'invalid payment reversal'; END IF;
 expected_sign=-1;
 ELSE
 IF NEW.amount<>inv.net+inv.tax OR inv.credit_of IS NOT NULL OR EXISTS(SELECT 1 FROM billing_invoices WHERE credit_of=inv.id) OR tx.reversal_of IS NOT NULL THEN RAISE EXCEPTION 'full settlement required'; END IF;
 IF (SELECT count(*) FROM billing_customer_payments p WHERE p.invoice_id=inv.id AND p.reversal_of IS NULL AND NOT EXISTS(SELECT 1 FROM billing_customer_payments x WHERE x.reversal_of=p.id))>1 THEN RAISE EXCEPTION 'already paid'; END IF;
 END IF;
 IF NEW.evidence_digest !~ '^[a-f0-9]{64}$' OR EXISTS(SELECT 1 FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=tx.id AND a.code NOT IN ('manual_cash','customer_receivable')) OR (SELECT coalesce(sum(e.amount_millimes),0) FROM ledger_entries e JOIN ledger_accounts a ON a.id=e.account_id WHERE e.transaction_id=tx.id AND a.code='manual_cash')<>NEW.amount*expected_sign THEN RAISE EXCEPTION 'payment journal mismatch'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER billing_invoice_line_source BEFORE INSERT ON billing_invoice_lines FOR EACH ROW EXECUTE FUNCTION billing_finance_guard();
CREATE CONSTRAINT TRIGGER billing_invoice_posting AFTER INSERT ON billing_invoices DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION billing_finance_guard();
CREATE CONSTRAINT TRIGGER billing_payment_posting AFTER INSERT ON billing_customer_payments DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION billing_finance_guard();
CREATE FUNCTION billing_reversal_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.reversal_of IS NOT NULL THEN
 IF EXISTS(SELECT 1 FROM billing_invoices i WHERE i.transaction_id=NEW.reversal_of) AND NOT EXISTS(SELECT 1 FROM billing_invoices i JOIN billing_invoices c ON c.credit_of=i.id WHERE i.transaction_id=NEW.reversal_of AND c.transaction_id=NEW.id) THEN RAISE EXCEPTION 'credit record required'; END IF;
 IF EXISTS(SELECT 1 FROM billing_customer_payments p WHERE p.transaction_id=NEW.reversal_of) AND NOT EXISTS(SELECT 1 FROM billing_customer_payments p JOIN billing_customer_payments r ON r.reversal_of=p.id WHERE p.transaction_id=NEW.reversal_of AND r.transaction_id=NEW.id) THEN RAISE EXCEPTION 'payment reversal record required'; END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER billing_linked_reversal AFTER INSERT ON ledger_transactions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION billing_reversal_guard();
""")
    for table in (
        "billing_plan_versions",
        "billing_grants",
        "billing_invoices",
        "billing_invoice_lines",
        "billing_customer_payments",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reviews_immutable()"
        )


def downgrade():
    op.execute("DROP TRIGGER billing_linked_reversal ON ledger_transactions")
    for table in (
        "billing_customer_payments",
        "billing_invoice_lines",
        "billing_invoices",
        "billing_usage",
        "billing_grants",
        "billing_subscriptions",
        "billing_plan_versions",
    ):
        op.drop_table(table)
    for name in (
        "billing_reversal_guard",
        "billing_finance_guard",
        "billing_usage_guard",
        "billing_subscription_guard",
        "billing_plan_guard",
    ):
        op.execute(f"DROP FUNCTION {name}()")
    # Preserve historical commercial journal rows; constrain only subsequent legacy writes.
    op.execute("ALTER TABLE ledger_accounts DROP CONSTRAINT billing_account_codes")
    op.execute(
        "ALTER TABLE ledger_accounts ADD CHECK(currency='TND' AND code IN ('expense','payable','manual_cash')) NOT VALID"
    )
