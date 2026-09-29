from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field


PARTICIPANT_ROLES = ("HOST", "PARTICIPANT", "ORGANIZER")


def normalize_participant_role(role: str | None) -> str:
    value = str(role or "PARTICIPANT").strip().upper()
    aliases = {
        "ATTENDEE": "PARTICIPANT",
        "CHAIR": "HOST",
        "HOST": "HOST",
        "PARTICIPANT": "PARTICIPANT",
        "ORGANIZER": "ORGANIZER",
    }
    mapped = aliases.get(value, value)
    if mapped not in PARTICIPANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role must be one of: {', '.join(PARTICIPANT_ROLES)}",
        )
    return mapped


class MeetingParticipantAdd(BaseModel):
    user_id: int = Field(..., gt=0)
    role: str = "PARTICIPANT"


class MeetingParticipantResponse(BaseModel):
    id: int
    meeting_id: int
    user_id: Optional[int] = None
    role: str
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    name: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
