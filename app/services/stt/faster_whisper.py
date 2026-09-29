import math
from pathlib import Path

from app.core.config import settings
from app.services.stt.types import SpeechSegment

SPEAKER_LABEL = "Speaker"


class FasterWhisperTranscriber:
    """Local speech-to-text. The model stays in memory after the first run."""

    def __init__(self, model_name: str, device: str, compute_type: str) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def transcribe(self, audio_path: Path) -> list[SpeechSegment]:
        model = self._load_model()
        segments, _info = model.transcribe(
            str(audio_path),
            vad_filter=False,
            condition_on_previous_text=False,
        )
        spoken: list[SpeechSegment] = []
        for segment in segments:
            text = str(getattr(segment, "text", "") or "").strip()
            if not text:
                continue
            spoken.append(
                SpeechSegment(
                    speaker=SPEAKER_LABEL,
                    text=text[:20000],
                    start_seconds=_seconds(getattr(segment, "start", None)),
                    end_seconds=_seconds(getattr(segment, "end", None)),
                    confidence=_confidence(getattr(segment, "avg_logprob", None)),
                )
            )
        return spoken

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model


def build_faster_whisper_transcriber() -> FasterWhisperTranscriber:
    return FasterWhisperTranscriber(
        model_name=settings.STT_MODEL,
        device=settings.STT_DEVICE,
        compute_type=settings.STT_COMPUTE_TYPE,
    )


def _seconds(value) -> float | None:
    if value is None:
        return None
    seconds = float(value)
    if seconds < 0:
        return 0.0
    return seconds


def _confidence(avg_logprob) -> float | None:
    if avg_logprob is None:
        return None
    score = math.exp(float(avg_logprob))
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return round(score, 4)
