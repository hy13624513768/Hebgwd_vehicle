from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FuelCardCreate(BaseModel):
    card_no: str = Field(min_length=1, max_length=64)
    col_c: str = Field(default="", max_length=256)
    col_d: str = Field(default="", max_length=256)


class FuelCardUpdate(BaseModel):
    col_c: str | None = Field(default=None, max_length=256)
    col_d: str | None = Field(default=None, max_length=256)


class FuelCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_no: str
    col_c: str
    col_d: str
    created_at: datetime
    updated_at: datetime


class FuelRecordCreate(BaseModel):
    card_asn: str = Field(default="", max_length=64)
    car_no: str = Field(default="", max_length=64)
    occur_time: datetime
    volumn: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0"))
    amount: Decimal = Field(ge=Decimal("0"))
    balance: Decimal = Field(default=Decimal("0.00"))
    workshop: str = Field(default="", max_length=128)
    org_name: str = Field(default="", max_length=128)
    gift_name: str = Field(default="", max_length=128)


class FuelRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_asn: str
    car_no: str
    occur_time: datetime
    volumn: Decimal
    amount: Decimal
    balance: Decimal
    workshop: str
    org_name: str
    gift_name: str
    created_at: datetime
    updated_at: datetime


class FuelRecordPage(BaseModel):
    """加油流水分页（列表接口）。"""

    items: list[FuelRecordOut]
    total: int


class FuelBalanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_no: str
    workshop: str
    vehicle_no: str
    amount: Decimal
    reserve_fund: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime


class FuelBalancePage(BaseModel):
    """油卡余额分页（列表接口）。"""

    items: list[FuelBalanceOut]
    total: int
    total_amount: Decimal
    count_zero: int
    count_low: int
    count_high: int
    sum_zero: Decimal
    sum_low: Decimal
    sum_high: Decimal
