"""Allowance recycling through real service writes and PostgreSQL guards."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_billing import rules

from app.auth.security import utcnow
from app.billing import service
from app.billing.schemas import ActivateBody, PlanBody
from app.common.errors import DomainError

pytestmark = pytest.mark.db


@pytest.fixture
def allowance(research_app, db_engine):
    def create(price=1001, budget=100000):
        _, _, actor = research_app
        _, uid, wid = actor()
        snapshot = rules()
        snapshot["rates"]["response"].update(included_units=1, price=price)
        snapshot["budget"] = budget
        with Session(db_engine) as s, s.begin():
            plan = service.create_plan(
                s, wid, uid, PlanBody(key="allowance", version=1, reviewed=True, rules=snapshot)
            )
            sub = service.activate(
                s,
                wid,
                uid,
                ActivateBody(
                    plan_id=plan.id,
                    starts_at=utcnow() - timedelta(seconds=1),
                    ends_at=utcnow() + timedelta(days=1),
                ),
            )
            return wid, sub.id

    return create


@pytest.mark.parametrize("price,budget", [(1001, 100000), (1001, 1191), (0, 1)])
def test_released_included_recycles_without_repricing_paid(allowance, db_engine, price, budget):
    wid, _ = allowance(price, budget)
    a, b, c = uuid4(), uuid4(), uuid4()
    with Session(db_engine) as s, s.begin():
        first = service.reserve_response(s, wid, a)
        paid = service.reserve_response(s, wid, b)
        assert (first.included_allocation, paid.included_allocation) == (True, False)
        assert paid.net == price
        service.release_response(s, wid, a)
        replacement = service.reserve_response(s, wid, c)
        assert replacement.included_allocation and replacement.net == 0
        assert paid.net == price and not paid.included_allocation
        assert service.reserve_response(s, wid, c).id == replacement.id
        service.consume_response(s, wid, c)
        if price and budget == 1191:
            with pytest.raises(DomainError):
                service.reserve_response(s, wid, uuid4())
        else:
            next_row = service.reserve_response(s, wid, uuid4())
            assert next_row.net == price and not next_row.included_allocation


def test_concurrent_recycling_only_one_included(allowance, db_engine):
    wid, _ = allowance()
    a = uuid4()
    with Session(db_engine) as s, s.begin():
        service.reserve_response(s, wid, a)
        service.reserve_response(s, wid, uuid4())
        service.release_response(s, wid, a)

    def reserve(_):
        with Session(db_engine) as s, s.begin():
            row = service.reserve_response(s, wid, uuid4())
            return row.included_allocation, row.net

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(reserve, range(2))) == [(False, 1001), (True, 0)]


@pytest.mark.parametrize("price", [0, 1001])
def test_sql_allocation_and_price_forgery(allowance, db_engine, price):
    wid, sub = allowance(price)

    def insert(included, net):
        with Session(db_engine) as s, s.begin():
            s.execute(
                text("""INSERT INTO billing_usage
                (id,workspace_id,subscription_id,source_id,kind,state,net,tax,included_allocation)
                VALUES (:id,:wid,:sub,:source,'response','reserved',:net,0,:included)"""),
                dict(id=uuid4(), wid=wid, sub=sub, source=uuid4(), net=net, included=included),
            )

    # Even a zero-price rate must not let callers choose allocation provenance.
    with pytest.raises(DBAPIError):
        insert(False, 0)
    insert(True, 0)
    with pytest.raises(DBAPIError):
        insert(True, 0)
    with pytest.raises(DBAPIError):
        insert(False, price + 1)
    with pytest.raises(DBAPIError), Session(db_engine) as s, s.begin():
        s.execute(
            text("UPDATE billing_usage SET included_allocation=false WHERE workspace_id=:w"),
            {"w": wid},
        )
