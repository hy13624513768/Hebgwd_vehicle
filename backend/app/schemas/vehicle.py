from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
    plate_number: str = Field(min_length=1, max_length=32)
    brand: str = Field(default="", max_length=64)
    model: str = Field(default="", max_length=64)
    vin: str | None = Field(default=None, max_length=64)
    color: str = Field(default="", max_length=32)
    seats: int = Field(default=5, ge=1, le=60)
    mileage: int = Field(default=0, ge=0)
    status: str = Field(default="active", max_length=16)
    remarks: str | None = None
    org_unit: str = Field(default="", max_length=128)
    vehicle_class: str = Field(default="", max_length=64)
    vehicle_type_label: str = Field(default="", max_length=64)
    emission_std: str = Field(default="", max_length=32)
    displacement: str = Field(default="", max_length=32)
    registered_at: datetime | None = None


class VehicleUpdate(BaseModel):
    plate_number: str | None = Field(default=None, min_length=1, max_length=32)
    brand: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=64)
    vin: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=32)
    seats: int | None = Field(default=None, ge=1, le=60)
    mileage: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=16)
    remarks: str | None = None
    org_unit: str | None = Field(default=None, max_length=128)
    vehicle_class: str | None = Field(default=None, max_length=64)
    vehicle_type_label: str | None = Field(default=None, max_length=64)
    emission_std: str | None = Field(default=None, max_length=32)
    displacement: str | None = Field(default=None, max_length=32)
    registered_at: datetime | None = None


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plate_number: str
    brand: str
    model: str
    vin: str | None
    color: str
    seats: int
    mileage: int
    status: str
    remarks: str | None
    org_unit: str = ""
    vehicle_class: str = ""
    vehicle_type_label: str = ""
    history_plate: str = ""
    engine_no: str = ""
    emission_std: str = ""
    displacement: str = ""
    purchase_amount: Decimal | None = None
    registered_at: datetime | None = None
    created_by: int | None
    created_at: datetime
    updated_at: datetime
