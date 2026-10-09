from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FuelCard(Base):
    """油卡档案"""

    __tablename__ = "fuel_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    col_c: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    col_d: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelCardLookup(Base):
    """油卡号与车间、车辆的映射；结构与线上开发库保持一致。"""

    __tablename__ = "fuel_card_lookups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    workshop: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    vehicle_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelRecord(Base):
    """加油流水（对接新结构字段）"""

    __tablename__ = "fuel_records"
    __table_args__ = (
        Index("ix_fuel_records_occur_time", "occur_time"),
        Index("ix_fuel_records_workshop_occur_time", "workshop_id", "occur_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_record_id: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True)
    platform_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    volume_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    balance_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    card_asn: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    org_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    occur_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gift_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    volumn: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    workshop: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    workshop_id: Mapped[int | None] = mapped_column(
        ForeignKey("workshops.id"), nullable=True, index=True
    )
    car_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelEntry(Base):
    """移动端人工登记的加油凭证；与第三方平台同步流水分表保存。"""

    __tablename__ = "fuel_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False, index=True)
    odometer: Mapped[int] = mapped_column(Integer, nullable=False)
    fueled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    photo_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FuelBalance(Base):
    """油卡余额快照（来自 Excel《卡内剩余金额》Sheet1）。"""

    __tablename__ = "fuel_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    workshop: Mapped[str] = mapped_column(String(128), default="", nullable=False)  # 车间
    workshop_id: Mapped[int | None] = mapped_column(
        ForeignKey("workshops.id"), nullable=True, index=True
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

    __tablename__ = "fuel_sync_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
