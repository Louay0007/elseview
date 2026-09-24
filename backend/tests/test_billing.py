from copy import deepcopy
from decimal import ROUND_HALF_UP, Decimal

import pytest
from pydantic import ValidationError

from app.billing.schemas import Rules
from app.billing.service import tax_amount
from app.common.errors import DomainError


def rules():
    return dict(
        currency="TND",
        exponent=3,
        tax_numerator=19,
        tax_denominator=100,
        rounding="half_up",
        reviewed_rules_reference="review-1",
        supplier_reference="supplier-1",
        customer_reference="customer-1",
        tax_reference="tax-review-1",
        retention_days=30,
        budget=100000,
        operational_limit=50,
        payment_policy="full_settlement_only",
        rates={
            k: dict(price=1001, quota=10, included_units=0)
            for k in ("publication", "response", "ai_addon", "specialist")
        },
    )


@pytest.mark.parametrize("net", [0, 1, 2, 3, 5, 999, 1001, 1234567, 99999999])
@pytest.mark.parametrize("num,den", [(0, 1), (1, 2), (19, 100), (7, 13)])
def test_tax_independent(net, num, den):
    assert tax_amount(net, num, den) == int(
        (Decimal(net) * Decimal(num) / Decimal(den)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"currency": "USD"},
        {"exponent": 2},
        {"exponent": 3.0},
        {"tax_numerator": True},
        {"tax_denominator": 0},
        {"tax_numerator": -1},
        {"budget": 10**12 + 1},
        {"operational_limit": 0},
        {"retention_days": None},
        {"reviewed_rules_reference": ""},
        {"supplier_reference": ""},
        {"rates": {}},
    ],
)
def test_rules_strict(patch):
    with pytest.raises(ValidationError):
        Rules(**(rules() | patch))


@pytest.mark.parametrize("value", [-1, True, "100", 1.2, 10**12 + 1])
def test_tax_money_bounds(value):
    with pytest.raises(DomainError):
        tax_amount(value, 19, 100)


def test_finite_allowance():
    r = deepcopy(rules())
    r["rates"]["response"]["included_units"] = 11
    with pytest.raises(ValidationError):
        Rules(**r)
