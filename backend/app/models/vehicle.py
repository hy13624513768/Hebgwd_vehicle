from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Vehicle(Base):
    """车辆档案"""

    __tablename__ = "bus_vehicle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plate_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    brand: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    seats: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    mileage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active/inactive/repairing
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    org_unit: Mapped[str] = mapped_column(String(128), default="", nullable=False)  # 使用单位（与车间主表 name 同步）
    workshop_id: Mapped[int | None] = mapped_column(
        ForeignKey("bus_workshop.id"), nullable=True, index=True
    )
    vehicle_class: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 种类
    vehicle_type_label: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 车辆类型（Excel）
    history_plate: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    engine_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    emission_std: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    displacement: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    purchase_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
