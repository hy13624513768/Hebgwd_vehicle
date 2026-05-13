from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DriverCreate(BaseModel):
    sort_no: int | None = Field(default=None, ge=0)
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=3, max_length=32)
    license_type: str = Field(default="", max_length=32)
    vehicle_type_label: str = Field(default="", max_length=64)
    status: str = Field(default="", max_length=64)
    id_card: str | None = Field(default=None, max_length=32)
    health_check_report: str | None = None
    outsourcing_onboarding: str | None = None
    first_hire_date: date | None = None
    user_id: int | None = None


class DriverUpdate(BaseModel):
    sort_no: int | None = Field(default=None, ge=0)
    name: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, min_length=3, max_length=32)
    license_type: str | None = Field(default=None, max_length=32)
    vehicle_type_label: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=64)
    id_card: str | None = Field(default=None, max_length=32)
    health_check_report: str | None = None
    outsourcing_onboarding: str | None = None
    first_hire_date: date | None = None
    user_id: int | None = None


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
    user_id: int | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class DriverListOut(BaseModel):
    items: list[DriverOut]
    total: int


class DriverFiltersOut(BaseModel):
    statuses: list[str]
    license_types: list[str]


class DriverStatsOut(BaseModel):
    total: int
    by_status: dict[str, int]
    by_license_type: dict[str, int]
    by_vehicle_type_label: dict[str, int]
