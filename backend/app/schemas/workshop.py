from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkshopCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str = Field(default="", max_length=32)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True
    remarks: str | None = None


class WorkshopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    remarks: str | None = None


class WorkshopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    sort_order: int
    is_active: bool
    remarks: str | None
    created_at: datetime
    updated_at: datetime


class WorkshopListOut(BaseModel):
    items: list[WorkshopOut]
    total: int
