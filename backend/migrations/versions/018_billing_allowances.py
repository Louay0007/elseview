"""Track included holds independently of paid usage.

Positive-price historical allocations are exactly identifiable by net=0, including
released rows. Zero-price history has no release timestamps, so original hold
occupancy cannot be reconstructed. Assign the earliest live rows (created_at, id)
up to the allowance; released zero-price rows receive false. This canonicalizes
indistinguishable zero-price allocations without altering financial history.
"""

from alembic import op

revision = "018_billing_allowances"
down_revision = "017_privacy_ops"
branch_labels = None
depends_on = None

OLD_GUARD = r"""CREATE OR REPLACE FUNCTION billing_usage_guard() RETURNS trigger LANGUAGE plpgsql AS $$
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
"""

NEW_GUARD = r"""CREATE OR REPLACE FUNCTION billing_usage_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE sub billing_subscriptions; r jsonb; n bigint; allocated bigint; included boolean; extra bigint; total numeric; operational bigint; price numeric; tax numeric;
BEGIN
 PERFORM 1 FROM workspaces WHERE id=NEW.workspace_id FOR UPDATE;
 IF TG_OP='UPDATE' THEN
 IF (to_jsonb(NEW)-'state') IS DISTINCT FROM (to_jsonb(OLD)-'state') OR OLD.state<>'reserved' OR NEW.state NOT IN ('consumed','released') THEN RAISE EXCEPTION 'invalid usage transition'; END IF;
 RETURN NEW;
 END IF;
 SELECT * INTO sub FROM billing_subscriptions WHERE id=NEW.subscription_id AND workspace_id=NEW.workspace_id;
 IF sub.id IS NULL OR CURRENT_TIMESTAMP<sub.starts_at OR CURRENT_TIMESTAMP>=sub.ends_at OR sub.cancelled_at IS NOT NULL OR NEW.state<>'reserved' THEN RAISE EXCEPTION 'inactive subscription'; END IF;
 SELECT snapshot INTO r FROM billing_plan_versions WHERE id=sub.plan_id;
 SELECT count(*) FILTER(WHERE u.kind=NEW.kind),count(*),coalesce(sum(u.net+u.tax),0) ,count(*) FILTER(WHERE u.kind=NEW.kind AND u.included_allocation) INTO n,operational,total,allocated FROM billing_usage u WHERE u.subscription_id=sub.id AND u.state<>'released';
 SELECT coalesce(sum(units),0) INTO extra FROM billing_grants WHERE subscription_id=sub.id AND kind=NEW.kind;
 IF NEW.kind<>'specialist' THEN extra=extra+(r->'rates'->NEW.kind->>'quota')::bigint; END IF;
 included=allocated<(r->'rates'->NEW.kind->>'included_units')::bigint;
 price=CASE WHEN included THEN 0 ELSE (r->'rates'->NEW.kind->>'price')::numeric END;
 tax=floor((2*price*(r->>'tax_numerator')::numeric+(r->>'tax_denominator')::numeric)/(2*(r->>'tax_denominator')::numeric));
 IF NEW.included_allocation IS DISTINCT FROM included OR NEW.net<>price OR NEW.tax<>tax OR n>=extra OR operational>=(r->>'operational_limit')::bigint OR total+NEW.net+NEW.tax>(r->>'budget')::numeric THEN RAISE EXCEPTION 'quota budget or rate violation'; END IF;
 RETURN NEW;
END $$;
"""


def upgrade():
    op.execute("ALTER TABLE billing_usage ADD COLUMN included_allocation boolean")
    op.execute("ALTER TABLE billing_usage DISABLE TRIGGER billing_usage_transition")
    op.execute("""
        WITH history AS (
          SELECT u.id, u.net, u.state,
            (p.snapshot->'rates'->u.kind->>'price')::bigint AS price,
            (p.snapshot->'rates'->u.kind->>'included_units')::bigint AS allowance,
            count(*) FILTER (WHERE u.state <> 'released') OVER (
              PARTITION BY u.subscription_id, u.kind ORDER BY u.created_at, u.id
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS live_ordinal
          FROM billing_usage u JOIN billing_subscriptions s ON s.id=u.subscription_id
          JOIN billing_plan_versions p ON p.id=s.plan_id
        )
        UPDATE billing_usage u SET included_allocation = CASE
          WHEN h.price > 0 THEN h.net = 0
          ELSE h.state <> 'released' AND h.live_ordinal <= h.allowance END
        FROM history h WHERE h.id=u.id
    """)
    op.execute("ALTER TABLE billing_usage ALTER COLUMN included_allocation SET NOT NULL")
    op.execute(NEW_GUARD)
    op.execute("ALTER TABLE billing_usage ENABLE TRIGGER billing_usage_transition")


def downgrade():
    op.execute(OLD_GUARD)
    op.execute("ALTER TABLE billing_usage DROP COLUMN included_allocation")
