from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SummaryResponse(BaseModel):
    id: int
    meeting_id: int
    summary_text: str
    key_topics: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
