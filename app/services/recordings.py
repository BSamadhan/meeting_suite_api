from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.meeting_recording import MeetingRecording
from app.services.meetings import get_meeting_or_404
from app.services.object_storage import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_RECORDING_BYTES,
    build_object_key,
    delete_object,
    public_file_url,
    storage_root,
)

RECORDING_STATUS_UPLOADED = "UPLOADED"
RECORDING_STATUS_PROCESSING = "PROCESSING"
RECORDING_STATUS_COMPLETED = "COMPLETED"
RECORDING_STATUS_FAILED = "FAILED"


def _validate_recording_file(file: UploadFile) -> str:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording file is required.",
        )

    extension = Path(filename).suffix.lower()
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported formats: MP3, WAV, M4A, MP4, WEBM.",
        )
    if (
        content_type
        and content_type not in ALLOWED_CONTENT_TYPES
        and content_type != "application/octet-stream"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported formats: MP3, WAV, M4A, MP4, WEBM.",
        )
    return filename


def create_recording(
    db: Session,
    meeting_id: int,
    file: UploadFile,
    duration: float | None = None,
) -> MeetingRecording:
    get_meeting_or_404(db, meeting_id)
    filename = _validate_recording_file(file)
    object_key = build_object_key(meeting_id, filename)
    destination = storage_root() / object_key
    destination.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_RECORDING_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Recording file is too large.",
                    )
                out.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recording file is empty.",
        )

    recording = MeetingRecording(
        meeting_id=meeting_id,
        file_url=public_file_url(object_key),
        duration=duration,
        status=RECORDING_STATUS_UPLOADED,
    )
    db.add(recording)
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_object(object_key)
        raise
    db.refresh(recording)
    return recording


def recording_file_path(file_url: str) -> Path:
    base = (settings.STORAGE_PUBLIC_BASE_URL or "/files").rstrip("/")
    key = file_url or ""
    marker = f"{base}/"
    if key.startswith(marker):
        key = key[len(marker) :]
    else:
        key = key.lstrip("/")
    root = storage_root().resolve()
    path = (root / key).resolve()
    if root != path and root not in path.parents:
        raise FileNotFoundError(file_url)
    if not path.is_file():
        raise FileNotFoundError(file_url)
    return path


def get_latest_recording(db: Session, meeting_id: int) -> MeetingRecording | None:
    get_meeting_or_404(db, meeting_id)
    return (
        db.query(MeetingRecording)
        .filter(MeetingRecording.meeting_id == meeting_id)
        .order_by(MeetingRecording.created_at.desc(), MeetingRecording.id.desc())
        .first()
    )
