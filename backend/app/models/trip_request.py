from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TripRequest(Base):
    """用车申请 / 调度单"""

    __tablename__ = "trip_requests"
    __table_args__ = (
        Index("ix_trip_requests_workshop_status_id", "workshop_id", "status", "id"),
        Index("ix_trip_requests_created_by_status", "created_by", "status"),
        Index("ix_trip_requests_driver_id", "driver_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    applicant_name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(256), nullable=False)
    destination: Mapped[str] = mapped_column(String(256), nullable=False)
    passenger_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )  # pending/approved/rejected/in_progress/completed/cancelled

    workshop_id: Mapped[int | None] = mapped_column(
        ForeignKey("workshops.id"), nullable=True, index=True
    )
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
