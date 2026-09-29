from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class SpeechSegment:
    speaker: str
    text: str
    start_seconds: float | None
    end_seconds: float | None
    confidence: float | None


class SpeechToTextService(Protocol):
    def transcribe(self, audio_path: Path) -> list[SpeechSegment]:
        """Return spoken lines. Do not log the text."""
