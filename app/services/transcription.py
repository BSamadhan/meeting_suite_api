from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.jobs.transcribe_recording import transcribe_recording_job
from app.models.meeting_recording import MeetingRecording
from app.services.recordings import (
    RECORDING_STATUS_PROCESSING,
    get_latest_recording,
)


def start_transcription(
    db: Session,
    meeting_id: int,
    background_tasks: BackgroundTasks,
) -> MeetingRecording:
    recording = get_latest_recording(db, meeting_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload a recording before running speech to text.",
        )
    if recording.status == RECORDING_STATUS_PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Speech to text is already running for this recording.",
        )
    recording.status = RECORDING_STATUS_PROCESSING
    recording.error_message = None
    db.commit()
    db.refresh(recording)
    background_tasks.add_task(transcribe_recording_job, recording.id)
    return recording
