from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.auth.dependencies import current_user, rate_limit
from app.auth.models import User
from app.collection.models import CollectionSession
from app.longitudinal import service
from app.longitudinal.models import Booking, DiaryOccurrence, Notification
from app.longitudinal.schemas import (
    AttendanceBody,
    BookingBody,
    DiaryBody,
    DiaryStartBody,
    RecordingBody,
    RescheduleBody,
    RevisionBody,
    SlotBody,
    TranscriptBody,
)

router = APIRouter(prefix="/api/v1", tags=["longitudinal"])
Actor = Annotated[User, Depends(current_user)]
S = "/workspaces/{workspace_id}/longitudinal"
P = "/participant/longitudinal"


def guard(request, response):
    rate_limit(
        request,
        "longitudinal",
        service.digest(request.headers.get("Authorization", "anonymous")),
        120,
    )
    response.headers["Cache-Control"] = "no-store"


@router.post(S + "/slots")
def create_slot(
    workspace_id: UUID, body: SlotBody, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.create_slot(session, workspace_id, user.id, body)


@router.get(S + "/slots")
def staff_slots(
    workspace_id: UUID, version_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.list_slots(session, workspace_id, user.id, version_id, True)


@router.get(P + "/slots")
def slots(workspace_id: UUID, version_id: UUID, request: Request, response: Response, user: Actor):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.list_slots(session, workspace_id, user.id, version_id)


@router.post(P + "/bookings")
def book(body: BookingBody, request: Request, response: Response, user: Actor):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.book(session, user.id, body)


@router.get(P + "/notifications")
def notifications(workspace_id: UUID, request: Request, response: Response, user: Actor):
    """Durable in-app reminders, not a claim of email/SMS delivery."""
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        service.require_unrestricted(session, workspace_id, user.id)
        rows = session.scalars(
            select(Notification)
            .join(Booking, Booking.id == Notification.booking_id)
            .where(
                Notification.workspace_id == workspace_id,
                Booking.subject_id == user.id,
                Booking.state == "booked",
                Booking.revision == Notification.booking_revision,
                Notification.delivered_at.is_not(None),
            )
            .order_by(Notification.delivered_at.desc(), Notification.id)
            .limit(100)
        )
        return [
            {
                "id": row.id,
                "kind": "interview_reminder",
                "available_at": row.delivered_at,
                "booking": service.booking_json(session, session.get(Booking, row.booking_id)),
            }
            for row in rows
        ]


@router.get(P + "/bookings")
def bookings(workspace_id: UUID, request: Request, response: Response, user: Actor):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        service.require_unrestricted(session, workspace_id, user.id)
        rows = session.scalars(
            select(Booking)
            .where(Booking.workspace_id == workspace_id, Booking.subject_id == user.id)
            .order_by(Booking.created_at.desc(), Booking.id)
            .limit(200)
        )
        return [service.booking_json(session, row) for row in rows]


@router.post(P + "/bookings/{booking_id}/cancel")
def cancel(booking_id: UUID, body: RevisionBody, request: Request, response: Response, user: Actor):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.change_booking(session, user.id, booking_id, body, True)


@router.post(P + "/bookings/{booking_id}/reschedule")
def reschedule(
    booking_id: UUID, body: RescheduleBody, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.change_booking(session, user.id, booking_id, body)


@router.post(S + "/bookings/{booking_id}/attendance")
def attendance(
    workspace_id: UUID,
    booking_id: UUID,
    body: AttendanceBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.attendance(session, workspace_id, user.id, booking_id, body)


@router.post(S + "/diary-schedules")
def diary(workspace_id: UUID, body: DiaryBody, request: Request, response: Response, user: Actor):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.create_diary(session, workspace_id, user.id, body)


@router.get(P + "/diary-occurrences")
def occurrences(workspace_id: UUID, request: Request, response: Response, user: Actor):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        service.require_unrestricted(session, workspace_id, user.id)
        rows = session.scalars(
            select(DiaryOccurrence)
            .join(CollectionSession, CollectionSession.id == DiaryOccurrence.base_session_id)
            .where(
                DiaryOccurrence.workspace_id == workspace_id,
                CollectionSession.subject_id == user.id,
                CollectionSession.state.notin_(["withdrawn", "erased"]),
            )
            .order_by(DiaryOccurrence.opens_at, DiaryOccurrence.id)
            .limit(200)
        )
        return [service.occurrence_json(session, row) for row in rows]


@router.post(P + "/diary-occurrences/{occurrence_id}/start")
def start_diary(
    occurrence_id: UUID, body: DiaryStartBody, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.start_diary(session, user.id, occurrence_id, body)


@router.post(S + "/recordings")
def recording(
    workspace_id: UUID, body: RecordingBody, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.create_recording(session, workspace_id, user.id, body)


@router.get(S + "/recordings/{recording_id}")
def get_recording(
    workspace_id: UUID, recording_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.get_recording(session, workspace_id, user.id, recording_id)


@router.post(S + "/recordings/{recording_id}/transcript")
def transcript(
    workspace_id: UUID,
    recording_id: UUID,
    body: TranscriptBody,
    request: Request,
    response: Response,
    user: Actor,
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.import_transcript(session, workspace_id, user.id, recording_id, body)


@router.get(S + "/metrics")
def metrics(
    workspace_id: UUID, version_id: UUID, request: Request, response: Response, user: Actor
):
    guard(request, response)
    with request.app.state.database.sessions.begin() as session:
        return service.metrics(session, workspace_id, user.id, version_id)
