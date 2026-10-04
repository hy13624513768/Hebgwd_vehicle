from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.core.roles import is_fleet_management
from app.services.trip_service import validate_trip
from app.models.trip_request import TripRequest
from app.schemas.trip_request import TripRequestCreate, TripRequestOut, TripRequestUpdate
from app.services.trip_acl import assert_trip_visible, normalize_trip_update, trips_query_filtered

router = APIRouter(prefix="/trip-requests", tags=["trip-requests"])

ALLOWED_STATUS = {
    "pending",
    "approved",
    "rejected",
    "in_progress",
    "completed",
    "cancelled",
}


@router.get("", response_model=list[TripRequestOut])
def list_trip_requests(
    db: DbSession,
    current: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    q: Annotated[str | None, Query(max_length=64)] = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=16)] = None,
) -> list[TripRequest]:
    stmt = trips_query_filtered(db, current).order_by(TripRequest.id.desc()).offset(skip).limit(limit)
    if status_filter:
        stmt = stmt.where(TripRequest.status == status_filter.strip())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                TripRequest.purpose.ilike(like),
                TripRequest.applicant_name.ilike(like),
                TripRequest.origin.ilike(like),
                TripRequest.destination.ilike(like),
            )
        )
    return list(db.scalars(stmt).all())


@router.post("", response_model=TripRequestOut, status_code=status.HTTP_201_CREATED)
def create_trip_request(db: DbSession, current: CurrentUser, body: TripRequestCreate) -> TripRequest:
    if not is_fleet_management(current.role) and (body.vehicle_id or body.driver_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="普通用户提交申请时不可指定车辆或驾驶员")
    row = TripRequest(
        purpose=body.purpose.strip(),
        applicant_name=body.applicant_name.strip(),
        start_at=body.start_at,
        end_at=body.end_at,
        origin=body.origin.strip(),
        destination=body.destination.strip(),
        passenger_count=body.passenger_count,
        status="pending",
        vehicle_id=body.vehicle_id,
        driver_id=body.driver_id,
        notes=body.notes,
        created_by=current.id,
    )
    validate_trip(db, current, row)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车辆或驾驶员不存在")
    db.refresh(row)
    return row


@router.get("/{trip_id}", response_model=TripRequestOut)
def get_trip_request(db: DbSession, current: CurrentUser, trip_id: int) -> TripRequest:
    row = db.get(TripRequest, trip_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用车申请不存在")
    assert_trip_visible(db, current, row)
    return row


@router.patch("/{trip_id}", response_model=TripRequestOut)
def update_trip_request(db: DbSession, current: CurrentUser, trip_id: int, body: TripRequestUpdate) -> TripRequest:
    row = db.scalar(select(TripRequest).where(TripRequest.id == trip_id).with_for_update())
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用车申请不存在")
    assert_trip_visible(db, current, row)
    data = normalize_trip_update(db, current, row, body)
    previous_status = row.status
    if previous_status in {"completed", "cancelled", "rejected"} and set(data) - {"notes", "status"}:
        raise HTTPException(409, "已结束的申请只能修改备注")
    if "status" in data and data["status"] is not None:
        st = str(data["status"]).strip()
        if st not in ALLOWED_STATUS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="状态值不合法")
        data["status"] = st
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    validate_trip(db, current, row, previous_status)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车辆或驾驶员不存在")
    db.refresh(row)
    return row


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip_request(db: DbSession, current: FleetUser, trip_id: int) -> None:
    row = db.get(TripRequest, trip_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用车申请不存在")
    assert_trip_visible(db, current, row)
    db.delete(row)
    db.commit()
