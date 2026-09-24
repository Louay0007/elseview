"""No administrator route can erase another user's global account."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import Field, SecretStr

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.common.privacy_schemas import StrictBody
from app.privacy_ops import account

router = APIRouter(prefix="/api/v1/account/erasure", tags=["privacy"])


class AccountErasureBody(StrictBody):
    request_key: UUID
    current_password: SecretStr = Field(min_length=1, max_length=1024)
    confirmation: Literal["ERASE MY ACCOUNT"]
    # Generate with crypto.getRandomValues(new Uint8Array(32)), encoded as hex.
    status_capability: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)


class StatusBody(StrictBody):
    request_key: UUID
    status_capability: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)


def view(row):
    return {
        "request_key": row.request_key,
        "state": row.state,
        "completed_at": row.completed_at,
        "retained": "Minimal identifier, consent and financial evidence is retained.",
    }


@router.post("", status_code=202)
def erase(body: AccountErasureBody, request: Request, user: Annotated[User, Depends(current_user)]):
    rate_limit(request, "account_erasure", str(user.id), 5)
    with request.app.state.database.sessions.begin() as session:
        return view(account.request_account_erasure(session, user.id, body))


@router.post("/status")
def status(body: StatusBody, request: Request):
    # Capability is in the body, never URLs, logs, audit details or restore manifests.
    rate_limit(request, "account_erasure_status", str(body.request_key), 30)
    with request.app.state.database.sessions.begin() as session:
        row = account.status_receipt(session, body.request_key, body.status_capability)
        return view(account.process_account(session, row.id))
