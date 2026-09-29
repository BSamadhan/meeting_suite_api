from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.recording import RecordingResponse
from app.services.recordings import create_recording, get_latest_recording
from app.services.transcription import start_transcription

router = APIRouter(tags=["Recordings"])


@router.post(
    "/{meeting_id}/recording",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/{meeting_id}/recording/",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def upload_meeting_recording(
    meeting_id: int,
    file: UploadFile = File(...),
    duration: float | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_recording(db, meeting_id, file, duration)


@router.get(
    "/{meeting_id}/recording",
    response_model=RecordingResponse,
)
@router.get(
    "/{meeting_id}/recording/",
    response_model=RecordingResponse,
    include_in_schema=False,
)
def get_meeting_recording(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recording = get_latest_recording(db, meeting_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found",
        )
    return recording


@router.post(
    "/{meeting_id}/speech-to-text",
    response_model=RecordingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@router.post(
    "/{meeting_id}/speech-to-text/",
    response_model=RecordingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
def run_meeting_speech_to_text(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return start_transcription(db, meeting_id, background_tasks)
