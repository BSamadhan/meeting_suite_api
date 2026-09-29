from app.core.config import settings
from app.services.stt.faster_whisper import build_faster_whisper_transcriber
from app.services.stt.types import SpeechToTextService

_service: SpeechToTextService | None = None


def get_speech_to_text_service() -> SpeechToTextService:
    global _service
    if _service is None:
        provider = (settings.STT_PROVIDER or "faster_whisper").strip().lower()
        if provider != "faster_whisper":
            raise RuntimeError(f"Unsupported speech-to-text provider: {provider}")
        _service = build_faster_whisper_transcriber()
    return _service
