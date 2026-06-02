from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleOut, VehicleUpdate
from app.services.workshop_service import apply_workshop_name_to_vehicle, get_workshop_by_id

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleOut])
def list_vehicles(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    q: Annotated[str | None, Query(max_length=64)] = None,
) -> list[Vehicle]:
    stmt = select(Vehicle).order_by(Vehicle.id.desc()).offset(skip).limit(limit)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Vehicle.plate_number.ilike(like),
                Vehicle.brand.ilike(like),
                Vehicle.model.ilike(like),
                Vehicle.org_unit.ilike(like),
                Vehicle.vehicle_class.ilike(like),
                Vehicle.vehicle_type_label.ilike(like),
                Vehicle.emission_std.ilike(like),
                Vehicle.displacement.ilike(like),
            )
        )
    return list(db.scalars(stmt).all())


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(db: DbSession, current: FleetUser, body: VehicleCreate) -> Vehicle:
    row = Vehicle(
        plate_number=body.plate_number.strip(),
        brand=body.brand.strip(),
        model=body.model.strip(),
        vin=body.vin.strip() if body.vin else None,
        color=body.color.strip(),
        seats=body.seats,
        mileage=body.mileage,
        status=body.status.strip(),
        remarks=body.remarks,
        org_unit=body.org_unit.strip(),
        workshop_id=body.workshop_id,
        vehicle_class=body.vehicle_class.strip(),
        vehicle_type_label=body.vehicle_type_label.strip(),
        emission_std=body.emission_std.strip(),
        displacement=body.displacement.strip(),
        registered_at=body.registered_at,
        created_by=current.id,
    )
    if body.workshop_id is not None:
        ws = get_workshop_by_id(db, body.workshop_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间不存在")
        row.workshop_id = ws.id
        row.org_unit = ws.name
    else:
        apply_workshop_name_to_vehicle(db, row, body.org_unit)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="车牌号已存在")
    db.refresh(row)
    return row


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(db: DbSession, _: CurrentUser, vehicle_id: int) -> Vehicle:
    row = db.get(Vehicle, vehicle_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")
    return row


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(db: DbSession, _: FleetUser, vehicle_id: int, body: VehicleUpdate) -> Vehicle:
    row = db.get(Vehicle, vehicle_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")
    data = body.model_dump(exclude_unset=True)
    if "workshop_id" in data and data["workshop_id"] is not None:
        ws = get_workshop_by_id(db, int(data["workshop_id"]))
        if not ws:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间不存在")
        row.workshop_id = ws.id
        row.org_unit = ws.name
        data.pop("workshop_id", None)
        data.pop("org_unit", None)
    elif "org_unit" in data and data["org_unit"] is not None:
        apply_workshop_name_to_vehicle(db, row, str(data["org_unit"]))
        data.pop("org_unit", None)
        data.pop("workshop_id", None)
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="车牌号已存在")
    db.refresh(row)
    return row


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(db: DbSession, _: FleetUser, vehicle_id: int) -> None:
    row = db.get(Vehicle, vehicle_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车辆不存在")
    db.delete(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该车辆仍被用车申请或维保记录引用，无法删除",
        )
