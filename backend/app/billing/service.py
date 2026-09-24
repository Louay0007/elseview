"""Caller-owned atomic commands; serial workspace lock precedes quota and money effects."""

from sqlalchemy import func, select

from app.auth.security import utcnow
from app.auth.service import require_workspace
from app.billing.models import (
    CustomerPayment,
    Grant,
    Invoice,
    InvoiceLine,
    PlanVersion,
    Subscription,
    Usage,
)
from app.common.errors import DomainError
from app.common.privacy import lock_workspace
from app.reviews.service import post


def fail(code="BILLING_CONFLICT", status=409):
    raise DomainError(code, "Commercial command unavailable.", status)


def authorize(session, wid, actor):
    lock_workspace(session, wid)
    require_workspace(session, actor, wid, "members.manage")


def scoped(session, model, wid, id):
    row = session.scalar(select(model).where(model.workspace_id == wid, model.id == id))
    if not row:
        fail("NOT_FOUND", 404)
    return row


def tax_amount(net, numerator, denominator):
    if (
        any(type(x) is not int for x in (net, numerator, denominator))
        or not 0 <= net <= 10**12
        or not 0 <= numerator <= 10**6
        or not 0 < denominator <= 10**6
    ):
        fail("INVALID_MONEY", 422)
    tax = (2 * net * numerator + denominator) // (2 * denominator)
    if net + tax > 10**12:
        fail("INVALID_MONEY", 422)
    return tax


def create_plan(session, wid, actor, body):
    authorize(session, wid, actor)
    old = session.scalar(
        select(PlanVersion).where(
            PlanVersion.workspace_id == wid,
            PlanVersion.key == body.key,
            PlanVersion.version == body.version,
        )
    )
    snapshot = body.rules.model_dump()
    if old:
        if old.snapshot != snapshot:
            fail("IDEMPOTENCY_CONFLICT")
        return old
    row = PlanVersion(
        workspace_id=wid, key=body.key, version=body.version, snapshot=snapshot, reviewed_by=actor
    )
    session.add(row)
    session.flush()
    return row


def activate(session, wid, actor, body):
    authorize(session, wid, actor)
    scoped(session, PlanVersion, wid, body.plan_id)
    if body.ends_at <= utcnow():
        fail("INVALID_PERIOD", 422)
    rows = session.scalars(select(Subscription).where(Subscription.workspace_id == wid)).all()
    for old in rows:
        if (
            old.plan_id == body.plan_id
            and old.starts_at == body.starts_at
            and old.ends_at == body.ends_at
        ):
            return old
        end = min(old.ends_at, old.cancelled_at) if old.cancelled_at else old.ends_at
        if body.starts_at < end and old.starts_at < body.ends_at:
            fail("OVERLAPPING_SUBSCRIPTION")
    # Subsequent purchases cannot backdate into historical usage.
    if rows and body.starts_at < utcnow():
        fail("PLAN_CHANGE_FUTURE_ONLY")
    row = Subscription(workspace_id=wid, **body.model_dump())
    session.add(row)
    session.flush()
    return row


def cancel(session, wid, actor, id):
    authorize(session, wid, actor)
    row = scoped(session, Subscription, wid, id)
    if row.cancelled_at is None:
        row.cancelled_at = utcnow()
    session.flush()
    return row


def grant(session, wid, actor, body):
    authorize(session, wid, actor)
    scoped(session, Subscription, wid, body.subscription_id)
    old = session.scalar(
        select(Grant).where(Grant.workspace_id == wid, Grant.source_id == body.source_id)
    )
    if old:
        if any(getattr(old, k) != v for k, v in body.model_dump().items()):
            fail("IDEMPOTENCY_CONFLICT")
        return old
    row = Grant(workspace_id=wid, **body.model_dump())
    session.add(row)
    session.flush()
    return row


def reserve(session, wid, source_id, kind):
    lock_workspace(session, wid)
    old = session.scalar(
        select(Usage).where(
            Usage.workspace_id == wid, Usage.kind == kind, Usage.source_id == source_id
        )
    )
    if old:
        if old.state == "released":
            fail("RESERVATION_RELEASED")
        return old
    subscriptions = session.scalars(
        select(Subscription).where(Subscription.workspace_id == wid)
    ).all()
    now = utcnow()
    if not subscriptions:
        return None
    sub = next(
        (
            s
            for s in subscriptions
            if s.starts_at <= now < s.ends_at and (s.cancelled_at is None or now < s.cancelled_at)
        ),
        None,
    )
    if sub is None:
        if all(s.starts_at > now for s in subscriptions):
            return None
        fail("SUBSCRIPTION_INACTIVE")
    rules = scoped(session, PlanVersion, wid, sub.plan_id).snapshot
    rate = rules["rates"][kind]
    extra = session.scalar(
        select(func.coalesce(func.sum(Grant.units), 0)).where(
            Grant.subscription_id == sub.id, Grant.kind == kind
        )
    )
    usages = session.scalars(
        select(Usage).where(Usage.subscription_id == sub.id, Usage.state != "released")
    ).all()
    limit = extra + (0 if kind == "specialist" else rate["quota"])
    if sum(u.kind == kind for u in usages) >= limit or len(usages) >= rules["operational_limit"]:
        fail("BILLING_QUOTA_EXCEEDED")
    included = (
        sum(u.kind == kind and u.included_allocation for u in usages) < rate["included_units"]
    )
    net = 0 if included else rate["price"]
    tax = tax_amount(net, rules["tax_numerator"], rules["tax_denominator"])
    if sum(u.net + u.tax for u in usages) + net + tax > rules["budget"]:
        fail("BILLING_BUDGET_EXCEEDED")
    row = Usage(
        workspace_id=wid,
        subscription_id=sub.id,
        source_id=source_id,
        kind=kind,
        state="reserved",
        included_allocation=included,
        net=net,
        tax=tax,
    )
    session.add(row)
    session.flush()
    return row


def finish(session, wid, source_id, kind, release=False):
    lock_workspace(session, wid)
    row = session.scalar(
        select(Usage).where(
            Usage.workspace_id == wid, Usage.kind == kind, Usage.source_id == source_id
        )
    )
    if row is None:
        # Unactivated development requests remain unbilled, even if activation happened later.
        return None
    target = "released" if release else "consumed"
    if row.state == target:
        return row
    if row.state != "reserved":
        if release:
            return row  # Never undo consumed financial usage via privacy cleanup.
        fail("RESERVATION_RELEASED")
    row.state = target
    session.flush()
    return row


def reserve_response(session, workspace_id, source_id):
    return reserve(session, workspace_id, source_id, "response")


def consume_response(session, workspace_id, source_id):
    return finish(session, workspace_id, source_id, "response")


def release_response(session, workspace_id, source_id):
    return finish(session, workspace_id, source_id, "response", True)


def reserve_ai_addon(session, workspace_id, source_id):
    return reserve(session, workspace_id, source_id, "ai_addon")


def consume_ai_addon(session, workspace_id, source_id):
    return finish(session, workspace_id, source_id, "ai_addon")


def sell_ai_addon(session, workspace_id, source_id):
    return consume_ai_addon(session, workspace_id, source_id)


def release_ai_addon(session, workspace_id, source_id):
    return finish(session, workspace_id, source_id, "ai_addon", True)


def publication_charge(session, workspace_id, source_id):
    row = reserve(session, workspace_id, source_id, "publication")
    return finish(session, workspace_id, source_id, "publication") if row else None


def consume_specialist(session, workspace_id, source_id):
    row = reserve(session, workspace_id, source_id, "specialist")
    return finish(session, workspace_id, source_id, "specialist") if row else None


def postings(net, tax, sign=1):
    return [
        (code, amount * sign)
        for code, amount in [
            ("customer_receivable", net + tax),
            ("billing_revenue", -net),
            ("billing_tax", -tax),
        ]
        if amount
    ]


def issue_invoice(session, wid, actor, body):
    authorize(session, wid, actor)
    old = session.scalar(
        select(Invoice).where(Invoice.workspace_id == wid, Invoice.command_id == body.command_id)
    )
    if old:
        if old.subscription_id != body.subscription_id or old.credit_of:
            fail("IDEMPOTENCY_CONFLICT")
        return old
    sub = scoped(session, Subscription, wid, body.subscription_id)
    rows = session.scalars(
        select(Usage).where(
            Usage.subscription_id == sub.id,
            Usage.state == "consumed",
            ~Usage.id.in_(select(InvoiceLine.usage_id)),
        )
    ).all()
    net = sum(u.net for u in rows)
    tax = sum(u.tax for u in rows)
    if not 0 < net + tax <= 10**12:
        fail("INVALID_INVOICE_TOTAL")
    tx = post(session, wid, "invoice:" + str(body.command_id), postings(net, tax))
    invoice = Invoice(
        workspace_id=wid,
        subscription_id=sub.id,
        command_id=body.command_id,
        transaction_id=tx.id,
        snapshot=scoped(session, PlanVersion, wid, sub.plan_id).snapshot,
        net=net,
        tax=tax,
    )
    session.add(invoice)
    session.flush()
    session.add_all(
        [InvoiceLine(workspace_id=wid, invoice_id=invoice.id, usage_id=u.id) for u in rows]
    )
    session.flush()
    return invoice


def live_payment(session, invoice_id):
    return session.scalar(
        select(CustomerPayment).where(
            CustomerPayment.invoice_id == invoice_id,
            CustomerPayment.reversal_of.is_(None),
            ~CustomerPayment.id.in_(
                select(CustomerPayment.reversal_of).where(CustomerPayment.reversal_of.is_not(None))
            ),
        )
    )


def record_payment(session, wid, actor, invoice_id, body):
    authorize(session, wid, actor)
    inv = scoped(session, Invoice, wid, invoice_id)
    old = session.scalar(
        select(CustomerPayment).where(
            CustomerPayment.workspace_id == wid, CustomerPayment.command_id == body.command_id
        )
    )
    if old:
        if (
            old.invoice_id != invoice_id
            or old.reversal_of
            or any(
                getattr(old, k) != getattr(body, k)
                for k in ("amount", "reference", "evidence_digest")
            )
        ):
            fail("IDEMPOTENCY_CONFLICT")
        return old
    if (
        inv.credit_of
        or session.scalar(select(Invoice.id).where(Invoice.credit_of == inv.id))
        or live_payment(session, inv.id)
    ):
        fail("INVOICE_NOT_PAYABLE")
    if session.scalar(
        select(CustomerPayment.id).where(
            CustomerPayment.workspace_id == wid, CustomerPayment.reference == body.reference
        )
    ):
        fail("PAYMENT_REFERENCE_REUSED")
    if body.amount != inv.net + inv.tax:
        fail("FULL_SETTLEMENT_REQUIRED", 422)
    tx = post(
        session,
        wid,
        "customer-payment:" + str(body.command_id),
        [("manual_cash", body.amount), ("customer_receivable", -body.amount)],
    )
    row = CustomerPayment(
        workspace_id=wid,
        invoice_id=inv.id,
        transaction_id=tx.id,
        **body.model_dump(exclude={"currency", "exponent"}),
    )
    session.add(row)
    session.flush()
    return row


def reverse_payment(session, wid, actor, payment_id, command_id):
    authorize(session, wid, actor)
    old = scoped(session, CustomerPayment, wid, payment_id)
    existing = session.scalar(select(CustomerPayment).where(CustomerPayment.reversal_of == old.id))
    if existing:
        if existing.command_id != command_id:
            fail("IDEMPOTENCY_CONFLICT")
        return existing
    if old.reversal_of:
        fail("REVERSAL_OF_REVERSAL")
    tx = post(
        session,
        wid,
        "payment-reversal:" + str(command_id),
        [("manual_cash", -old.amount), ("customer_receivable", old.amount)],
        reversal_of=old.transaction_id,
    )
    row = CustomerPayment(
        workspace_id=wid,
        invoice_id=old.invoice_id,
        transaction_id=tx.id,
        command_id=command_id,
        reversal_of=old.id,
        reference="reversal_" + str(command_id),
        evidence_digest=old.evidence_digest,
        amount=old.amount,
    )
    session.add(row)
    session.flush()
    return row


def credit_invoice(session, wid, actor, invoice_id, command_id):
    authorize(session, wid, actor)
    inv = scoped(session, Invoice, wid, invoice_id)
    old = session.scalar(select(Invoice).where(Invoice.credit_of == inv.id))
    if old:
        if old.command_id != command_id:
            fail("IDEMPOTENCY_CONFLICT")
        return old
    if inv.credit_of or live_payment(session, inv.id):
        fail("REVERSE_PAYMENT_FIRST")
    tx = post(
        session,
        wid,
        "credit:" + str(command_id),
        postings(inv.net, inv.tax, -1),
        reversal_of=inv.transaction_id,
    )
    row = Invoice(
        workspace_id=wid,
        subscription_id=inv.subscription_id,
        command_id=command_id,
        credit_of=inv.id,
        transaction_id=tx.id,
        snapshot=inv.snapshot,
        net=inv.net,
        tax=inv.tax,
    )
    session.add(row)
    session.flush()
    return row


def meters(session, wid, actor):
    authorize(session, wid, actor)
    rows = session.execute(
        select(Usage.kind, Usage.state, func.count(), func.sum(Usage.net + Usage.tax))
        .where(Usage.workspace_id == wid)
        .group_by(Usage.kind, Usage.state)
    ).all()
    return [dict(kind=k, state=s, units=n, gross_millimes=v) for k, s, n, v in rows]


def sweep_reservations(session, wid, actor, limit=100):
    """Bounded operator reconciliation; only expired/terminal live sources release holds."""
    from app.ai.models import AIRun
    from app.collection.models import CollectionSession

    authorize(session, wid, actor)
    from sqlalchemy import and_, or_

    live_response = (
        select(CollectionSession.id)
        .where(
            CollectionSession.id == Usage.source_id,
            CollectionSession.workspace_id == wid,
            or_(
                CollectionSession.state == "submitted",
                and_(CollectionSession.state == "active", CollectionSession.expires_at > utcnow()),
            ),
        )
        .exists()
    )
    live_ai = (
        select(AIRun.id)
        .where(
            AIRun.id == Usage.source_id,
            AIRun.workspace_id == wid,
            AIRun.state.not_in(("failed", "uncertain", "invalidated")),
        )
        .exists()
    )
    rows = session.scalars(
        select(Usage)
        .where(
            Usage.workspace_id == wid,
            Usage.state == "reserved",
            or_(
                and_(Usage.kind == "response", ~live_response),
                and_(Usage.kind == "ai_addon", ~live_ai),
            ),
        )
        .order_by(Usage.created_at)
        .limit(min(max(limit, 1), 1000))
    ).all()
    released = 0
    for row in rows:
        if row.kind == "response":
            source = session.get(CollectionSession, row.source_id)
            terminal = (
                source is None
                or source.workspace_id != wid
                or source.state in ("withdrawn", "erased")
                or (source.state == "active" and source.expires_at <= utcnow())
            )
        elif row.kind == "ai_addon":
            source = session.get(AIRun, row.source_id)
            terminal = (
                source is None
                or source.workspace_id != wid
                or source.state in ("failed", "uncertain", "invalidated")
            )
        else:
            terminal = False
        if terminal:
            finish(session, wid, row.source_id, row.kind, True)
            released += 1
    return {"scanned": len(rows), "released": released}


def quota_snapshot(session, wid, actor):
    authorize(session, wid, actor)
    now = utcnow()
    sub = session.scalar(
        select(Subscription).where(
            Subscription.workspace_id == wid,
            Subscription.starts_at <= now,
            Subscription.ends_at > now,
            Subscription.cancelled_at.is_(None),
        )
    )
    if not sub:
        return {"active": False, "meters": meters(session, wid, actor)}
    rules = scoped(session, PlanVersion, wid, sub.plan_id).snapshot
    rows = session.scalars(
        select(Usage).where(Usage.subscription_id == sub.id, Usage.state != "released")
    ).all()
    products = {}
    for kind, rate in rules["rates"].items():
        extra = session.scalar(
            select(func.coalesce(func.sum(Grant.units), 0)).where(
                Grant.subscription_id == sub.id, Grant.kind == kind
            )
        )
        selected = [u for u in rows if u.kind == kind]
        quota = extra + (0 if kind == "specialist" else rate["quota"])
        products[kind] = dict(
            quota=quota,
            available=max(0, quota - len(selected)),
            reserved=sum(u.state == "reserved" for u in selected),
            consumed=sum(u.state == "consumed" for u in selected),
            included_units=rate["included_units"],
            price_millimes=rate["price"],
        )
    return dict(
        active=True,
        subscription_id=str(sub.id),
        products=products,
        budget_millimes=rules["budget"],
        committed_millimes=sum(u.net + u.tax for u in rows),
        operational_limit=rules["operational_limit"],
    )
