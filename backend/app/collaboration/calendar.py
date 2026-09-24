from datetime import UTC

from app.common.errors import DomainError
from app.longitudinal.models import ScheduleSlot
from app.longitudinal.service import owned_booking


def escape(value):
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold(line):
    parts = []
    part = ""
    for char in line:
        if len((part + char).encode("utf-8")) > 75:
            parts.append(part)
            part = " " + char
        else:
            part += char
    parts.append(part)
    return "\r\n".join(parts)


def booking_ics(session, actor, bid, revision):
    b = owned_booking(session, actor, bid)
    if b.revision != revision:
        raise DomainError("STALE_BOOKING", "Booking revision is stale.", 409)
    slot = session.get(ScheduleSlot, b.slot_id)

    def fmt(dt):
        return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Elseview//Calendar//EN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{b.id}@elseview",
        f"SEQUENCE:{b.revision}",
        f"DTSTAMP:{fmt(b.created_at)}",
        f"DTSTART:{fmt(slot.starts_at)}",
        f"DTEND:{fmt(slot.ends_at)}",
        "SUMMARY:Research appointment",
        f"STATUS:{'CANCELLED' if b.state == 'cancelled' else 'CONFIRMED'}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(fold(line) for line in lines) + "\r\n"
