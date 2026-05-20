from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NavPresetOpLog(Base):
    """段内导航标记点操作审计（不含地图拖动过程）。"""

    __tablename__ = "bus_nav_preset_op_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    marker_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    marker_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    marker_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
