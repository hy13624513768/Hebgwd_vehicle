"""用车状态和派车约束，供 API 与后续调度模块共用。"""

from fastapi import HTTPException
from sqlalchemy import or_, select
from app.core.roles import is_fleet_management

from app.core.datetime_utils import as_utc
from app.core.data_scope import require_vehicle_access, require_workshop_access
from app.models.driver import Driver
from app.models.trip_request import TripRequest
from app.models.vehicle import Vehicle

TRANSITIONS = {
    "pending": {"approved", "rejected", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "rejected": set(),
    "cancelled": set(),
}
RESERVED = {"approved", "in_progress"}


def validate_trip(db, user, row, previous_status=None):
    row.start_at = as_utc(row.start_at)
    row.end_at = as_utc(row.end_at)
    if row.end_at <= row.start_at:
        raise HTTPException(400, "结束时间必须晚于开始时间")
    if row.status not in TRANSITIONS:
        raise HTTPException(400, "状态值不合法")
    if previous_status and row.status != previous_status:
        if row.status not in TRANSITIONS.get(previous_status, set()):
            raise HTTPException(409, "当前状态不允许此操作，请刷新后重试")
    if row.vehicle_id:
        vehicle = require_vehicle_access(db, user, row.vehicle_id)
        row.workshop_id = vehicle.workshop_id
    else:
        vehicle = None
        row.workshop_id = row.workshop_id or user.workshop_id
    if row.driver_id:
        driver = db.get(Driver, row.driver_id)
        if not driver:
            raise HTTPException(400, "驾驶员不存在")
        require_workshop_access(user, driver.workshop_id)
    if not is_fleet_management(user.role) and previous_status == "pending" and row.status != "pending":
        raise HTTPException(403, "申请尚未批准，不能开始执行")
    if row.status not in RESERVED:
        return
    if not vehicle or not row.driver_id:
        raise HTTPException(400, "批准或执行前请分配车辆和驾驶员")
    # PostgreSQL 锁住共同资源，避免两个并发审批同时通过冲突检查。
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == row.vehicle_id).with_for_update().execution_options(populate_existing=True))
    if vehicle.status != "active":
        raise HTTPException(409, "该车辆当前不可派出")
    db.execute(select(Driver).where(Driver.id == row.driver_id).with_for_update())
    conflict = db.scalar(select(TripRequest.id).where(
        TripRequest.id != (row.id or -1),
        TripRequest.status.in_(RESERVED),
        TripRequest.start_at < row.end_at,
        TripRequest.end_at > row.start_at,
        or_(TripRequest.vehicle_id == row.vehicle_id, TripRequest.driver_id == row.driver_id),
    ).limit(1))
    if conflict:
        raise HTTPException(409, "所选车辆或驾驶员在该时段已有任务")
