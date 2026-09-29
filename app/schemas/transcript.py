from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _required_text(value: str, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required.")
    return cleaned


class TranscriptSegmentIn(BaseModel):
    speaker: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=20000)
    start_seconds: Optional[float] = Field(default=None, ge=0)
    end_seconds: Optional[float] = Field(default=None, ge=0)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    @field_validator("speaker")
    @classmethod
    def clean_speaker(cls, value: str) -> str:
        return _required_text(value, "speaker")

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return _required_text(value, "text")

    @model_validator(mode="after")
    def end_after_start(self):
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError("end_seconds must be greater than or equal to start_seconds.")
        return self


class TranscriptReplace(BaseModel):
    segments: list[TranscriptSegmentIn] = Field(default_factory=list, max_length=5000)


class TranscriptNoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=20000)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return _required_text(value, "text")


class TranscriptSegmentResponse(BaseModel):
    id: int
    meeting_id: int
    sequence: int
    speaker: str
    text: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
