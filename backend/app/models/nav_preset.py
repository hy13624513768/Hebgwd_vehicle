from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NavPreset(Base):
    """段内导航预设点（GCJ-02），全系统共享。"""

    __tablename__ = "bus_nav_preset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True, default=0)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
