from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.meeting_action import MeetingAction
from app.models.meeting_risk import MeetingRisk
from app.schemas.ops import DashboardSummary

PENDING_ACTION_STATUSES = ("open", "pending")
OPEN_WORK_STATUSES = ("open", "pending", "in_progress")


def _count_status(query, status_value: str) -> int:
    return query.filter(func.lower(Meeting.status) == status_value).count()


def get_dashboard_summary(db: Session, user_id: int) -> DashboardSummary:
    meetings = db.query(Meeting).filter(Meeting.created_by == user_id)
    actions = (
        db.query(MeetingAction)
        .join(Meeting, Meeting.id == MeetingAction.meeting_id)
        .filter(Meeting.created_by == user_id)
    )
    today = date.today()
    return DashboardSummary(
        today=meetings.filter(
            Meeting.meeting_date == today,
            func.lower(Meeting.status) != "cancelled",
        ).count(),
        upcoming=_count_status(meetings, "scheduled"),
        in_progress=_count_status(meetings, "ongoing"),
        completed=_count_status(meetings, "completed"),
        action_items=actions.count(),
        pending_actions=actions.filter(
            func.lower(MeetingAction.status).in_(OPEN_WORK_STATUSES)
        ).count(),
        open_risks=(
            db.query(MeetingRisk)
            .join(Meeting, Meeting.id == MeetingRisk.meeting_id)
            .filter(
                Meeting.created_by == user_id,
                func.lower(MeetingRisk.status).in_(PENDING_ACTION_STATUSES),
            )
            .count()
        ),
    )
