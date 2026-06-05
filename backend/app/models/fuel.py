from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FuelCard(Base):
    """油卡档案"""

    __tablename__ = "bus_fuel_card"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    col_c: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    col_d: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelRecord(Base):
    """加油流水（对接新结构字段）"""

    __tablename__ = "bus_fuel_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_asn: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    org_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    occur_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gift_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    volumn: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    workshop: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    workshop_id: Mapped[int | None] = mapped_column(
        ForeignKey("bus_workshop.id"), nullable=True, index=True
    )
    car_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelBalance(Base):
    """油卡余额快照（来自 Excel《卡内剩余金额》Sheet1）。"""

    __tablename__ = "bus_fuel_balance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    workshop: Mapped[str] = mapped_column(String(128), default="", nullable=False)  # 车间
    workshop_id: Mapped[int | None] = mapped_column(
        ForeignKey("bus_workshop.id"), nullable=True, index=True
    )
    vehicle_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 车号
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    reserve_fund: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelSyncLog(Base):
    """油卡余额从中国石油平台同步的记录（用于统计今日刷新次数与上次刷新时间）。"""

    __tablename__ = "bus_fuel_sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), nullable=True, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
