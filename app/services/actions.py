from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.meeting_action import MeetingAction
from app.models.meeting_agenda import MeetingAgenda
from app.models.user import User
from app.schemas.ops import CaptureActionCreate
from app.services.meetings import get_meeting_or_404


def list_actions(db: Session, meeting_id: int | None = None) -> list[MeetingAction]:
    query = db.query(MeetingAction).order_by(MeetingAction.created_at.desc())
    if meeting_id is not None:
        query = query.filter(MeetingAction.meeting_id == meeting_id)
    return query.all()


def create_action(
    db: Session,
    payload: CaptureActionCreate,
    current_user: User,
) -> MeetingAction:
    get_meeting_or_404(db, payload.meeting_id)
    if payload.agenda_id is not None:
        agenda = (
            db.query(MeetingAgenda)
            .filter(
                MeetingAgenda.id == payload.agenda_id,
                MeetingAgenda.meeting_id == payload.meeting_id,
            )
            .first()
        )
        if agenda is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="agenda_id does not belong to this meeting.",
            )

    action = MeetingAction(
        meeting_id=payload.meeting_id,
        agenda_id=payload.agenda_id,
        description=payload.description.strip(),
        assigned_to=payload.assigned_to.strip(),
        deadline=payload.deadline,
        department=payload.department,
        priority=payload.priority,
        source="manual",
        created_by=current_user.id,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action
