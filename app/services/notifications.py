from datetime import date

from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.meeting_action import MeetingAction
from app.models.notification import Notification
from app.services.notice_rules import KIND_ORDER, build_notices


def list_notifications(db: Session, user_id: int, today: date | None = None) -> list[Notification]:
    current_day = today or date.today()
    _sync_notifications(db, user_id, current_day)
    rows = db.query(Notification).filter(Notification.user_id == user_id).all()
    rows.sort(key=lambda row: (KIND_ORDER.get(row.kind, 9), row.id))
    return rows


def _sync_notifications(db: Session, user_id: int, today: date) -> None:
    meetings = (
        db.query(Meeting)
        .filter(Meeting.created_by == user_id)
        .all()
    )
    actions = (
        db.query(MeetingAction, Meeting)
        .join(Meeting, Meeting.id == MeetingAction.meeting_id)
        .filter(Meeting.created_by == user_id)
        .all()
    )
    desired = build_notices(
        [
            {
                "id": meeting.id,
                "title": meeting.title,
                "status": meeting.status,
                "meeting_date": meeting.meeting_date,
            }
            for meeting in meetings
        ],
        [
            {
                "id": action.id,
                "meeting_id": action.meeting_id,
                "description": action.description,
                "assigned_to": action.assigned_to,
                "deadline": action.deadline,
                "status": action.status,
            }
            for action, _meeting in actions
        ],
        today,
    )
    existing = db.query(Notification).filter(Notification.user_id == user_id).all()
    by_key = {row.dedupe_key: row for row in existing}
    desired_keys = set()
    for item in desired:
        desired_keys.add(item["dedupe_key"])
        row = by_key.get(item["dedupe_key"])
        if row is None:
            db.add(
                Notification(
                    user_id=user_id,
                    kind=item["kind"],
                    dedupe_key=item["dedupe_key"],
                    message=item["message"],
                    meeting_id=item["meeting_id"],
                    action_id=item["action_id"],
                    href=item["href"],
                )
            )
            continue
        row.kind = item["kind"]
        row.message = item["message"]
        row.meeting_id = item["meeting_id"]
        row.action_id = item["action_id"]
        row.href = item["href"]
    for row in existing:
        if row.dedupe_key not in desired_keys:
            db.delete(row)
    db.commit()
