from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RepairRecord(Base):
    """驾驶员维修上报（含结算单照片，识别后流转至维修保养）。"""

    __tablename__ = "bus_repair_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("bus_vehicle.id"), nullable=False, index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("bus_driver.id"), nullable=True, index=True)
    repair_order_no: Mapped[str] = mapped_column(String(128), default="", nullable=False, index=True)

    photo_duo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_item_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_item_video_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_settlement_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("sys_user.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    settlement: Mapped["RepairSettlement | None"] = relationship(
        "RepairSettlement",
        back_populates="repair_record",
        uselist=False,
    )


class RepairSettlement(Base):
    """结算单 AI 识别结果（与维修上报一对一）。"""

    __tablename__ = "bus_repair_settlement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repair_record_id: Mapped[int] = mapped_column(
        ForeignKey("bus_repair_record.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    order_no: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    plate_number: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    owner: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    shop_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    mileage_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    recognition_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    recognition_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    repair_record: Mapped[RepairRecord] = relationship("RepairRecord", back_populates="settlement")
    lines: Mapped[list["RepairSettlementLine"]] = relationship(
        "RepairSettlementLine",
        back_populates="settlement",
        order_by="RepairSettlementLine.line_no",
        cascade="all, delete-orphan",
    )


class RepairSettlementLine(Base):
    """结算单明细行 + 维修词条归类。"""

    __tablename__ = "bus_repair_settlement_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("bus_repair_settlement.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_name: Mapped[str] = mapped_column(String(256), nullable=False)
    part_name: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1"), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    labor_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    part_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    term_id: Mapped[int | None] = mapped_column(ForeignKey("bus_maintenance_term.id"), nullable=True, index=True)
    term_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    category_l1: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    category_l2: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    match_method: Mapped[str] = mapped_column(String(32), default="unmatched", nullable=False)

    settlement: Mapped[RepairSettlement] = relationship("RepairSettlement", back_populates="lines")
