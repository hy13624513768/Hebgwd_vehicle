import json
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _parse_str_list(v: list[str] | str | None) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except json.JSONDecodeError:
                pass
        return [line.strip() for line in s.replace("，", ",").split(",") if line.strip()]
    return []


class MaintenanceTermBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    code: str = Field(default="", max_length=32)
    aliases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True
    standard_hours: Decimal | None = Field(default=None, ge=0)
    reference_cost: Decimal | None = Field(default=None, ge=0)
    remarks: str | None = Field(default=None, max_length=2000)

    @field_validator("aliases", "keywords", mode="before")
    @classmethod
    def coerce_list(cls, v: list[str] | str | None) -> list[str]:
        return _parse_str_list(v)


class MaintenanceTermCreate(MaintenanceTermBase):
    parent_id: int | None = Field(default=None, description="一级大类 parent_id 为空；二级挂一级；三级挂二级")
    level: int = Field(ge=1, le=3)


class MaintenanceTermUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    code: str | None = Field(default=None, max_length=32)
    aliases: list[str] | None = None
    keywords: list[str] | None = None
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    standard_hours: Decimal | None = Field(default=None, ge=0)
    reference_cost: Decimal | None = Field(default=None, ge=0)
    remarks: str | None = Field(default=None, max_length=2000)
    parent_id: int | None = None

    @field_validator("aliases", "keywords", mode="before")
    @classmethod
    def coerce_list(cls, v: list[str] | str | None) -> list[str] | None:
        if v is None:
            return None
        return _parse_str_list(v)


class MaintenanceTermOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    level: int
    code: str
    name: str
    aliases: list[str]
    keywords: list[str]
    sort_order: int
    is_active: bool
    standard_hours: Decimal | None
    reference_cost: Decimal | None
    remarks: str | None


class MaintenanceTermTreeNode(MaintenanceTermOut):
    children: list["MaintenanceTermTreeNode"] = Field(default_factory=list)


class MaintenanceTermListOut(BaseModel):
    items: list[MaintenanceTermOut]
    total: int


class MaintenanceTermStatsOut(BaseModel):
    level1: int
    level2: int
    level3: int
    active_terms: int
    total: int


class MaintenanceTermTreeOut(BaseModel):
    items: list[MaintenanceTermTreeNode]
    stats: MaintenanceTermStatsOut


class MaintenanceTermSeedOut(BaseModel):
    ok: bool
    created: int
    skipped: bool
    message: str
