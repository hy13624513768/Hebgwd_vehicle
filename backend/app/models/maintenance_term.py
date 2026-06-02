from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MaintenanceTerm(Base):
    """维修词条树：一级大类 / 二级子类 / 三级词条（含别名与关键词，供结算单归类）。"""

    __tablename__ = "bus_maintenance_term"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("bus_maintenance_term.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 1=大类 2=子类 3=词条
    code: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aliases: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    keywords: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    standard_hours: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    reference_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped["MaintenanceTerm | None"] = relationship(
        "MaintenanceTerm",
        remote_side="MaintenanceTerm.id",
        back_populates="children",
    )
    children: Mapped[list["MaintenanceTerm"]] = relationship(
        "MaintenanceTerm",
        back_populates="parent",
        order_by="MaintenanceTerm.sort_order, MaintenanceTerm.id",
    )
