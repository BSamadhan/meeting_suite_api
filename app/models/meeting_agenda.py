from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from app.database import Base


class MeetingAgenda(Base):
    __tablename__ = "meeting_agendas"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    sequence = Column(
        Integer,
        nullable=False,
        default=1,
    )

    duration_minutes = Column(
        Integer,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    # =========================================================
    # Relationships
    # =========================================================

    meeting = relationship(
        "Meeting",
        back_populates="agendas",
    )