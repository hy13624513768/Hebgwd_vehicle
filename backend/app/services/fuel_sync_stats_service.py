"""油卡同步刷新统计。"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fuel import FuelBalance, FuelSyncLog

SHANGHAI = ZoneInfo("Asia/Shanghai")


def _today_start_shanghai() -> datetime:
    now = datetime.now(SHANGHAI)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(SHANGHAI)


def record_fuel_sync_log(user_id: int | None, *, success: bool = True) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.add(FuelSyncLog(user_id=user_id, success=success))
        db.commit()
    finally:
        db.close()


def get_fuel_sync_stats(db: Session) -> dict[str, object]:
    today_start = _today_start_shanghai()
    today_count = int(
        db.scalar(
            select(func.count())
            .select_from(FuelSyncLog)
            .where(FuelSyncLog.success.is_(True), FuelSyncLog.synced_at >= today_start)
        )
        or 0
    )
    last_from_log = db.scalar(
        select(func.max(FuelSyncLog.synced_at)).where(FuelSyncLog.success.is_(True))
    )
    last_from_balance = db.scalar(select(func.max(FuelBalance.updated_at)))
    last_synced_at = last_from_log
    if last_from_balance is not None:
        if last_synced_at is None or last_from_balance > last_synced_at:
            last_synced_at = last_from_balance
    return {"today_count": today_count, "last_synced_at": last_synced_at}
