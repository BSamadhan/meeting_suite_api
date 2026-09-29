from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class MeetingAction(Base):
    __tablename__ = "meeting_actions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agenda_id = Column(
        Integer,
        ForeignKey("meeting_agendas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description = Column(Text, nullable=False)
    assigned_to = Column(String(255), nullable=True)
    deadline = Column(Date, nullable=True)
    department = Column(String(100), nullable=True)
    priority = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")
    source = Column(String(50), nullable=False, default="manual")
    start_seconds = Column(Float, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    meeting = relationship("Meeting", back_populates="actions")
