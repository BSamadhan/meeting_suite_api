from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.meeting_participant import MeetingParticipant
from app.models.user import User
from app.schemas.participant import MeetingParticipantAdd, normalize_participant_role
from app.services.meetings import get_meeting_or_404


def _to_response(item: MeetingParticipant) -> dict:
    user = item.user
    return {
        "id": item.id,
        "meeting_id": item.meeting_id,
        "user_id": item.user_id,
        "role": item.role,
        "joined_at": item.joined_at,
        "left_at": item.left_at,
        "name": (user.name if user else None) or item.guest_name,
        "email": (user.email if user else None) or item.guest_email,
    }


def list_participants(db: Session, meeting_id: int) -> list[dict]:
    get_meeting_or_404(db, meeting_id)
    rows = (
        db.query(MeetingParticipant)
        .options(selectinload(MeetingParticipant.user))
        .filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.left_at.is_(None),
        )
        .order_by(MeetingParticipant.id.asc())
        .all()
    )
    return [_to_response(row) for row in rows]


def add_participant(
    db: Session,
    meeting_id: int,
    payload: MeetingParticipantAdd,
) -> dict:
    get_meeting_or_404(db, meeting_id)
    role = normalize_participant_role(payload.role)

    user = db.query(User).filter(User.id == payload.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown user id: {payload.user_id}",
        )

    existing = (
        db.query(MeetingParticipant)
        .filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == payload.user_id,
        )
        .first()
    )
    if existing and existing.left_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a participant in this meeting.",
        )
    if existing:
        existing.left_at = None
        existing.role = role
        existing.joined_at = datetime.now()
        db.commit()
        db.refresh(existing)
        existing.user = user
        return _to_response(existing)

    participant = MeetingParticipant(
        meeting_id=meeting_id,
        user_id=payload.user_id,
        role=role,
        status="INVITED",
        is_required=True,
        joined_at=datetime.now(),
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    participant.user = user
    return _to_response(participant)


def remove_participant(db: Session, meeting_id: int, user_id: int) -> None:
    get_meeting_or_404(db, meeting_id)
    participant = (
        db.query(MeetingParticipant)
        .filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id,
            MeetingParticipant.left_at.is_(None),
        )
        .first()
    )
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Participant not found",
        )
    participant.left_at = datetime.now()
    db.commit()
