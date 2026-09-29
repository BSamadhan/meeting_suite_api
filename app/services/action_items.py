from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.meeting_action import MeetingAction

OPEN_ACTION_STATUSES = {"open", "pending", "in_progress"}
STATUS_LABELS = {
    "open": "pending",
    "pending": "pending",
    "in_progress": "in_progress",
    "inprogress": "in_progress",
    "completed": "completed",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}


def list_action_items(db: Session, user_id: int, today: date | None = None) -> list[dict]:
    current_day = today or date.today()
    rows = (
        db.query(MeetingAction, Meeting)
        .join(Meeting, Meeting.id == MeetingAction.meeting_id)
        .filter(Meeting.created_by == user_id)
        .all()
    )
    items = [_to_item(action, meeting, current_day) for action, meeting in rows]
    items.sort(key=lambda item: (not item["overdue"], item["deadline"] is None, item["deadline"] or date.max, item["id"]))
    return items


def update_action_item_status(
    db: Session,
    user_id: int,
    action_id: int,
    new_status: str,
    today: date | None = None,
) -> dict:
    row = (
        db.query(MeetingAction, Meeting)
        .join(Meeting, Meeting.id == MeetingAction.meeting_id)
        .filter(
            MeetingAction.id == action_id,
            Meeting.created_by == user_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found",
        )
    action, meeting = row
    action.status = new_status
    db.commit()
    db.refresh(action)
    return _to_item(action, meeting, today or date.today())


def normalize_action_status(value: str | None) -> str:
    token = str(value or "").strip().lower().replace(" ", "_")
    return STATUS_LABELS.get(token, "pending")


def is_overdue(action_status: str, deadline: date | None, today: date) -> bool:
    if deadline is None or deadline >= today:
        return False
    return normalize_action_status(action_status) in OPEN_ACTION_STATUSES


def _to_item(action: MeetingAction, meeting: Meeting, today: date) -> dict:
    normalized = normalize_action_status(action.status)
    return {
        "id": action.id,
        "meeting_id": action.meeting_id,
        "meeting_title": meeting.title or "Meeting",
        "description": action.description,
        "assigned_to": action.assigned_to,
        "deadline": action.deadline,
        "status": normalized,
        "overdue": is_overdue(normalized, action.deadline, today),
    }
