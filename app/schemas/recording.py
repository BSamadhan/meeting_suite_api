from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class RecordingResponse(BaseModel):
    recording_id: int = Field(validation_alias=AliasChoices("id", "recording_id"))
    meeting_id: int
    file_url: str
    duration: Optional[float] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
