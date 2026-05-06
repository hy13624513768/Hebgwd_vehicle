from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.driver import Driver
from app.schemas.driver import (
    DriverCreate,
    DriverFiltersOut,
    DriverListOut,
    DriverOut,
    DriverStatsOut,
    DriverUpdate,
)

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("/filters", response_model=DriverFiltersOut)
def driver_filters(db: DbSession, _: CurrentUser) -> DriverFiltersOut:
    st_rows = db.execute(
        select(Driver.status).where(Driver.status != "").distinct().order_by(Driver.status.asc())
    ).all()
    lt_rows = db.execute(
        select(Driver.license_type)
        .where(Driver.license_type != "")
        .distinct()
        .order_by(Driver.license_type.asc())
    ).all()
    return DriverFiltersOut(
        statuses=[r[0] for r in st_rows],
        license_types=[r[0] for r in lt_rows],
    )


@router.get("/stats", response_model=DriverStatsOut)
def driver_stats(db: DbSession, _: CurrentUser) -> DriverStatsOut:
    total = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
    by_status: dict[str, int] = {}
    for st, cnt in db.execute(select(Driver.status, func.count()).group_by(Driver.status)).all():
        key = (st or "").strip() or "(未填)"
        by_status[key] = int(cnt)
    by_license_type: dict[str, int] = {}
    for lt, cnt in db.execute(select(Driver.license_type, func.count()).group_by(Driver.license_type)).all():
        key = (lt or "").strip() or "(未填)"
        by_license_type[key] = int(cnt)
    return DriverStatsOut(total=total, by_status=by_status, by_license_type=by_license_type)


@router.get("", response_model=DriverListOut)
def list_drivers(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    q: Annotated[str | None, Query(max_length=128)] = None,
    status: Annotated[str | None, Query(max_length=64, description="状态（精确匹配）")] = None,
    license_type: Annotated[str | None, Query(max_length=32, description="准驾（精确匹配）")] = None,
) -> DriverListOut:
    conds: list = []
    if q and q.strip():
        like = f"%{q.strip()}%"
        conds.append(
            or_(
                Driver.name.ilike(like),
                Driver.phone.ilike(like),
                Driver.id_card.ilike(like),
            )
        )
    if status is not None and status.strip():
        st = status.strip()
        if st in ("(未填)", "未填"):
            conds.append(Driver.status == "")
        else:
            conds.append(Driver.status == st)
    if license_type is not None and license_type.strip():
        lt = license_type.strip()
        if lt in ("(未填)", "未填"):
            conds.append(Driver.license_type == "")
        else:
            conds.append(Driver.license_type == lt)

    cnt_stmt = select(func.count()).select_from(Driver)
    stmt = select(Driver)
    if conds:
        w = and_(*conds)
        cnt_stmt = cnt_stmt.where(w)
        stmt = stmt.where(w)

    total = int(db.scalar(cnt_stmt) or 0)
    stmt = stmt.order_by(Driver.sort_no.asc().nulls_last(), Driver.id.asc()).offset(skip).limit(limit)
    items = list(db.scalars(stmt).all())
    return DriverListOut(items=items, total=total)


@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(db: DbSession, current: FleetUser, body: DriverCreate) -> Driver:
    row = Driver(
        sort_no=body.sort_no,
        name=body.name.strip(),
        phone=body.phone.strip(),
        license_type=(body.license_type or "").strip(),
        status=(body.status or "").strip(),
        id_card=(body.id_card or "").strip() or None,
        health_check_report=body.health_check_report,
        outsourcing_onboarding=body.outsourcing_onboarding,
        first_hire_date=body.first_hire_date,
        user_id=body.user_id,
        created_by=current.id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号或绑定用户冲突")
    db.refresh(row)
    return row


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(db: DbSession, _: CurrentUser, driver_id: int) -> Driver:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    return row


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(db: DbSession, _: FleetUser, driver_id: int, body: DriverUpdate) -> Driver:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号或绑定用户冲突")
    db.refresh(row)
    return row


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(db: DbSession, _: FleetUser, driver_id: int) -> None:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    db.delete(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该驾驶员仍被用车申请引用，无法删除",
        )
