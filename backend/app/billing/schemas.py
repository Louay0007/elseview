from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

MAX = 1_000_000_000_000
KINDS = ("publication", "response", "ai_addon", "specialist")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rate(Strict):
    price: StrictInt = Field(ge=0, le=MAX)
    quota: StrictInt = Field(ge=0, le=1000000)
    included_units: StrictInt = Field(default=0, ge=0, le=1000000)


class Rules(Strict):
    currency: Literal["TND"]
    exponent: StrictInt = Field(ge=3, le=3)
    tax_numerator: StrictInt = Field(ge=0, le=1000000)
    tax_denominator: StrictInt = Field(gt=0, le=1000000)
    rounding: Literal["half_up"]
    reviewed_rules_reference: str = Field(min_length=1, max_length=120, pattern=r"^\S+$")
    supplier_reference: str = Field(min_length=1, max_length=120, pattern=r"^\S+$")
    customer_reference: str = Field(min_length=1, max_length=120, pattern=r"^\S+$")
    tax_reference: str = Field(min_length=1, max_length=120, pattern=r"^\S+$")
    retention_days: StrictInt = Field(ge=0, le=36500)
    budget: StrictInt = Field(ge=0, le=MAX)
    operational_limit: StrictInt = Field(gt=0, le=1000000)
    rates: dict[str, Rate]
    payment_policy: Literal["full_settlement_only"]

    @model_validator(mode="after")
    def valid(self):
        if set(self.rates) != set(KINDS):
            raise ValueError("Explicit finite rate/quota required for each product")
        for r in self.rates.values():
            if r.included_units > r.quota:
                raise ValueError("Allowance exceeds finite quota")
            if (
                r.price
                + (2 * r.price * self.tax_numerator + self.tax_denominator)
                // (2 * self.tax_denominator)
                > MAX
            ):
                raise ValueError("Gross amount exceeds bound")
        return self


class PlanBody(Strict):
    key: str = Field(pattern=r"^[a-z0-9_-]{1,80}$")
    version: StrictInt = Field(gt=0)
    rules: Rules
    reviewed: Literal[True]


class ActivateBody(Strict):
    plan_id: UUID
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def valid(self):
        if not self.starts_at.tzinfo or not self.ends_at.tzinfo or self.ends_at <= self.starts_at:
            raise ValueError("Explicit timezone and positive period required")
        return self


class GrantBody(Strict):
    subscription_id: UUID
    source_id: UUID
    kind: Literal["publication", "response", "ai_addon", "specialist"]
    units: StrictInt = Field(gt=0, le=1000000)


class InvoiceBody(Strict):
    subscription_id: UUID
    command_id: UUID


class PaymentBody(Strict):
    command_id: UUID
    reference: str = Field(pattern=r"^[A-Za-z0-9_-]{1,120}$")
    evidence_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    amount: StrictInt = Field(gt=0, le=MAX)
    currency: Literal["TND"]
    exponent: StrictInt = Field(ge=3, le=3)


class CommandBody(Strict):
    command_id: UUID
