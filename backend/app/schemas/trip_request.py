from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.patch import PatchModel
from app.core.datetime_utils import as_utc


class TripRequestCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    purpose: str = Field(min_length=1, max_length=500)
    applicant_name: str = Field(min_length=1, max_length=64)
    start_at: datetime
    end_at: datetime
    origin: str = Field(min_length=1, max_length=256)
    destination: str = Field(min_length=1, max_length=256)
    passenger_count: int = Field(default=1, ge=1, le=99)
    vehicle_id: int | None = None
    driver_id: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def check_time_order(self):
        self.start_at = as_utc(self.start_at)
        self.end_at = as_utc(self.end_at)
        if self.end_at <= self.start_at:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class TripRequestUpdate(PatchModel):
    nullable_fields = {"vehicle_id", "driver_id", "notes"}
    purpose: str | None = Field(default=None, min_length=1, max_length=500)
    applicant_name: str | None = Field(default=None, min_length=1, max_length=64)
    start_at: datetime | None = None
    end_at: datetime | None = None
    origin: str | None = Field(default=None, min_length=1, max_length=256)
    destination: str | None = Field(default=None, min_length=1, max_length=256)
    passenger_count: int | None = Field(default=None, ge=1, le=99)
    status: str | None = Field(default=None, max_length=16)
    vehicle_id: int | None = None
    driver_id: int | None = None
    notes: str | None = None


class TripRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purpose: str
    applicant_name: str
    start_at: datetime
    end_at: datetime
    origin: str
    destination: str
    passenger_count: int
    status: str
    vehicle_id: int | None
    driver_id: int | None
    notes: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime
