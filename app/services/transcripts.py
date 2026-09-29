from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.meeting_transcript import MeetingTranscriptSegment
from app.schemas.transcript import TranscriptReplace, TranscriptSegmentIn
from app.services.meetings import get_meeting_or_404
from app.services.stt.types import SpeechSegment

NOTES_SPEAKER = "Notes"


def list_transcript(db: Session, meeting_id: int) -> list[MeetingTranscriptSegment]:
    get_meeting_or_404(db, meeting_id)
    return (
        db.query(MeetingTranscriptSegment)
        .filter(MeetingTranscriptSegment.meeting_id == meeting_id)
        .order_by(
            MeetingTranscriptSegment.sequence.asc(),
            MeetingTranscriptSegment.id.asc(),
        )
        .all()
    )


def replace_transcript(
    db: Session,
    meeting_id: int,
    payload: TranscriptReplace,
) -> list[MeetingTranscriptSegment]:
    get_meeting_or_404(db, meeting_id)
    (
        db.query(MeetingTranscriptSegment)
        .filter(MeetingTranscriptSegment.meeting_id == meeting_id)
        .delete(synchronize_session=False)
    )
    rows = [
        _new_segment(meeting_id, index, segment)
        for index, segment in enumerate(payload.segments, start=1)
    ]
    db.add_all(rows)
    db.commit()
    return list_transcript(db, meeting_id)


def replace_speech_segments(
    db: Session,
    meeting_id: int,
    segments: list[SpeechSegment],
) -> None:
    """Replace spoken lines and keep typed notes. The caller commits."""
    get_meeting_or_404(db, meeting_id)
    (
        db.query(MeetingTranscriptSegment)
        .filter(
            MeetingTranscriptSegment.meeting_id == meeting_id,
            MeetingTranscriptSegment.speaker != NOTES_SPEAKER,
        )
        .delete(synchronize_session=False)
    )
    current_max = (
        db.query(MeetingTranscriptSegment.sequence)
        .filter(MeetingTranscriptSegment.meeting_id == meeting_id)
        .order_by(MeetingTranscriptSegment.sequence.desc())
        .limit(1)
        .scalar()
    )
    sequence = int(current_max or 0)
    rows: list[MeetingTranscriptSegment] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        start_seconds = segment.start_seconds
        end_seconds = segment.end_seconds
        if (
            start_seconds is not None
            and end_seconds is not None
            and end_seconds < start_seconds
        ):
            end_seconds = start_seconds
        sequence += 1
        rows.append(
            MeetingTranscriptSegment(
                meeting_id=meeting_id,
                sequence=sequence,
                speaker=(segment.speaker or "Speaker").strip() or "Speaker",
                text=text,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                confidence=segment.confidence,
            )
        )
    db.add_all(rows)


def add_note(
    db: Session,
    meeting_id: int,
    text: str,
) -> MeetingTranscriptSegment:
    get_meeting_or_404(db, meeting_id)
    current_max = (
        db.query(MeetingTranscriptSegment.sequence)
        .filter(MeetingTranscriptSegment.meeting_id == meeting_id)
        .order_by(MeetingTranscriptSegment.sequence.desc())
        .limit(1)
        .scalar()
    )
    row = MeetingTranscriptSegment(
        meeting_id=meeting_id,
        sequence=int(current_max or 0) + 1,
        speaker=NOTES_SPEAKER,
        text=text.strip(),
        start_seconds=None,
        end_seconds=None,
        confidence=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _new_segment(
    meeting_id: int,
    sequence: int,
    segment: TranscriptSegmentIn,
) -> MeetingTranscriptSegment:
    if not segment.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcript text is required.",
        )
    return MeetingTranscriptSegment(
        meeting_id=meeting_id,
        sequence=sequence,
        speaker=segment.speaker.strip(),
        text=segment.text.strip(),
        start_seconds=segment.start_seconds,
        end_seconds=segment.end_seconds,
        confidence=segment.confidence,
    )
