from fastapi import APIRouter, Depends

from app.core.lookups import MEETING_LOCATIONS
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ops import LookupItem

router = APIRouter(tags=["Lookups"])


@router.get(
    "/meeting-locations/",
    response_model=list[LookupItem],
)
def list_meeting_locations(current_user: User = Depends(get_current_user)):
    return MEETING_LOCATIONS
