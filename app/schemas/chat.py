from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = str(value or "").strip()
        if not cleaned:
            raise ValueError("text is required.")
        return cleaned


class ChatMessageResponse(BaseModel):
    id: int
    meeting_id: int
    role: str
    text: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatTurnResponse(BaseModel):
    user: ChatMessageResponse
    assistant: ChatMessageResponse
