from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ops import CaptureActionCreate, CaptureActionResponse
from app.services.actions import create_action, list_actions

router = APIRouter(tags=["Capture actions"])


@router.get(
    "/capture-actions/",
    response_model=list[CaptureActionResponse],
)
def get_capture_actions(
    meeting_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_actions(db, meeting_id)


@router.post(
    "/capture-actions/",
    response_model=CaptureActionResponse,
    status_code=201,
)
def post_capture_action(
    payload: CaptureActionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_action(db, payload, current_user)
