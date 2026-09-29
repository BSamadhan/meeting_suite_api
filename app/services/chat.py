from sqlalchemy.orm import Session

from app.models.meeting_ai_message import MeetingAiMessage
from app.services.ai.grounded_chat import answer_from_records
from app.services.actions import list_actions
from app.services.meetings import get_meeting_or_404
from app.services.summaries import latest_summary, list_decisions, list_risks
from app.services.transcripts import list_transcript


def list_chat(db: Session, meeting_id: int) -> list[MeetingAiMessage]:
    get_meeting_or_404(db, meeting_id)
    return (
        db.query(MeetingAiMessage)
        .filter(MeetingAiMessage.meeting_id == meeting_id)
        .order_by(MeetingAiMessage.id.asc())
        .all()
    )


def ask_meeting(db: Session, meeting_id: int, question: str) -> tuple[MeetingAiMessage, MeetingAiMessage]:
    get_meeting_or_404(db, meeting_id)
    lines = list_transcript(db, meeting_id)
    summary = latest_summary(db, meeting_id)
    decisions = list_decisions(db, meeting_id)
    actions = list_actions(db, meeting_id)
    risks = list_risks(db, meeting_id)
    reply = answer_from_records(
        question,
        [line.text for line in lines],
        summary.summary_text if summary else None,
        [
            {
                "text": item.text,
                "owner": item.owner,
                "start_seconds": item.start_seconds,
            }
            for item in decisions
        ],
        [
            {
                "description": item.description,
                "assigned_to": item.assigned_to,
                "deadline": item.deadline.isoformat() if item.deadline else None,
                "start_seconds": item.start_seconds,
            }
            for item in actions
        ],
        [
            {
                "description": item.description,
                "impact": item.impact,
                "owner": item.owner,
                "mitigation": item.mitigation,
                "start_seconds": item.start_seconds,
            }
            for item in risks
        ],
    )
    user_message = MeetingAiMessage(meeting_id=meeting_id, role="user", text=question)
    assistant_message = MeetingAiMessage(meeting_id=meeting_id, role="assistant", text=reply)
    db.add(user_message)
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return user_message, assistant_message
