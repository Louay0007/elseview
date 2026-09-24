from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.billing import service
from app.billing.schemas import (
    ActivateBody,
    CommandBody,
    GrantBody,
    InvoiceBody,
    PaymentBody,
    PlanBody,
)


def guard(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    rate_limit(request, "billing", request.client.host if request.client else "unknown", 120)


router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/billing",
    tags=["billing"],
    dependencies=[Depends(guard)],
)
Actor = Annotated[User, Depends(current_user)]


def view(row):
    result = {"id": str(row.id)}
    for k in (
        "key",
        "version",
        "plan_id",
        "subscription_id",
        "invoice_id",
        "reference",
        "state",
        "net",
        "tax",
        "amount",
        "starts_at",
        "ends_at",
        "cancelled_at",
        "snapshot",
        "credit_of",
        "reversal_of",
        "transaction_id",
    ):
        if hasattr(row, k):
            result[k] = getattr(row, k)
    return result


@router.post("/plans", status_code=201)
def plan(workspace_id: UUID, body: PlanBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.create_plan(s, workspace_id, user.id, body))


@router.post("/subscriptions", status_code=201)
def subscribe(workspace_id: UUID, body: ActivateBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.activate(s, workspace_id, user.id, body))


@router.post("/subscriptions/{id}/cancel")
def cancel(workspace_id: UUID, id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.cancel(s, workspace_id, user.id, id))


@router.post("/grants", status_code=201)
def grant(workspace_id: UUID, body: GrantBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.grant(s, workspace_id, user.id, body))


@router.post("/invoices", status_code=201)
def invoice(workspace_id: UUID, body: InvoiceBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.issue_invoice(s, workspace_id, user.id, body))


@router.post("/invoices/{id}/payments", status_code=201)
def payment(workspace_id: UUID, id: UUID, body: PaymentBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.record_payment(s, workspace_id, user.id, id, body))


@router.post("/invoices/{id}/credit", status_code=201)
def credit(workspace_id: UUID, id: UUID, body: CommandBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.credit_invoice(s, workspace_id, user.id, id, body.command_id))


@router.post("/payments/{id}/reverse", status_code=201)
def reverse(workspace_id: UUID, id: UUID, body: CommandBody, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return view(service.reverse_payment(s, workspace_id, user.id, id, body.command_id))


@router.get("/usage")
def usage(workspace_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return service.meters(s, workspace_id, user.id)


@router.get("/plans")
def plans(workspace_id: UUID, request: Request, user: Actor):
    return listing(request, workspace_id, user, service.PlanVersion)


@router.get("/subscriptions")
def subscriptions(workspace_id: UUID, request: Request, user: Actor):
    return listing(request, workspace_id, user, service.Subscription)


@router.get("/invoices")
def invoices(workspace_id: UUID, request: Request, user: Actor):
    return listing(request, workspace_id, user, service.Invoice)


@router.get("/payments")
def payments(workspace_id: UUID, request: Request, user: Actor):
    return listing(request, workspace_id, user, service.CustomerPayment)


def listing(request, workspace_id, user, model):
    from sqlalchemy import select

    with request.app.state.database.sessions.begin() as s:
        service.authorize(s, workspace_id, user.id)
        return [
            view(row)
            for row in s.scalars(
                select(model)
                .where(model.workspace_id == workspace_id)
                .order_by(model.created_at.desc())
                .limit(100)
            )
        ]


@router.get("/invoices/{id}")
def invoice_detail(workspace_id: UUID, id: UUID, request: Request, user: Actor):
    from sqlalchemy import select

    with request.app.state.database.sessions.begin() as s:
        service.authorize(s, workspace_id, user.id)
        inv = service.scoped(s, service.Invoice, workspace_id, id)
        result = view(inv)
        result["lines"] = [
            dict(kind=u.kind, net=u.net, tax=u.tax)
            for u in s.scalars(
                select(service.Usage)
                .join(service.InvoiceLine, service.InvoiceLine.usage_id == service.Usage.id)
                .where(service.InvoiceLine.invoice_id == id)
            )
        ]
        result["settled"] = service.live_payment(s, id) is not None
        return result


@router.post("/reconcile-reservations")
def reconcile(workspace_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return service.sweep_reservations(s, workspace_id, user.id)


@router.get("/quotas")
def quotas(workspace_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        return service.quota_snapshot(s, workspace_id, user.id)


@router.post("/specialist/{source_id}", status_code=201)
def specialist(workspace_id: UUID, source_id: UUID, request: Request, user: Actor):
    with request.app.state.database.sessions.begin() as s:
        service.authorize(s, workspace_id, user.id)
        row = service.consume_specialist(s, workspace_id, source_id)
        return view(row) if row else {"billed": False}
