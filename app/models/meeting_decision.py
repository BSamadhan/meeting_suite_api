from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class MeetingDecision(Base):
    __tablename__ = "meeting_decisions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(Text, nullable=False)
    owner = Column(String(255), nullable=True)
    start_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    meeting = relationship("Meeting", back_populates="decisions")
