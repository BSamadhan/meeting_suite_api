import logging

from app.database import SessionLocal
from app.models.meeting_recording import MeetingRecording
from app.services.recordings import (
    RECORDING_STATUS_COMPLETED,
    RECORDING_STATUS_FAILED,
    recording_file_path,
)
from app.services.stt import get_speech_to_text_service
from app.services.transcripts import replace_speech_segments

logger = logging.getLogger(__name__)

FAILURE_MESSAGE = "Speech to text could not read this recording."
MISSING_FILE_MESSAGE = "The recording file could not be found."
UNAVAILABLE_MESSAGE = "Speech to text is not available on this server."


def transcribe_recording_job(recording_id: int) -> None:
    db = SessionLocal()
    try:
        recording = db.get(MeetingRecording, recording_id)
        if recording is None:
            return
        try:
            audio_path = recording_file_path(recording.file_url)
        except FileNotFoundError:
            _mark_failed(db, recording, MISSING_FILE_MESSAGE)
            return
        try:
            segments = get_speech_to_text_service().transcribe(audio_path)
        except ModuleNotFoundError:
            logger.exception(
                "Speech-to-text provider is not installed for recording %s",
                recording_id,
            )
            _mark_failed(db, recording, UNAVAILABLE_MESSAGE)
            return
        except Exception:
            logger.exception("Speech to text failed for recording %s", recording_id)
            _mark_failed(db, recording, FAILURE_MESSAGE)
            return

        replace_speech_segments(db, recording.meeting_id, segments)
        recording.status = RECORDING_STATUS_COMPLETED
        recording.error_message = None
        db.commit()
    except Exception:
        logger.exception("Speech to text failed for recording %s", recording_id)
        db.rollback()
        recording = db.get(MeetingRecording, recording_id)
        if recording is not None:
            _mark_failed(db, recording, FAILURE_MESSAGE)
    finally:
        db.close()


def _mark_failed(db, recording: MeetingRecording, message: str) -> None:
    recording.status = RECORDING_STATUS_FAILED
    recording.error_message = message[:1000]
    db.commit()
