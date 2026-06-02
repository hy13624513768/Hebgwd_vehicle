from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RepairSettlementLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    line_no: int
    item_name: str
    part_name: str
    quantity: Decimal
    unit: str
    labor_fee: Decimal
    part_fee: Decimal
    amount: Decimal
    raw_text: str
    term_id: int | None
    term_name: str
    category_l1: str
    category_l2: str
    match_score: int
    match_method: str


class RepairSettlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repair_record_id: int
    order_no: str
    plate_number: str
    vehicle_model: str
    owner: str
    shop_name: str
    service_date: date | None
    mileage_in: int
    total_amount: Decimal
    recognition_status: str
    recognition_error: str | None
    lines: list[RepairSettlementLineOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RepairRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    driver_id: int | None
    repair_order_no: str
    photo_duo_path: str | None
    photo_item_path: str | None
    photo_item_video_path: str | None
    photo_settlement_path: str | None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    plate_number: str = ""
    driver_name: str = ""
    settlement: RepairSettlementOut | None = None


class RepairRecordListOut(BaseModel):
    items: list[RepairRecordOut]
    total: int


class SettlementSummaryOut(BaseModel):
    id: int
    repair_record_id: int
    vehicle_id: int
    plate_number: str
    order_no: str
    service_date: date | None
    total_amount: Decimal
    mileage_in: int
    shop_name: str
    recognition_status: str
    line_count: int
    category_summary: dict[str, Decimal] = Field(default_factory=dict)
    created_at: datetime


class SettlementSummaryListOut(BaseModel):
    items: list[SettlementSummaryOut]
    total: int
    category_totals: dict[str, Decimal] = Field(default_factory=dict)


class RecognizeOut(BaseModel):
    ok: bool
    settlement_id: int | None = None
    message: str = ""
