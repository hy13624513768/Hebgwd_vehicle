from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.roles import (
    LEGACY_DRIVER,
    LEGACY_STAFF,
    VEHICLE_DRIVER,
    is_fleet_management,
)
from app.models.driver import Driver
from app.models.trip_request import TripRequest
from app.models.user import User
from app.schemas.trip_request import TripRequestUpdate


def driver_id_for_user(db: Session, user_id: int) -> int | None:
    return db.scalar(select(Driver.id).where(Driver.user_id == user_id))


def _is_driver_channel(role: str) -> bool:
    return role in (VEHICLE_DRIVER, LEGACY_DRIVER)


def trips_query_filtered(db: Session, user: User):
    stmt = select(TripRequest)
    if is_fleet_management(user.role):
        return stmt
    if user.role in (LEGACY_STAFF, "staff"):
        return stmt.where(TripRequest.created_by == user.id)
    if _is_driver_channel(user.role):
        did = driver_id_for_user(db, user.id)
        if did:
            return stmt.where(or_(TripRequest.driver_id == did, TripRequest.created_by == user.id))
        return stmt.where(TripRequest.created_by == user.id)
    return stmt.where(TripRequest.id == -1)


def assert_trip_visible(db: Session, user: User, row: TripRequest) -> None:
    if is_fleet_management(user.role):
        return
    if user.role in (LEGACY_STAFF, "staff"):
        if row.created_by != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用车申请不存在")
        return
    if _is_driver_channel(user.role):
        if row.created_by == user.id:
            return
        did = driver_id_for_user(db, user.id)
        if did and row.driver_id == did:
            return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用车申请不存在")
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用车申请不存在")


def normalize_trip_update(
    db: Session, user: User, row: TripRequest, body: TripRequestUpdate
) -> dict:
    """按角色裁剪 PATCH 字段，返回可写入的 dict。"""
    raw = body.model_dump(exclude_unset=True)
    if is_fleet_management(user.role):
        return raw

    if user.role in (LEGACY_STAFF, "staff"):
        if row.created_by != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该申请")
        if row.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅待审批状态可由申请人修改")
        blocked = {"status", "vehicle_id", "driver_id"} & raw.keys()
        if blocked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="普通用户不可修改状态/派车信息")
        allowed = {"purpose", "applicant_name", "start_at", "end_at", "origin", "destination", "passenger_count", "notes"}
        return {k: v for k, v in raw.items() if k in allowed}

    if _is_driver_channel(user.role):
        did = driver_id_for_user(db, user.id)
        if not did or row.driver_id != did:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅指派给本人的任务可办理")
        allowed_keys = {"status", "notes"}
        extra = set(raw.keys()) - allowed_keys
        if extra:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="驾驶员仅可更新状态与备注")
        if "status" in raw:
            st = str(raw["status"]).strip()
            if st not in {"in_progress", "completed", "cancelled"}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="驾驶员仅可将状态改为执行中/已完成/已取消")
        return raw

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该申请")
