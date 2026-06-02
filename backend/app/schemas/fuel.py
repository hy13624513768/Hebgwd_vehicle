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
    workshop_id: int | None = Field(default=None, description="所属车间主数据 ID")
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
    workshop_id: int | None = None
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
    workshop_id: int | None = None
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


class FuelSyncRequest(BaseModel):
    date_from: date | None = Field(default=None, description="加油流水查询起始日期（含）")
    date_to: date | None = Field(default=None, description="加油流水查询截止日期（含）")


class FuelSyncResult(BaseModel):
    ok: bool
    balance_written: int = 0
    record_written: int = 0
    balance_matched: int = 0
    record_matched: int = 0
    date_from: str | None = None
    date_to: str | None = None
    error: str | None = None
