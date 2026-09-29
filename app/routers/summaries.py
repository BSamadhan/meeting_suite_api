from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.finding import DecisionResponse, RiskResponse
from app.schemas.summary import SummaryResponse
from app.services.summaries import (
    analyze_meeting,
    latest_summary,
    list_decisions,
    list_risks,
)

router = APIRouter(tags=["Summary"])


@router.post(
    "/{meeting_id}/ai/analyze",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/{meeting_id}/ai/analyze/",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def post_meeting_analysis(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return analyze_meeting(db, meeting_id)


@router.get(
    "/{meeting_id}/summary",
    response_model=SummaryResponse,
)
@router.get(
    "/{meeting_id}/summary/",
    response_model=SummaryResponse,
    include_in_schema=False,
)
def get_meeting_summary(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = latest_summary(db, meeting_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found",
        )
    return summary


@router.get(
    "/{meeting_id}/decisions",
    response_model=list[DecisionResponse],
)
@router.get(
    "/{meeting_id}/decisions/",
    response_model=list[DecisionResponse],
    include_in_schema=False,
)
def get_meeting_decisions(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_decisions(db, meeting_id)


@router.get(
    "/{meeting_id}/risks",
    response_model=list[RiskResponse],
)
@router.get(
    "/{meeting_id}/risks/",
    response_model=list[RiskResponse],
    include_in_schema=False,
)
def get_meeting_risks(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_risks(db, meeting_id)
