from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(30), nullable=False)
    dedupe_key = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=True)
    action_id = Column(Integer, ForeignKey("meeting_actions.id", ondelete="CASCADE"), nullable=True)
    href = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
