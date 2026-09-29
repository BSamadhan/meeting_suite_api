# Meeting request/response schemas
from datetime import date, time, datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class ParticipantCreate(BaseModel):
    user_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Registered user id. Omit for guest-only attendees.",
    )
    role: str = "PARTICIPANT"
    status: str = "INVITED"
    is_required: bool = True
    guest_email: Optional[EmailStr] = None
    guest_name: Optional[str] = None


class AgendaCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    order_index: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("order_index", "sequence"),
    )
    duration_minutes: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(populate_by_name=True)


class ParticipantResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    guest_email: Optional[str] = None
    guest_name: Optional[str] = None
    role: str
    status: str
    is_required: bool
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AgendaResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    order_index: int = Field(
        validation_alias=AliasChoices("order_index", "sequence"),
        serialization_alias="order_index",
    )
    duration_minutes: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class MeetingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None

    chair_id: Optional[int] = Field(
        default=None,
        description="Chair user id. Omit this to use the current user.",
    )
    host_name: Optional[str] = None
    guest_email: Optional[str] = None

    meeting_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    duration_minutes: Optional[int] = Field(
        default=None,
        ge=0,
    )

    timezone: Optional[str] = None

    repeat_type: Optional[str] = "NONE"

    reminder_minutes: Optional[int] = Field(
        default=10,
        ge=0,
    )

    meeting_type: str = "ONLINE"

    location: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    auto_generate_meeting_link: bool = True

    meeting_link: Optional[str] = None

    status: str = "Scheduled"


class MeetingCreate(MeetingBase):
    participants: list[ParticipantCreate] = Field(default_factory=list)
    agendas: list[AgendaCreate] = Field(default_factory=list)


class MeetingUpdate(BaseModel):
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
    )
    category: Optional[str] = Field(
        default=None,
    )

    chair_id: Optional[int] = None
    host_name: Optional[str] = None
    guest_email: Optional[str] = None

    meeting_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    duration_minutes: Optional[int] = Field(
        default=None,
        ge=0,
    )

    timezone: Optional[str] = None
    repeat_type: Optional[str] = "NONE"

    reminder_minutes: Optional[int] = Field(
        default=None,
        ge=0,
    )

    meeting_type: Optional[str] = "ONLINE"

    location: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    auto_generate_meeting_link: Optional[bool] = None
    meeting_link: Optional[str] = None

    status: Optional[str] = None

    participants: Optional[list[ParticipantCreate]] = None
    agendas: Optional[list[AgendaCreate]] = None


class MeetingResponse(MeetingBase):
    id: int
    created_by: int

    created_at: datetime
    updated_at: datetime
    actual_start_at: Optional[datetime] = None
    actual_end_at: Optional[datetime] = None
    google_event_id: Optional[str] = None

    participants: list[ParticipantResponse] = Field(default_factory=list)
    agendas: list[AgendaResponse] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
    )


class MeetingHistoryItem(BaseModel):
    id: int
    title: Optional[str] = None
    meeting_date: Optional[date] = None
    actual_end_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MeetingListResponse(BaseModel):
    items: list[MeetingResponse] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    total_pages: int
