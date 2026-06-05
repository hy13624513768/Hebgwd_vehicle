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


class DriverAccountItem(BaseModel):
    """单个驾驶员的处理结果（用于前端逐条展示/排查）。"""

    driver_id: int
    name: str = ""
    username: str | None = None
    status: str  # created / skipped / failed
    reason: str = ""


class DriverAccountBatchResult(BaseModel):
    """从 bus_driver 批量生成驾驶员账号的汇总结果。"""

    created: int = 0
    skipped: int = 0
    failed: int = 0
    details: list[DriverAccountItem] = []
