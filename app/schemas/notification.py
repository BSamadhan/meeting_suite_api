from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: int
    kind: str
    message: str
    meeting_id: int | None = None
    action_id: int | None = None
    href: str

    model_config = ConfigDict(from_attributes=True)
