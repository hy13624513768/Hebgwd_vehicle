import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PHONE_RE = re.compile(r"^\d{11}$")
_ID_CARD_RE = re.compile(r"^\d{17}[\dX]$", re.IGNORECASE)


def _normalize_phone(value: str) -> str:
    phone = value.strip()
    if not _PHONE_RE.match(phone):
        raise ValueError("手机号须为11位数字")
    return phone


def _normalize_id_card(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    upper = raw.upper()
    if not _ID_CARD_RE.match(upper):
        raise ValueError("身份证号须为18位（末位可为X）")
    return upper


class DriverCreate(BaseModel):
    sort_no: int | None = Field(default=None, ge=0)
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=11, max_length=11)
    license_type: str = Field(default="", max_length=32)
    vehicle_type_label: str = Field(default="", max_length=64)
    status: str = Field(default="", max_length=64)
    id_card: str | None = Field(default=None, max_length=18)
    health_check_report: str | None = None
    outsourcing_onboarding: str | None = None
    first_hire_date: date | None = None
    workshop_id: int | None = Field(default=None, description="所属车间主数据 ID")
    user_id: int | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return _normalize_phone(value)

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, value: str | None) -> str | None:
        return _normalize_id_card(value)


class DriverUpdate(BaseModel):
    sort_no: int | None = Field(default=None, ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, min_length=11, max_length=11)
    license_type: str | None = Field(default=None, max_length=32)
    vehicle_type_label: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=64)
    id_card: str | None = Field(default=None, max_length=18)
    health_check_report: str | None = None
    outsourcing_onboarding: str | None = None
    first_hire_date: date | None = None
    workshop_id: int | None = Field(default=None, description="所属车间主数据 ID")
    user_id: int | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_phone(value)

    @field_validator("id_card")
    @classmethod
    def validate_id_card(cls, value: str | None) -> str | None:
        return _normalize_id_card(value)


class DriverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sort_no: int | None
    name: str
    phone: str
    license_type: str
    vehicle_type_label: str
    status: str
    id_card: str | None
    health_check_report: str | None
    outsourcing_onboarding: str | None
    first_hire_date: date | None
    workshop_id: int | None = None
    workshop_name: str | None = None
    user_id: int | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class DriverListOut(BaseModel):
    items: list[DriverOut]
    total: int


class DriverFiltersOut(BaseModel):
    workshops: list[str]
    license_types: list[str]


class DriverStatsOut(BaseModel):
    total: int
    by_workshop: dict[str, int]
    by_license_type: dict[str, int]
    by_employment_status: dict[str, int] = Field(
        default_factory=dict,
        description="人员状态统计，键为本单位、外包",
    )
