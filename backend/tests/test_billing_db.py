"""Real HTTP commercial opt-in and PostgreSQL race/immutability contracts."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_billing import rules

from app.auth.security import utcnow
from app.billing import service
from app.billing.models import Usage
from app.billing.schemas import GrantBody
from app.common.errors import DomainError
from app.reviews.models import LedgerEntry

pytestmark = pytest.mark.db


@pytest.fixture
def commercial(research_app, db_engine):
    client, app, actor = research_app
    headers, actor_id, wid = actor()
    base = f"/api/v1/workspaces/{wid}/billing"
    body = dict(key="team", version=1, reviewed=True, rules=rules())
    response = client.post(base + "/plans", headers=headers, json=body)
    assert response.status_code == 201, response.text
    pid = response.json()["id"]
    response = client.post(
        base + "/subscriptions",
        headers=headers,
        json=dict(
            plan_id=pid,
            starts_at=(utcnow() - timedelta(seconds=1)).isoformat(),
            ends_at=(utcnow() + timedelta(days=30)).isoformat(),
        ),
    )
    assert response.status_code == 201, response.text
    return client, headers, UUID(str(wid)), base, UUID(response.json()["id"]), UUID(str(actor_id))


def test_http_invoice_payment_credit(commercial, db_engine):
    client, h, wid, base, sub, actor = commercial
    source = uuid4()
    with Session(db_engine) as s, s.begin():
        service.reserve_response(s, wid, source)
        service.consume_response(s, wid, source)
        service.consume_response(s, wid, source)
    command = str(uuid4())
    body = dict(subscription_id=str(sub), command_id=command)
    response = client.post(base + "/invoices", headers=h, json=body)
    assert response.status_code == 201, response.text
    inv = response.json()
    assert (inv["net"], inv["tax"]) == (1001, 190)
    assert client.post(base + "/invoices", headers=h, json=body).json()["id"] == inv["id"]
    p = dict(
        command_id=str(uuid4()),
        reference="receipt-" + uuid4().hex,
        evidence_digest="a" * 64,
        amount=1190,
        currency="TND",
        exponent=3,
    )
    assert (
        client.post(base + f"/invoices/{inv['id']}/payments", headers=h, json=p).status_code == 422
    )
    p["amount"] = 1191
    response = client.post(base + f"/invoices/{inv['id']}/payments", headers=h, json=p)
    assert response.status_code == 201, response.text
    pay = response.json()
    assert (
        client.post(base + f"/invoices/{inv['id']}/payments", headers=h, json=p).json()["id"]
        == pay["id"]
    )
    assert (
        client.post(
            base + f"/invoices/{inv['id']}/credit", headers=h, json=dict(command_id=str(uuid4()))
        ).status_code
        == 409
    )
    response = client.post(
        base + f"/payments/{pay['id']}/reverse", headers=h, json=dict(command_id=str(uuid4()))
    )
    assert response.status_code == 201, response.text
    response = client.post(
        base + f"/invoices/{inv['id']}/credit", headers=h, json=dict(command_id=str(uuid4()))
    )
    assert response.status_code == 201, response.text
    with Session(db_engine) as s:
        assert (
            s.scalar(select(func.count()).select_from(Usage).where(Usage.workspace_id == wid)) == 1
        )
        assert (
            s.scalar(
                select(func.sum(LedgerEntry.amount_millimes)).where(LedgerEntry.workspace_id == wid)
            )
            == 0
        )
    for table in (
        "billing_usage",
        "billing_invoices",
        "billing_customer_payments",
        "billing_plan_versions",
    ):
        with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
            s.execute(text(f"DELETE FROM {table} WHERE workspace_id=:w"), dict(w=wid))


def test_race_exactly_once_and_quota(commercial, db_engine):
    _, _, wid, _, _, _ = commercial
    source = uuid4()

    def reserve(source):
        try:
            with Session(db_engine) as s, s.begin():
                return str(service.reserve_response(s, wid, source).id)
        except DomainError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(reserve, [source] * 4))
    assert len(set(ids)) == 1
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(reserve, [uuid4() for _ in range(15)]))
    assert ids.count("BILLING_QUOTA_EXCEEDED") == 6
    with Session(db_engine) as s:
        assert (
            s.scalar(select(func.count()).select_from(Usage).where(Usage.workspace_id == wid)) == 10
        )


def test_cancellation_hold_release_specialist(commercial, db_engine):
    client, h, wid, base, sub, actor = commercial
    source = uuid4()
    with Session(db_engine) as s, s.begin():
        service.reserve_response(s, wid, source)
        with pytest.raises(DomainError):
            service.consume_specialist(s, wid, uuid4())
        service.grant(
            s,
            wid,
            actor,
            GrantBody(subscription_id=sub, source_id=uuid4(), kind="specialist", units=1),
        )
        assert service.consume_specialist(s, wid, uuid4()).state == "consumed"
    assert client.post(base + f"/subscriptions/{sub}/cancel", headers=h).status_code == 200
    with Session(db_engine) as s, s.begin():
        assert service.consume_response(s, wid, source).state == "consumed"
        with pytest.raises(DomainError):
            service.reserve_response(s, wid, uuid4())
    with Session(db_engine) as s, s.begin():
        assert service.release_response(s, wid, source).state == "consumed"


def test_unactivated_and_http_permission(research_app, db_engine):
    client, app, actor = research_app
    h, uid, wid = actor()
    with Session(db_engine) as s, s.begin():
        assert service.publication_charge(s, UUID(str(wid)), uuid4()) is None
        assert service.reserve_ai_addon(s, UUID(str(wid)), uuid4()) is None
    h2, _, _ = actor()
    base = f"/api/v1/workspaces/{wid}/billing"
    assert client.get(base + "/usage", headers=h2).status_code == 404
    assert client.get(base + "/usage").status_code == 401


def test_sql_rate_and_journal_guards(commercial, db_engine):
    _, _, wid, _, sub, _ = commercial
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        s.execute(
            text(
                "INSERT INTO billing_usage(id,workspace_id,subscription_id,source_id,kind,state,net,tax) VALUES(:i,:w,:sub,:source,'response','reserved',1,0)"
            ),
            dict(i=uuid4(), w=wid, sub=sub, source=uuid4()),
        )
    with Session(db_engine) as s, s.begin():
        source = uuid4()
        service.reserve_response(s, wid, source)
        service.release_response(s, wid, source)
        with pytest.raises(DomainError):
            service.reserve_response(s, wid, source)


def test_frozen_allowance_and_new_plan_future_only(commercial, db_engine):
    client, h, wid, base, sub, actor = commercial
    changed = rules()
    changed["rates"]["response"]["price"] = 9000
    r = client.post(
        base + "/plans", headers=h, json=dict(key="team", version=2, reviewed=True, rules=changed)
    )
    assert r.status_code == 201, r.text
    r = client.post(
        base + "/subscriptions",
        headers=h,
        json=dict(
            plan_id=r.json()["id"],
            starts_at=(utcnow() - timedelta(seconds=1)).isoformat(),
            ends_at=(utcnow() + timedelta(days=60)).isoformat(),
        ),
    )
    assert r.status_code == 409
    with Session(db_engine) as s, s.begin():
        assert service.reserve_response(s, wid, uuid4()).net == 1001
    changed["rates"]["response"]["price"] = 8000
    assert (
        client.post(
            base + "/plans",
            headers=h,
            json=dict(key="team", version=2, reviewed=True, rules=changed),
        ).status_code
        == 409
    )
    q = client.get(base + "/quotas", headers=h)
    assert q.status_code == 200 and q.json()["products"]["response"]["reserved"] == 1


def test_sql_unbalanced_and_reversal_without_credit(commercial, db_engine):
    from app.billing.schemas import InvoiceBody
    from app.reviews import service as ledger

    _, _, wid, _, sub, actor = commercial
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        from app.reviews.models import LedgerTransaction

        s.add(LedgerTransaction(workspace_id=wid, command_key="empty:" + uuid4().hex))
    with Session(db_engine) as s, s.begin():
        source = uuid4()
        service.reserve_response(s, wid, source)
        service.consume_response(s, wid, source)
        inv = service.issue_invoice(
            s, wid, actor, InvoiceBody(subscription_id=sub, command_id=uuid4())
        )
        tid = inv.transaction_id
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        ledger.post(
            s, wid, "bad-reverse:" + uuid4().hex, service.postings(1001, 190, -1), reversal_of=tid
        )


def test_allowance_budget_release_and_tax_snapshot(research_app, db_engine):
    from app.billing.schemas import ActivateBody, PlanBody

    client, _, actor = research_app
    _, uid, wid = actor()
    wid = UUID(str(wid))
    spec = rules()
    spec["rates"]["response"].update(included_units=1, quota=3)
    spec["budget"] = 1191
    with Session(db_engine) as s, s.begin():
        plan = service.create_plan(
            s, wid, uid, PlanBody(key="allowance", version=1, reviewed=True, rules=spec)
        )
        service.activate(
            s,
            wid,
            uid,
            ActivateBody(
                plan_id=plan.id,
                starts_at=utcnow() - timedelta(seconds=1),
                ends_at=utcnow() + timedelta(days=1),
            ),
        )
        free = service.reserve_response(s, wid, uuid4())
        assert free.net == free.tax == 0
        paid = service.reserve_response(s, wid, uuid4())
        assert (paid.net, paid.tax) == (1001, 190)
        with pytest.raises(DomainError) as e:
            service.reserve_response(s, wid, uuid4())
        assert e.value.code == "BILLING_BUDGET_EXCEEDED"
        service.release_response(s, wid, paid.source_id)
        assert service.reserve_response(s, wid, uuid4()).net == 1001


def test_http_payment_race_and_duplicate_reference(commercial, db_engine):
    from app.billing.schemas import InvoiceBody, PaymentBody

    _, _, wid, _, sub, actor = commercial
    with Session(db_engine) as s, s.begin():
        source = uuid4()
        service.reserve_response(s, wid, source)
        service.consume_response(s, wid, source)
        invoice = service.issue_invoice(
            s, wid, actor, InvoiceBody(subscription_id=sub, command_id=uuid4())
        ).id

    def pay(_):
        try:
            with Session(db_engine) as s, s.begin():
                body = PaymentBody(
                    command_id=uuid4(),
                    reference=uuid4().hex,
                    evidence_digest="b" * 64,
                    amount=1191,
                    currency="TND",
                    exponent=3,
                )
                service.record_payment(s, wid, actor, invoice, body)
                return "paid"
        except DomainError as e:
            return e.code

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(pay, range(3)))
    assert results.count("paid") == 1
    assert results.count("INVOICE_NOT_PAYABLE") == 2


def test_real_publication_hook_charges_once(commercial, db_engine):
    from study_fixtures import ready_study

    client, h, wid, base, sub, actor = commercial
    fixture = ready_study(client, f"/api/v1/workspaces/{wid}", h)
    r = client.post(fixture["endpoint"] + "/publish", headers=h, json={"expected_revision": 2})
    assert r.status_code == 200, r.text
    with Session(db_engine) as s:
        usage = s.scalar(
            select(Usage).where(Usage.workspace_id == wid, Usage.kind == "publication")
        )
        assert usage.source_id == UUID(fixture["version_id"])
        assert usage.state == "consumed"
        assert usage.net == 1001
    # A replay cannot publish another billable event.
    client.post(fixture["endpoint"] + "/publish", headers=h, json={"expected_revision": 2})
    with Session(db_engine) as s:
        assert (
            s.scalar(
                select(func.count())
                .select_from(Usage)
                .where(Usage.workspace_id == wid, Usage.kind == "publication")
            )
            == 1
        )


def test_response_start_submit_uses_reserved_snapshot(research_app, db_engine, monkeypatch):
    """Activate on workspace creation before reusable real participant collection fixture."""
    from test_collection_db import put
    from test_reviews_db import collected as collection_fixture

    from app.billing.schemas import ActivateBody, PlanBody

    client, app, actor = research_app

    def commercial_actor(*args, **kwargs):
        h, uid, wid = actor(*args, **kwargs)
        with Session(db_engine) as s, s.begin():
            p = service.create_plan(
                s, wid, uid, PlanBody(key="responses", version=1, reviewed=True, rules=rules())
            )
            service.activate(
                s,
                wid,
                uid,
                ActivateBody(
                    plan_id=p.id,
                    starts_at=utcnow() - timedelta(seconds=1),
                    ends_at=utcnow() + timedelta(days=1),
                ),
            )
        return h, uid, wid

    from types import SimpleNamespace

    collected = collection_fixture.__wrapped__(
        (client, app, commercial_actor), db_engine, SimpleNamespace()
    )
    client, url, headers, result, _, _ = collected
    sid = UUID(result["session_id"])
    with Session(db_engine) as s:
        usage = s.scalar(select(Usage).where(Usage.source_id == sid, Usage.kind == "response"))
        assert usage.state == "reserved"
        wid = usage.workspace_id
    assert put(client, url, headers, "no")[0].status_code == 200
    r = client.post(
        url + "/submit",
        headers=headers,
        json={"version_id": result["version_id"], "expected_revision": 1},
    )
    assert r.status_code == 200, r.text
    with Session(db_engine) as s:
        rows = s.scalars(
            select(Usage).where(Usage.workspace_id == wid, Usage.kind == "response")
        ).all()
        assert len(rows) == 1 and rows[0].state == "consumed"


def test_actual_ai_sale_distinct_from_provider_cost(commercial, db_engine, settings, monkeypatch):
    import asyncio
    from decimal import Decimal

    from study_fixtures import ready_study
    from test_ai_db import claim_run

    from app.ai import service as ai
    from app.ai.models import AIAttempt
    from app.ai.schemas import RunBody
    from app.jobs import service as jobs
    from app.jobs.models import Job

    client, h, wid, _, _, actor = commercial
    original = client.post

    def assisted(url, **kwargs):
        if url.endswith("/studies"):
            kwargs["json"] = kwargs["json"] | {"ai_policy": "assisted"}
        return original(url, **kwargs)

    monkeypatch.setattr(client, "post", assisted)
    fixture = ready_study(client, f"/api/v1/workspaces/{wid}", h)
    from app.studies.models import StudyVersion

    with Session(db_engine) as s:
        sid = s.get(StudyVersion, UUID(fixture["version_id"])).study_id
    settings.llm_input_price_per_million = Decimal("1")
    settings.llm_output_price_per_million = Decimal("1")
    for invalid in (False, True):
        with Session(db_engine) as s, s.begin():
            result = ai.create(
                s,
                settings,
                wid,
                actor,
                RunBody(
                    study_id=sid,
                    operation="study_helper",
                    command_key=uuid4().hex,
                    instruction="Synthetic draft " + uuid4().hex,
                    researcher_text_approved=True,
                ),
            )
            rid = UUID(result["id"])
            assert s.scalar(select(Usage).where(Usage.source_id == rid)).state == "reserved"
        with Session(db_engine) as s, s.begin():
            job = claim_run(s, rid)
            prompt, sources, coverage = ai.prepare(s, settings, job)
            jid = job.id
        content, usage, request_id = asyncio.run(ai.adapter.generate(settings, prompt))
        with Session(db_engine) as s, s.begin():
            job = s.get(Job, jid)
            ai.finish(
                s,
                settings,
                job,
                "not-json" if invalid else content,
                usage,
                request_id,
                sources,
                coverage,
            )
            jobs.complete(s, jid, job.lease_token, {"status": "ok"})
            sale = s.scalar(select(Usage).where(Usage.source_id == rid))
            assert sale.state == ("released" if invalid else "consumed")
            cost = s.scalar(select(AIAttempt).where(AIAttempt.run_id == rid))
            assert cost.actual_cost is not None
            assert sale.net == 1001 and Decimal(sale.net) != cost.actual_cost


@pytest.mark.parametrize("action", ["withdraw", "expire"])
def test_actual_response_hold_release(research_app, db_engine, action):
    from types import SimpleNamespace

    from test_reviews_db import collected as collection_fixture

    from app.billing.schemas import ActivateBody, PlanBody
    from app.collection.models import CollectionSession

    client, app, actor = research_app
    owner = {}

    def activate_actor(*args, **kwargs):
        h, uid, wid = actor(*args, **kwargs)
        owner.update(uid=uid, wid=wid)
        with Session(db_engine) as s, s.begin():
            p = service.create_plan(
                s, wid, uid, PlanBody(key="release", version=1, reviewed=True, rules=rules())
            )
            service.activate(
                s,
                wid,
                uid,
                ActivateBody(
                    plan_id=p.id,
                    starts_at=utcnow() - timedelta(seconds=1),
                    ends_at=utcnow() + timedelta(days=1),
                ),
            )
        return h, uid, wid

    client, url, headers, result, _, _ = collection_fixture.__wrapped__(
        (client, app, activate_actor), db_engine, SimpleNamespace()
    )
    sid = UUID(result["session_id"])
    if action == "withdraw":
        r = client.post(url + "/withdraw", headers=headers)
        assert r.status_code == 200, r.text
    else:
        with Session(db_engine) as s, s.begin():
            s.get(CollectionSession, sid).expires_at = utcnow() - timedelta(seconds=1)
        with Session(db_engine) as s, s.begin():
            assert service.sweep_reservations(s, owner["wid"], owner["uid"])["released"] == 1
    with Session(db_engine) as s:
        assert (
            s.scalar(select(Usage).where(Usage.source_id == sid, Usage.kind == "response")).state
            == "released"
        )
