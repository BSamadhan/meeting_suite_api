from datetime import date, datetime, time
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class AvailabilityBusySlot(BaseModel):
    start: str
    end: str


class AvailabilityParticipantInput(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    guest_email: Optional[str] = None
    role: str = "PARTICIPANT"


class AvailabilityCheckRequest(BaseModel):
    meeting_date: date
    start_time: time
    end_time: time
    timezone: str = "Asia/Kolkata"
    chair: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices("chair", "chair_id"),
    )
    created_by: Optional[int] = None
    participants: list[AvailabilityParticipantInput | int] = Field(
        default_factory=list,
    )
    exclude_meeting_id: Optional[int] = None

    @field_validator("timezone", mode="before")
    @classmethod
    def normalize_timezone(cls, value):
        token = str(value or "Asia/Kolkata").strip().split()[0]
        return token or "Asia/Kolkata"

    @field_validator("participants", mode="before")
    @classmethod
    def normalize_participants(cls, value):
        if not value:
            return []
        normalized = []
        for item in value:
            if isinstance(item, int):
                normalized.append({"user_id": item, "role": "PARTICIPANT"})
            elif isinstance(item, str) and item.isdigit():
                normalized.append({"user_id": int(item), "role": "PARTICIPANT"})
            else:
                normalized.append(item)
        return normalized


class AvailabilityParticipantStatus(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    guest_email: Optional[str] = None
    role: str
    is_available: bool
    calendar_accessible: bool = False
    busy_slots: list[AvailabilityBusySlot] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AvailabilityTimeSlot(BaseModel):
    start: str
    end: str
    timezone: str


class AvailabilityCheckData(BaseModel):
    time_slot: AvailabilityTimeSlot
    all_available: bool
    has_unknown: bool
    participants: list[AvailabilityParticipantStatus] = Field(default_factory=list)


class AvailabilityCheckResponse(BaseModel):
    success: bool
    message: str
    data: AvailabilityCheckData


class LookupItem(BaseModel):
    value: str
    label: str


class GoogleOAuthStatusResponse(BaseModel):
    connected: bool = False
    email: Optional[str] = None
    configured: bool = False
    redirect_uri: Optional[str] = None


class GoogleOAuthConnectResponse(BaseModel):
    connected: bool = False
    auth_url: Optional[str] = None
    detail: Optional[str] = None
    redirect_uri: Optional[str] = None


class CaptureActionCreate(BaseModel):
    meeting_id: int
    agenda_id: Optional[int] = None
    description: str = Field(..., min_length=1)
    assigned_to: str = Field(..., min_length=1)
    deadline: Optional[date] = None
    department: Optional[str] = None
    priority: Optional[str] = None


class DashboardSummary(BaseModel):
    today: int
    upcoming: int
    in_progress: int
    completed: int
    action_items: int
    pending_actions: int
    open_risks: int


class CaptureActionResponse(BaseModel):
    id: int
    meeting_id: int
    agenda_id: Optional[int] = None
    description: str
    assigned_to: Optional[str] = None
    deadline: Optional[date] = None
    department: Optional[str] = None
    priority: Optional[str] = None
    status: str
    source: Optional[str] = None
    start_seconds: Optional[float] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ActionItemResponse(BaseModel):
    id: int
    meeting_id: int
    meeting_title: str
    description: str
    assigned_to: Optional[str] = None
    deadline: Optional[date] = None
    status: str
    overdue: bool = False


class ActionItemStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def clean_status(cls, value: str) -> str:
        token = str(value or "").strip().lower().replace(" ", "_")
        allowed = {"pending", "in_progress", "completed", "cancelled"}
        if token not in allowed:
            raise ValueError("Status must be pending, in_progress, completed, or cancelled.")
        return token
