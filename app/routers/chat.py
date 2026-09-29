from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.chat import ChatMessageCreate, ChatMessageResponse, ChatTurnResponse
from app.services.chat import ask_meeting, list_chat

router = APIRouter(tags=["Chat"])


@router.get(
    "/{meeting_id}/ai/chat",
    response_model=list[ChatMessageResponse],
)
@router.get(
    "/{meeting_id}/ai/chat/",
    response_model=list[ChatMessageResponse],
    include_in_schema=False,
)
def get_meeting_chat(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_chat(db, meeting_id)


@router.post(
    "/{meeting_id}/ai/chat",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/{meeting_id}/ai/chat/",
    response_model=ChatTurnResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def post_meeting_chat(
    meeting_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_message, assistant_message = ask_meeting(db, meeting_id, payload.text)
    return ChatTurnResponse(user=user_message, assistant=assistant_message)
