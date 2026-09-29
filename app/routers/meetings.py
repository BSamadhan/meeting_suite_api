# Meeting routes (CRUD, lifecycle, availability)
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.lookups import MEETING_CATEGORIES, REPEAT_TYPES
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreate,
    MeetingHistoryItem,
    MeetingListResponse,
    MeetingResponse,
    MeetingUpdate,
)
from app.schemas.ops import (
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    LookupItem,
)
from app.services.availability import check_availability
from app.services.meetings import cancel_meeting as cancel_meeting_record
from app.services.meetings import create_meeting as create_meeting_record
from app.services.meetings import end_meeting as end_meeting_record
from app.services.meetings import get_meeting as get_meeting_record
from app.services.meetings import list_completed_history
from app.services.meetings import list_meetings as list_meeting_records
from app.services.meetings import start_meeting as start_meeting_record
from app.services.meetings import update_meeting as update_meeting_record

router = APIRouter()


@router.post(
    "/",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_meeting(
    meeting_data: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_meeting_record(db, meeting_data, current_user)


@router.get(
    "/",
    response_model=MeetingListResponse,
)
@router.get(
    "",
    response_model=MeetingListResponse,
    include_in_schema=False,
)
def get_all_meetings(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(default=None),
    meeting_status: str | None = Query(default=None, alias="status"),
    meeting_date: date | None = Query(default=None),
    period: str | None = Query(default=None),
    meeting_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = list_meeting_records(
        db,
        current_user.id,
        page=page,
        page_size=page_size,
        search=search,
        meeting_status=meeting_status,
        meeting_date=meeting_date,
        period=period,
        meeting_type=meeting_type,
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return MeetingListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.post(
    "/check-availability/",
    response_model=AvailabilityCheckResponse,
)
def check_meeting_availability(
    payload: AvailabilityCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return check_availability(db, payload, current_user=current_user)


@router.get(
    "/repeat-types/",
    response_model=list[LookupItem],
)
def list_repeat_types(current_user: User = Depends(get_current_user)):
    return REPEAT_TYPES


@router.get(
    "/categories/",
    response_model=list[LookupItem],
)
def list_meeting_categories(current_user: User = Depends(get_current_user)):
    return MEETING_CATEGORIES


@router.post(
    "/start/{meeting_id}/",
    response_model=MeetingResponse,
)
def start_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return start_meeting_record(db, meeting_id)


@router.post(
    "/end/{meeting_id}/",
    response_model=MeetingResponse,
)
def end_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return end_meeting_record(db, meeting_id)


@router.post(
    "/cancel/{meeting_id}/",
    response_model=MeetingResponse,
)
def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return cancel_meeting_record(db, meeting_id)


@router.get(
    "/history/",
    response_model=list[MeetingHistoryItem],
)
def get_meeting_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_completed_history(db, current_user.id)


@router.get(
    "/{meeting_id}/",
    response_model=MeetingResponse,
)
@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
    include_in_schema=False,
)
def get_meeting_by_id(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_record(db, meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return meeting


@router.put(
    "/{meeting_id}/",
    response_model=MeetingResponse,
)
@router.put(
    "/{meeting_id}",
    response_model=MeetingResponse,
    include_in_schema=False,
)
def update_meeting(
    meeting_id: int,
    meeting_data: MeetingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = get_meeting_record(db, meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    return update_meeting_record(db, meeting, meeting_data, current_user)


@router.delete(
    "/{meeting_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
)
@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found",
        )
    db.delete(meeting)
    db.commit()
    return None
