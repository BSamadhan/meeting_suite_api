from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class MeetingAiMessage(Base):
    __tablename__ = "meeting_ai_messages"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    meeting = relationship("Meeting", back_populates="ai_messages")
