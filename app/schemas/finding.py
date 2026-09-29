from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DecisionResponse(BaseModel):
    id: int
    meeting_id: int
    text: str
    owner: Optional[str] = None
    start_seconds: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RiskResponse(BaseModel):
    id: int
    meeting_id: int
    description: str
    impact: Optional[str] = None
    owner: Optional[str] = None
    mitigation: Optional[str] = None
    status: str
    start_seconds: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
