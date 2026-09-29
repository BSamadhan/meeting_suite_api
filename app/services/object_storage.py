from pathlib import Path
from uuid import uuid4

from app.core.config import settings

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".mp4", ".webm"}
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/aac",
    "audio/webm",
    "video/mp4",
    "video/webm",
    "video/quicktime",
}
MAX_RECORDING_BYTES = 500 * 1024 * 1024


def storage_root() -> Path:
    root = Path(settings.STORAGE_LOCAL_DIR)
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def public_file_url(object_key: str) -> str:
    base = (settings.STORAGE_PUBLIC_BASE_URL or "/files").rstrip("/")
    return f"{base}/{object_key}"


def build_object_key(meeting_id: int, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"meetings/{meeting_id}/recordings/{uuid4().hex}{extension}"


def put_object(object_key: str, data: bytes) -> Path:
    destination = storage_root() / object_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination


def delete_object(object_key: str) -> None:
    destination = storage_root() / object_key
    if destination.exists():
        destination.unlink()
