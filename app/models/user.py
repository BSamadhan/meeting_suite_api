from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # =========================================================
    # Relationships
    # =========================================================

    created_meetings = relationship(
        "Meeting",
        foreign_keys="Meeting.created_by",
        back_populates="creator",
    )

    chaired_meetings = relationship(
        "Meeting",
        foreign_keys="Meeting.chair_id",
        back_populates="chair",
    )

    meeting_participations = relationship(
        "MeetingParticipant",
        back_populates="user",
    )

    google_calendar = relationship(
        "GoogleCalendarConnection",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )