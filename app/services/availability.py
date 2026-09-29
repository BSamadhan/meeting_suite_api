from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session, selectinload

from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.ops import (
    AvailabilityBusySlot,
    AvailabilityCheckData,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    AvailabilityParticipantStatus,
    AvailabilityTimeSlot,
)
from app.services.google_oauth import load_calendar_connections, query_freebusy

INACTIVE_STATUSES = {"cancelled", "completed"}
DEFAULT_TIMEZONE = "Asia/Kolkata"


def _naive_time(value):
    if value is None:
        return None
    if getattr(value, "tzinfo", None) is not None:
        return value.replace(tzinfo=None)
    return value


def _zoneinfo(name: str):
    token = (name or DEFAULT_TIMEZONE).strip().split()[0] or DEFAULT_TIMEZONE
    try:
        return token, ZoneInfo(token)
    except (ZoneInfoNotFoundError, Exception):
        if token in {"Asia/Kolkata", "Asia/Calcutta"}:
            return DEFAULT_TIMEZONE, dt_timezone(timedelta(hours=5, minutes=30))
        return DEFAULT_TIMEZONE, dt_timezone.utc


def _combine(meeting_date, clock, tz) -> datetime:
    naive = datetime.combine(meeting_date, _naive_time(clock))
    return naive.replace(tzinfo=tz)


def _as_iso(value, tz) -> str:
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=tz)
    return moment.astimezone(tz).isoformat()


def _role_label(role: str | None) -> str:
    text = str(role or "participant").strip().lower()
    return text or "participant"


def _collect_people(payload: AvailabilityCheckRequest) -> list[dict]:
    people: list[dict] = []
    seen_ids: set[int] = set()
    seen_emails: set[str] = set()

    def add_person(
        user_id: int | None,
        email: str | None,
        guest_email: str | None,
        role: str,
    ) -> None:
        email_key = (email or guest_email or "").strip().lower()
        if user_id and user_id in seen_ids:
            return
        if not user_id and email_key and email_key in seen_emails:
            return
        if user_id:
            seen_ids.add(user_id)
        if email_key:
            seen_emails.add(email_key)
        people.append(
            {
                "user_id": user_id,
                "email": email,
                "guest_email": guest_email,
                "role": _role_label(role),
            }
        )

    if payload.chair:
        add_person(payload.chair, None, None, "chair")
    if payload.created_by:
        add_person(payload.created_by, None, None, "organizer")
    for item in payload.participants or []:
        add_person(
            item.user_id,
            item.email,
            item.guest_email,
            item.role or "participant",
        )
    return people


def _empty_response(
    *,
    success: bool,
    message: str,
    start: str,
    end: str,
    timezone_name: str,
    all_available: bool = False,
    has_unknown: bool = False,
    participants: list[AvailabilityParticipantStatus] | None = None,
) -> AvailabilityCheckResponse:
    return AvailabilityCheckResponse(
        success=success,
        message=message,
        data=AvailabilityCheckData(
            time_slot=AvailabilityTimeSlot(
                start=start,
                end=end,
                timezone=timezone_name,
            ),
            all_available=all_available,
            has_unknown=has_unknown,
            participants=participants or [],
        ),
    )


def _local_busy_by_user(
    meetings: list[Meeting],
    start_at: datetime,
    end_at: datetime,
    tz,
) -> dict[int, list[AvailabilityBusySlot]]:
    busy: dict[int, list[AvailabilityBusySlot]] = {}
    for meeting in meetings:
        if str(meeting.status or "").strip().lower() in INACTIVE_STATUSES:
            continue
        meeting_start = _naive_time(meeting.start_time)
        meeting_end = _naive_time(meeting.end_time)
        if meeting_start is None or meeting_end is None or meeting.meeting_date is None:
            continue
        local_start = _combine(meeting.meeting_date, meeting_start, tz)
        local_end = _combine(meeting.meeting_date, meeting_end, tz)
        if local_end <= start_at or local_start >= end_at:
            continue

        involved_ids = {
            participant.user_id
            for participant in meeting.participants
            if participant.user_id
        }
        if meeting.chair_id:
            involved_ids.add(meeting.chair_id)
        if meeting.created_by:
            involved_ids.add(meeting.created_by)

        slot = AvailabilityBusySlot(
            start=_as_iso(local_start, tz),
            end=_as_iso(local_end, tz),
        )
        for user_id in involved_ids:
            busy.setdefault(user_id, []).append(slot)
    return busy


def check_availability(
    db: Session,
    payload: AvailabilityCheckRequest,
    current_user: User | None = None,
) -> AvailabilityCheckResponse:
    timezone_name, tz = _zoneinfo(payload.timezone)
    start_clock = _naive_time(payload.start_time)
    end_clock = _naive_time(payload.end_time)

    if start_clock is None or end_clock is None:
        return _empty_response(
            success=False,
            message="Start time and end time are required.",
            start="",
            end="",
            timezone_name=timezone_name,
        )

    start_at = _combine(payload.meeting_date, start_clock, tz)
    end_at = _combine(payload.meeting_date, end_clock, tz)
    start_iso = start_at.isoformat()
    end_iso = end_at.isoformat()

    if end_at <= start_at:
        return _empty_response(
            success=False,
            message="End time must be after start time.",
            start=start_iso,
            end=end_iso,
            timezone_name=timezone_name,
        )

    if payload.created_by is None and current_user is not None:
        payload.created_by = current_user.id
    if payload.chair is None and current_user is not None:
        payload.chair = current_user.id

    people = _collect_people(payload)
    user_ids = {person["user_id"] for person in people if person.get("user_id")}
    emails = {
        str(person.get("email") or person.get("guest_email")).strip().lower()
        for person in people
        if not person.get("user_id") and (person.get("email") or person.get("guest_email"))
    }

    users_by_id: dict[int, User] = {}
    if user_ids:
        users_by_id = {
            user.id: user
            for user in db.query(User).filter(User.id.in_(user_ids)).all()
        }
    users_by_email: dict[str, User] = {}
    if emails:
        users_by_email = {
            user.email.lower(): user
            for user in db.query(User).filter(User.email.in_(emails)).all()
        }

    for person in people:
        user = None
        if person.get("user_id"):
            user = users_by_id.get(person["user_id"])
        elif person.get("email") or person.get("guest_email"):
            key = str(person.get("email") or person.get("guest_email")).strip().lower()
            user = users_by_email.get(key)
            if user:
                person["user_id"] = user.id
                user_ids.add(user.id)
        if user and not person.get("email"):
            person["email"] = user.email

    query = (
        db.query(Meeting)
        .options(selectinload(Meeting.participants))
        .filter(Meeting.meeting_date == payload.meeting_date)
    )
    if payload.exclude_meeting_id:
        query = query.filter(Meeting.id != payload.exclude_meeting_id)
    local_busy = _local_busy_by_user(query.all(), start_at, end_at, tz)
    connections = load_calendar_connections(db, user_ids)

    statuses: list[AvailabilityParticipantStatus] = []
    for person in people:
        user_id = person.get("user_id")
        busy_slots = list(local_busy.get(user_id, [])) if user_id else []
        errors: list[str] = []
        calendar_accessible = False
        connection = connections.get(user_id) if user_id else None
        if connection:
            google = query_freebusy(
                db,
                connection,
                start_iso,
                end_iso,
                timezone_name,
            )
            calendar_accessible = bool(google.get("calendar_accessible"))
            errors.extend(google.get("errors") or [])
            for slot in google.get("busy_slots") or []:
                busy_slots.append(
                    AvailabilityBusySlot(
                        start=_as_iso(slot["start"], tz),
                        end=_as_iso(slot["end"], tz),
                    )
                )
        unique_slots: list[AvailabilityBusySlot] = []
        seen_slots: set[tuple[str, str]] = set()
        for slot in busy_slots:
            key = (slot.start, slot.end)
            if key in seen_slots:
                continue
            seen_slots.add(key)
            unique_slots.append(slot)

        statuses.append(
            AvailabilityParticipantStatus(
                email=person.get("email"),
                user_id=user_id,
                guest_email=person.get("guest_email"),
                role=person["role"],
                is_available=len(unique_slots) == 0,
                calendar_accessible=calendar_accessible,
                busy_slots=unique_slots,
                errors=errors,
            )
        )

    all_available = all(item.is_available for item in statuses) if statuses else True
    has_unknown = any(not item.calendar_accessible for item in statuses)
    if not statuses:
        message = "No participants to check."
    elif all_available and not has_unknown:
        message = "All participants are available for this time slot."
    elif not all_available:
        message = "Some participants are not available for this time slot."
    else:
        message = "Time slot looks free, but some calendars could not be checked."

    return _empty_response(
        success=True,
        message=message,
        start=start_iso,
        end=end_iso,
        timezone_name=timezone_name,
        all_available=all_available,
        has_unknown=has_unknown,
        participants=statuses,
    )
