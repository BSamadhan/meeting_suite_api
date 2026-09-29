# Meeting business logic
from datetime import date, datetime, time, timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.meeting import Meeting
from app.models.meeting_agenda import MeetingAgenda
from app.models.meeting_participant import MeetingParticipant
from app.models.user import User
from app.schemas.meeting import AgendaCreate, MeetingCreate, MeetingUpdate, ParticipantCreate
from app.schemas.participant import normalize_participant_role
from app.services.google_oauth import create_google_meet_event


def _naive_time(value: Optional[time]) -> Optional[time]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def _clean_optional_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    if stripped == "" or stripped.lower() == "string":
        return None
    return stripped


def _meeting_query(db: Session):
    return db.query(Meeting).options(
        selectinload(Meeting.participants),
        selectinload(Meeting.agendas),
    )


def get_meeting(db: Session, meeting_id: int) -> Meeting | None:
    return _meeting_query(db).filter(Meeting.id == meeting_id).first()


def get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    meeting = get_meeting(db, meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return meeting


def _status_key(value: Optional[str]) -> str:
    return str(value or "").strip().lower()


def set_meeting_status(
    db: Session,
    meeting_id: int,
    new_status: str,
    allowed_from: set[str],
) -> Meeting:
    meeting = get_meeting_or_404(db, meeting_id)
    current = _status_key(meeting.status)
    target = _status_key(new_status)
    if current == target:
        return meeting
    if current not in {item.lower() for item in allowed_from}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot change meeting from '{meeting.status}' to '{new_status}'."
            ),
        )
    meeting.status = new_status
    db.commit()
    updated = get_meeting(db, meeting.id)
    return updated or meeting


def _stamp_once(db: Session, meeting: Meeting, field: str) -> Meeting:
    if getattr(meeting, field) is not None:
        return meeting
    setattr(meeting, field, datetime.now())
    db.commit()
    return get_meeting(db, meeting.id) or meeting


def start_meeting(db: Session, meeting_id: int) -> Meeting:
    meeting = set_meeting_status(
        db,
        meeting_id,
        "ongoing",
        {"scheduled"},
    )
    return _stamp_once(db, meeting, "actual_start_at")


def end_meeting(db: Session, meeting_id: int) -> Meeting:
    meeting = set_meeting_status(
        db,
        meeting_id,
        "completed",
        {"ongoing", "scheduled"},
    )
    return _stamp_once(db, meeting, "actual_end_at")


def cancel_meeting(db: Session, meeting_id: int) -> Meeting:
    return set_meeting_status(
        db,
        meeting_id,
        "cancelled",
        {"scheduled", "ongoing"},
    )


def _filtered_meetings_query(
    db: Session,
    user_id: int,
    search: Optional[str] = None,
    meeting_status: Optional[str] = None,
    meeting_date: Optional[date] = None,
    period: Optional[str] = None,
    meeting_type: Optional[str] = None,
):
    query = db.query(Meeting).filter(Meeting.created_by == user_id)

    term = (search or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            or_(
                Meeting.title.ilike(like),
                Meeting.location.ilike(like),
                Meeting.host_name.ilike(like),
                Meeting.description.ilike(like),
                Meeting.category.ilike(like),
            )
        )

    status_value = (meeting_status or "").strip()
    if status_value and status_value.lower() != "all":
        query = query.filter(func.lower(Meeting.status) == status_value.lower())

    if meeting_date is not None:
        query = query.filter(Meeting.meeting_date == meeting_date)

    period_value = (period or "").strip().lower()
    if period_value == "upcoming":
        query = query.filter(func.lower(Meeting.status).in_(("scheduled", "ongoing")))
    elif period_value == "past":
        query = query.filter(
            func.lower(Meeting.status).in_(("completed", "cancelled"))
        )

    type_value = (meeting_type or "").strip().upper()
    if type_value == "OFFLINE":
        query = query.filter(func.upper(Meeting.meeting_type) == "OFFLINE")
    elif type_value == "ONLINE":
        query = query.filter(
            func.upper(func.coalesce(Meeting.meeting_type, "ONLINE")) != "OFFLINE"
        )

    return query


def list_completed_history(db: Session, user_id: int) -> list[Meeting]:
    return (
        db.query(Meeting)
        .filter(
            Meeting.created_by == user_id,
            func.lower(Meeting.status) == "completed",
        )
        .order_by(Meeting.actual_end_at.desc().nullslast(), Meeting.id.desc())
        .all()
    )


def list_meetings(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    meeting_status: Optional[str] = None,
    meeting_date: Optional[date] = None,
    period: Optional[str] = None,
    meeting_type: Optional[str] = None,
) -> tuple[list[Meeting], int]:
    total = _filtered_meetings_query(
        db,
        user_id,
        search=search,
        meeting_status=meeting_status,
        meeting_date=meeting_date,
        period=period,
        meeting_type=meeting_type,
    ).count()
    items = (
        _filtered_meetings_query(
            db,
            user_id,
            search=search,
            meeting_status=meeting_status,
            meeting_date=meeting_date,
            period=period,
            meeting_type=meeting_type,
        )
        .options(
            selectinload(Meeting.participants),
            selectinload(Meeting.agendas),
        )
        .order_by(Meeting.meeting_date.desc(), Meeting.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def _attendee_emails(
    db: Session,
    participants: list[ParticipantCreate],
    chair_id: Optional[int],
    guest_email: Optional[str],
) -> list[str]:
    user_ids = {item.user_id for item in participants if item.user_id}
    if chair_id:
        user_ids.add(chair_id)
    emails: list[str] = []
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        emails.extend(user.email for user in users if user.email)
    emails.extend(
        str(item.guest_email) for item in participants if item.guest_email
    )
    if guest_email:
        emails.append(guest_email)
    unique: list[str] = []
    seen: set[str] = set()
    for email in emails:
        key = email.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(email.strip())
    return unique


def _ensure_users_exist(db: Session, user_ids: set[int]) -> None:
    user_ids = {user_id for user_id in user_ids if user_id}
    if not user_ids:
        return
    existing = {
        user.id
        for user in db.query(User).filter(User.id.in_(user_ids)).all()
    }
    missing = sorted(user_ids - existing)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown user id(s): {missing}",
        )


def _resolve_chair_id(db: Session, chair_id: Optional[int], current_user: User) -> int:
    if chair_id is None:
        return current_user.id
    _ensure_users_exist(db, {chair_id})
    return chair_id


def _build_participant(meeting_id: int, item: ParticipantCreate) -> MeetingParticipant:
    return MeetingParticipant(
        meeting_id=meeting_id,
        user_id=item.user_id,
        guest_email=item.guest_email,
        guest_name=item.guest_name,
        role=normalize_participant_role(item.role),
        status=item.status,
        is_required=item.is_required,
    )


def _build_agenda(meeting_id: int, item: AgendaCreate) -> MeetingAgenda:
    return MeetingAgenda(
        meeting_id=meeting_id,
        title=item.title,
        description=item.description,
        sequence=item.order_index,
        duration_minutes=item.duration_minutes,
    )


def _replace_participants(
    db: Session,
    meeting: Meeting,
    participants: list[ParticipantCreate],
) -> None:
    _ensure_users_exist(db, {item.user_id for item in participants})
    db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting.id
    ).delete()
    for item in participants:
        db.add(_build_participant(meeting.id, item))


def _replace_agendas(
    db: Session,
    meeting: Meeting,
    agendas: list[AgendaCreate],
) -> None:
    db.query(MeetingAgenda).filter(
        MeetingAgenda.meeting_id == meeting.id
    ).delete()
    for item in agendas:
        db.add(_build_agenda(meeting.id, item))


def create_meeting(
    db: Session,
    meeting_data: MeetingCreate,
    current_user: User,
) -> Meeting:
    payload = meeting_data.model_dump()
    participants = [
        ParticipantCreate.model_validate(item)
        for item in payload.pop("participants", [])
    ]
    agendas = [
        AgendaCreate.model_validate(item)
        for item in payload.pop("agendas", [])
    ]

    payload["start_time"] = _naive_time(payload.get("start_time"))
    payload["end_time"] = _naive_time(payload.get("end_time"))
    payload["guest_email"] = _clean_optional_str(payload.get("guest_email"))
    payload["location"] = _clean_optional_str(payload.get("location"))
    payload["meeting_link"] = _clean_optional_str(payload.get("meeting_link"))
    payload["timezone"] = _clean_optional_str(payload.get("timezone"))
    payload["chair_id"] = _resolve_chair_id(
        db,
        payload.get("chair_id"),
        current_user,
    )
    _ensure_users_exist(db, {item.user_id for item in participants})

    meeting_type = str(payload.get("meeting_type") or "ONLINE").upper()
    is_online = meeting_type != "OFFLINE"
    if is_online and (
        payload.get("auto_generate_meeting_link") or payload.get("meeting_link")
    ):
        if payload.get("start_time") is None or payload.get("meeting_date") is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Online meetings need a date and start time to create Google Meet.",
            )
        end_time = payload.get("end_time")
        if end_time is None:
            minutes = payload.get("duration_minutes") or 30
            end_time = (
                datetime.combine(date.today(), payload["start_time"])
                + timedelta(minutes=int(minutes))
            ).time()
            payload["end_time"] = end_time
        event = create_google_meet_event(
            db,
            organizer_id=current_user.id,
            title=payload.get("title") or "Meeting",
            description=payload.get("description"),
            meeting_date=payload["meeting_date"],
            start_time=payload["start_time"],
            end_time=end_time,
            timezone_name=payload.get("timezone") or "Asia/Kolkata",
            attendee_emails=_attendee_emails(
                db,
                participants,
                payload.get("chair_id"),
                payload.get("guest_email"),
            ),
            existing_meet_url=payload.get("meeting_link"),
        )
        payload["meeting_link"] = event["meet_url"]
        payload["google_event_id"] = event["event_id"]

    meeting = Meeting(**payload, created_by=current_user.id)
    db.add(meeting)
    db.flush()

    for item in participants:
        db.add(_build_participant(meeting.id, item))
    for item in agendas:
        db.add(_build_agenda(meeting.id, item))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not create meeting. "
                "Check that chair_id and participant user ids exist, "
                "and that meeting_link is unique."
            ),
        )

    created = get_meeting(db, meeting.id)
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Meeting was created but could not be reloaded.",
        )
    return created


def update_meeting(
    db: Session,
    meeting: Meeting,
    meeting_data: MeetingUpdate,
    current_user: User,
) -> Meeting:
    update_data = meeting_data.model_dump(exclude_unset=True)
    participants = update_data.pop("participants", None)
    agendas = update_data.pop("agendas", None)

    if "start_time" in update_data:
        update_data["start_time"] = _naive_time(update_data.get("start_time"))
    if "end_time" in update_data:
        update_data["end_time"] = _naive_time(update_data.get("end_time"))
    if "guest_email" in update_data:
        update_data["guest_email"] = _clean_optional_str(update_data.get("guest_email"))
    if "location" in update_data:
        update_data["location"] = _clean_optional_str(update_data.get("location"))
    if "meeting_link" in update_data:
        update_data["meeting_link"] = _clean_optional_str(update_data.get("meeting_link"))
    if "timezone" in update_data:
        update_data["timezone"] = _clean_optional_str(update_data.get("timezone"))
    if "chair_id" in update_data:
        update_data["chair_id"] = _resolve_chair_id(
            db,
            update_data.get("chair_id"),
            current_user,
        )

    for field, value in update_data.items():
        setattr(meeting, field, value)

    if participants is not None:
        _replace_participants(
            db,
            meeting,
            [ParticipantCreate.model_validate(item) for item in participants],
        )
    if agendas is not None:
        _replace_agendas(
            db,
            meeting,
            [AgendaCreate.model_validate(item) for item in agendas],
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not update meeting. "
                "Check that chair_id and participant user ids exist, "
                "and that meeting_link is unique."
            ),
        )

    updated = get_meeting(db, meeting.id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return updated
