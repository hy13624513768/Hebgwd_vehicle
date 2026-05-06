from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.maintenance import MaintenanceRecord
from app.schemas.maintenance import MaintenanceCreate, MaintenanceOut, MaintenanceUpdate

router = APIRouter(prefix="/maintenance-records", tags=["maintenance"])


@router.get("", response_model=list[MaintenanceOut])
def list_maintenance(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    vehicle_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[MaintenanceRecord]:
    stmt = select(MaintenanceRecord).order_by(MaintenanceRecord.id.desc()).offset(skip).limit(limit)
    if vehicle_id:
        stmt = stmt.where(MaintenanceRecord.vehicle_id == vehicle_id)
    return list(db.scalars(stmt).all())


@router.post("", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED)
def create_maintenance(db: DbSession, current: FleetUser, body: MaintenanceCreate) -> MaintenanceRecord:
    row = MaintenanceRecord(
        vehicle_id=body.vehicle_id,
        service_date=body.service_date,
        category=body.category.strip(),
        amount=body.amount,
        mileage=body.mileage,
        vendor=body.vendor.strip(),
        description=body.description,
        created_by=current.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车辆不存在")
    db.refresh(row)
    return row


@router.get("/{record_id}", response_model=MaintenanceOut)
def get_maintenance(db: DbSession, _: CurrentUser, record_id: int) -> MaintenanceRecord:
    row = db.get(MaintenanceRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="维保记录不存在")
    return row


@router.patch("/{record_id}", response_model=MaintenanceOut)
def update_maintenance(db: DbSession, _: FleetUser, record_id: int, body: MaintenanceUpdate) -> MaintenanceRecord:
    row = db.get(MaintenanceRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="维保记录不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车辆不存在")
    db.refresh(row)
    return row


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_maintenance(db: DbSession, _: FleetUser, record_id: int) -> None:
    row = db.get(MaintenanceRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="维保记录不存在")
    db.delete(row)
    db.commit()
