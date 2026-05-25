from __future__ import annotations

from pydantic import BaseModel, Field


class RoleDefinitionOut(BaseModel):
    code: str
    label: str
    rank: int
    description: str = ""


class UserAdminOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    workshop_id: int | None = None

    model_config = {"from_attributes": True}


class UserAdminCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=32)
    workshop_id: int | None = Field(default=None, description="车间管理员/主任须绑定车间")
    is_active: bool = True


class UserAdminUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, min_length=1, max_length=32)
    workshop_id: int | None = Field(default=None, description="所属车间；段级/超管可留空")
    is_active: bool | None = None


class UserAdminListOut(BaseModel):
    items: list[UserAdminOut]
    total: int
