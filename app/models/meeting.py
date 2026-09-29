# Meeting, AgendaItem, ActionItem SQLAlchemy models
from datetime import datetime
from sqlalchemy import Column, Boolean, String, Integer, DateTime, Date, Time, ForeignKey, Text

from sqlalchemy.orm import relationship

from app.database import Base

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(
        Integer, 
        primary_key=True, 
        index=True
    )
    title = Column(
        String, 
        index=True
    )
    description = Column(
        Text, 
        nullable=True
    )
    category = Column(
        String, 
        nullable=True
    )
    chair_id = Column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True
    )
    host_name = Column(
        String,
        nullable=True
    )
    guest_email = Column(
        String, 
        nullable=True
    )
    meeting_date = Column(
        Date, 
        nullable=True
    )
    start_time = Column(
        Time, nullable=True
    )
    end_time = Column(
        Time, 
        nullable=True
    )
    duration_minutes = Column(
        "durration_minutes",
        Integer,
        nullable=True
    )
    timezone = Column(
        String, 
        nullable=True
    )

    repeat_type = Column(
        String, 
        nullable=True, 
        default=10
    )
    reminder_minutes = Column(
        Integer,
        nullable=True,
        default=10,
    )
    meeting_type = Column(
        String(50),
        nullable=False,
        default="ONLINE",
    )

    # Used for offline meetings
    location = Column(
        String(500),
        nullable=True,
    )

    auto_generate_meeting_link = Column(
        Boolean,
        nullable=False,
        default=True,
    )
    meeting_link = Column(
        String, 
        nullable=True, 
        unique=True
    )
    google_event_id = Column(String(255), nullable=True)

    status = Column(
        String, 
        nullable=True, 
        default="Scheduled"
    )
    actual_start_at = Column(DateTime, nullable=True)
    actual_end_at = Column(DateTime, nullable=True)

    created_by = Column(
        Integer, 
        ForeignKey("users.id"), 
        nullable=True
    )
    created_at = Column(
        DateTime, 
        default=datetime.now, 
        nullable=True
    )
    updated_at = Column(
        DateTime, 
        default=datetime.now, 
        onupdate=datetime.now, 
        nullable=True
    )

    # =========================================================
    # Relationships
    # =========================================================

    # User who created the meeting
    creator = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_meetings",
    )

    # Chair / Host of the meeting
    chair = relationship(
        "User",
        foreign_keys=[chair_id],
        back_populates="chaired_meetings",
    )

    # Meeting participants
    participants = relationship(
        "MeetingParticipant",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    # Meeting agenda
    agendas = relationship(
        "MeetingAgenda",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    actions = relationship(
        "MeetingAction",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    recordings = relationship(
        "MeetingRecording",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    transcript_segments = relationship(
        "MeetingTranscriptSegment",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="MeetingTranscriptSegment.sequence",
    )

    summaries = relationship(
        "MeetingSummary",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    decisions = relationship(
        "MeetingDecision",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    risks = relationship(
        "MeetingRisk",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )

    ai_messages = relationship(
        "MeetingAiMessage",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
