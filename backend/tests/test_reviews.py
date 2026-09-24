from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.common.errors import DomainError
from app.reviews.schemas import DecisionBody, PayoutBody, RetentionBody
from app.reviews.service import money


@pytest.mark.parametrize("amount", [-1, 0, True, 1.5, "100", 10**12 + 1])
def test_money_invalid(amount):
    with pytest.raises(DomainError):
        money(amount)


@pytest.mark.parametrize("amount", [1, 1000, 10**12])
def test_money_boundaries(amount):
    money(amount)


@pytest.mark.parametrize("currency", ["USD", "tnd", "credits", ""])
def test_money_currency(currency):
    with pytest.raises(DomainError):
        money(1000, currency)


@pytest.mark.parametrize(
    "patch",
    [
        {"rationale": ""},
        {"rationale": "   "},
        {"verdict": "rejected"},
        {"evidence": [""]},
        {"evidence": ["x" * 501]},
        {"evidence": ["x"] * 21},
        {"verdict": "flagged"},
        {"automatic": True},
    ],
)
def test_decision_bounds(patch):
    with pytest.raises(ValidationError):
        DecisionBody(
            **(
                {"command_key": uuid4(), "verdict": "accepted", "rationale": "Reviewed evidence"}
                | patch
            )
        )


def test_rejection_evidence_is_human_rationale():
    assert (
        DecisionBody(
            command_key=uuid4(),
            verdict="rejected",
            rationale="Inconsistent task",
            evidence=["block:single final answer"],
        ).verdict
        == "rejected"
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"amount_millimes": True},
        {"amount_millimes": 0},
        {"amount_millimes": 10**12 + 1},
        {"currency": "USD"},
        {"external_reference": "bank account 123"},
        {"evidence": " "},
    ],
)
def test_payment_bounds(patch):
    with pytest.raises(ValidationError):
        PayoutBody(
            **(
                {
                    "command_key": uuid4(),
                    "amount_millimes": 100,
                    "external_reference": "receipt-1",
                    "evidence": "Manual reconciliation record",
                }
                | patch
            )
        )


def test_retention_requires_reviewed_explicit_interval():
    with pytest.raises(ValidationError):
        RetentionBody(rationale="reviewed")
    with pytest.raises(ValidationError):
        RetentionBody(settled_days=30, rationale=" ")
    assert (
        RetentionBody(settled_days=0, rationale="Reviewed immediate minimization").settled_days == 0
    )
