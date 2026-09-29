from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class MeetingRisk(Base):
    __tablename__ = "meeting_risks"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description = Column(Text, nullable=False)
    impact = Column(String(255), nullable=True)
    owner = Column(String(255), nullable=True)
    mitigation = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")
    start_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    meeting = relationship("Meeting", back_populates="risks")
