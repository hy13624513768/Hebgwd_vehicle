from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceCreate(BaseModel):
    vehicle_id: int = Field(ge=1)
    service_date: date
    category: str = Field(min_length=1, max_length=32)
    amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    mileage: int = Field(default=0, ge=0)
    vendor: str = Field(default="", max_length=128)
    description: str | None = None


class MaintenanceUpdate(BaseModel):
    vehicle_id: int | None = Field(default=None, ge=1)
    service_date: date | None = None
    category: str | None = Field(default=None, max_length=32)
    amount: Decimal | None = Field(default=None, ge=Decimal("0"))
    mileage: int | None = Field(default=None, ge=0)
    vendor: str | None = Field(default=None, max_length=128)
    description: str | None = None


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    service_date: date
    category: str
    amount: Decimal
    mileage: int
    vendor: str
    description: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime
