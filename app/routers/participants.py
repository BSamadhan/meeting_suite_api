from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.participant import MeetingParticipantAdd, MeetingParticipantResponse
from app.services.participants import add_participant, list_participants, remove_participant

router = APIRouter(tags=["Participants"])


@router.get(
    "/{meeting_id}/participants",
    response_model=list[MeetingParticipantResponse],
)
@router.get(
    "/{meeting_id}/participants/",
    response_model=list[MeetingParticipantResponse],
    include_in_schema=False,
)
def get_meeting_participants(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_participants(db, meeting_id)


@router.post(
    "/{meeting_id}/participants",
    response_model=MeetingParticipantResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/{meeting_id}/participants/",
    response_model=MeetingParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def post_meeting_participant(
    meeting_id: int,
    payload: MeetingParticipantAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return add_participant(db, meeting_id, payload)


@router.delete(
    "/{meeting_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@router.delete(
    "/{meeting_id}/participants/{user_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def delete_meeting_participant(
    meeting_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    remove_participant(db, meeting_id, user_id)
    return None
