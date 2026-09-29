from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.transcript import (
    TranscriptNoteCreate,
    TranscriptReplace,
    TranscriptSegmentResponse,
)
from app.services.transcripts import add_note, list_transcript, replace_transcript

router = APIRouter(tags=["Transcript"])


@router.get(
    "/{meeting_id}/transcript",
    response_model=list[TranscriptSegmentResponse],
)
@router.get(
    "/{meeting_id}/transcript/",
    response_model=list[TranscriptSegmentResponse],
    include_in_schema=False,
)
def get_meeting_transcript(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_transcript(db, meeting_id)


@router.put(
    "/{meeting_id}/transcript",
    response_model=list[TranscriptSegmentResponse],
)
@router.put(
    "/{meeting_id}/transcript/",
    response_model=list[TranscriptSegmentResponse],
    include_in_schema=False,
)
def put_meeting_transcript(
    meeting_id: int,
    payload: TranscriptReplace,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return replace_transcript(db, meeting_id, payload)


@router.post(
    "/{meeting_id}/notes",
    response_model=TranscriptSegmentResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/{meeting_id}/notes/",
    response_model=TranscriptSegmentResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def post_meeting_note(
    meeting_id: int,
    payload: TranscriptNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return add_note(db, meeting_id, payload.text)
