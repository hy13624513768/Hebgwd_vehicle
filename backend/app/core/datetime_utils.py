"""数据库和接口统一使用 UTC；SQLite 返回的无时区时间按 UTC 解释。"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def shanghai_day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=ZoneInfo("Asia/Shanghai")).astimezone(timezone.utc)
