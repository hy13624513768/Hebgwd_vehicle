from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

NavPresetOpAction = Literal["create", "delete", "unlock_drag", "lock_drag", "save"]


class NavPresetOpLogCreate(BaseModel):
    action: NavPresetOpAction
    marker_name: str = Field(min_length=1, max_length=256)
    marker_lng: float | None = Field(default=None, ge=-180, le=180)
    marker_lat: float | None = Field(default=None, ge=-90, le=90)
    detail: str = Field(default="", max_length=2000)


class NavPresetOpLogOut(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: str
    role: str
    action: str
    marker_name: str
    marker_lng: float | None
    marker_lat: float | None
    detail: str
    created_at: datetime

    model_config = {"from_attributes": True}
