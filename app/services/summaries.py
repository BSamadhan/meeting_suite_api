from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.meeting_action import MeetingAction
from app.models.meeting_decision import MeetingDecision
from app.models.meeting_risk import MeetingRisk
from app.models.meeting_summary import MeetingSummary
from app.services.ai import get_summarizer
from app.services.ai.findings import extract_findings
from app.services.meetings import get_meeting_or_404
from app.services.transcripts import list_transcript

TRANSCRIPT_SOURCE = "transcript"


def latest_summary(db: Session, meeting_id: int) -> MeetingSummary | None:
    list_transcript(db, meeting_id)
    return (
        db.query(MeetingSummary)
        .filter(MeetingSummary.meeting_id == meeting_id)
        .order_by(MeetingSummary.created_at.desc(), MeetingSummary.id.desc())
        .first()
    )


def analyze_meeting(db: Session, meeting_id: int) -> MeetingSummary:
    lines = list_transcript(db, meeting_id)
    if not any((line.text or "").strip() for line in lines):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a transcript before creating a summary.",
        )
    try:
        brief = get_summarizer().summarize(lines)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Meeting summary is not available on this server.",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Add a transcript before creating a summary.",
        ) from None

    row = MeetingSummary(
        meeting_id=meeting_id,
        summary_text=brief.summary_text,
        key_topics=brief.key_topics,
    )
    db.add(row)
    meeting = get_meeting_or_404(db, meeting_id)
    _replace_transcript_findings(db, meeting_id, lines, meeting.meeting_date)
    db.commit()
    db.refresh(row)
    return row


def list_decisions(db: Session, meeting_id: int) -> list[MeetingDecision]:
    get_meeting_or_404(db, meeting_id)
    return (
        db.query(MeetingDecision)
        .filter(MeetingDecision.meeting_id == meeting_id)
        .order_by(MeetingDecision.start_seconds.asc().nullslast(), MeetingDecision.id.asc())
        .all()
    )


def list_risks(db: Session, meeting_id: int) -> list[MeetingRisk]:
    get_meeting_or_404(db, meeting_id)
    return (
        db.query(MeetingRisk)
        .filter(MeetingRisk.meeting_id == meeting_id)
        .order_by(MeetingRisk.start_seconds.asc().nullslast(), MeetingRisk.id.asc())
        .all()
    )


def _replace_transcript_findings(db: Session, meeting_id: int, lines, meeting_date) -> None:
    findings = extract_findings(lines, meeting_date)
    (
        db.query(MeetingDecision)
        .filter(MeetingDecision.meeting_id == meeting_id)
        .delete(synchronize_session=False)
    )
    (
        db.query(MeetingRisk)
        .filter(MeetingRisk.meeting_id == meeting_id)
        .delete(synchronize_session=False)
    )
    (
        db.query(MeetingAction)
        .filter(
            MeetingAction.meeting_id == meeting_id,
            MeetingAction.source == TRANSCRIPT_SOURCE,
        )
        .delete(synchronize_session=False)
    )
    for item in findings.decisions:
        db.add(
            MeetingDecision(
                meeting_id=meeting_id,
                text=item.text,
                owner=item.owner,
                start_seconds=item.start_seconds,
            )
        )
    for item in findings.actions:
        db.add(
            MeetingAction(
                meeting_id=meeting_id,
                description=item.description,
                assigned_to=item.assigned_to,
                deadline=item.deadline,
                source=TRANSCRIPT_SOURCE,
                start_seconds=item.start_seconds,
                status="OPEN",
            )
        )
    for item in findings.risks:
        db.add(
            MeetingRisk(
                meeting_id=meeting_id,
                description=item.description,
                impact=item.impact,
                owner=item.owner,
                mitigation=item.mitigation,
                status="OPEN",
                start_seconds=item.start_seconds,
            )
        )
