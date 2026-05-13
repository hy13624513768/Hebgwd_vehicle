from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Driver(Base):
    """驾驶员档案（与《驾驶员数据库表》Excel 列一致）"""

    __tablename__ = "bus_driver"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sort_no: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    license_type: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # 准驾
    vehicle_type_label: Mapped[str] = mapped_column(
        String(64), default="", nullable=False
    )  # 车辆类型标签（与车辆主数据字段名一致，便于对账）
    status: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)  # 状态
    id_card: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)  # 身份证号
    health_check_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    outsourcing_onboarding: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), nullable=True, unique=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("sys_user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
