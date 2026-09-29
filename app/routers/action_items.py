from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ops import ActionItemResponse, ActionItemStatusUpdate
from app.services.action_items import list_action_items, update_action_item_status

router = APIRouter(tags=["Action items"])


@router.get("/action-items/", response_model=list[ActionItemResponse])
def get_action_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_action_items(db, current_user.id)


@router.put("/action-items/{action_id}/", response_model=ActionItemResponse)
def put_action_item_status(
    action_id: int,
    payload: ActionItemStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_action_item_status(db, current_user.id, action_id, payload.status)
