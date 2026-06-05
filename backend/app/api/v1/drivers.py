import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.driver import Driver
from app.models.workshop import Workshop
from app.schemas.driver import (
    DriverCreate,
    DriverFiltersOut,
    DriverListOut,
    DriverOut,
    DriverStatsOut,
    DriverUpdate,
)
from app.services.driver_service import driver_to_out, drivers_to_out_list
from app.services.workshop_service import get_workshop_by_id, list_active_workshop_names

router = APIRouter(prefix="/drivers", tags=["drivers"])


def _workshop_label(db: Session, workshop_id: int | None) -> str:
    if not workshop_id:
        return "(未分配)"
    ws = db.get(Workshop, workshop_id)
    return (ws.name if ws else "").strip() or "(未分配)"


def _employment_status_bucket(raw: str | None) -> str:
    """与前端 driverEmploymentStatusLabel 规则一致。"""
    t = (raw or "").strip()
    if not t:
        return "(其他)"
    if t in ("本单位", "外包"):
        return t
    if "外包" in t:
        return "外包"
    if t in ("在岗", "在职"):
        return "本单位"
    return "(其他)"


# 年龄段分桶顺序（与前端展示顺序一致，固定从年轻到年长）
AGE_GROUP_ORDER = ("29岁及以下", "30–39岁", "40–49岁", "50–59岁", "60岁及以上")
_AGE_UNKNOWN = "未知"


def _age_from_id_card(id_card: str | None) -> int | None:
    """从身份证号解析周岁年龄；无法识别返回 None（与前端 idCard.ts 规则一致）。"""
    s = (id_card or "").strip().upper()
    if re.fullmatch(r"\d{17}[\dX]", s):
        year, month, day = int(s[6:10]), int(s[10:12]), int(s[12:14])
    elif re.fullmatch(r"\d{15}", s):
        yy = int(s[6:8])
        year = 2000 + yy if yy <= 30 else 1900 + yy
        month, day = int(s[8:10]), int(s[10:12])
    else:
        return None
    try:
        birth = date(year, month, day)
    except ValueError:
        return None
    today = date.today()
    age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    return age if age >= 0 else None


def _age_group_bucket(age: int | None) -> str:
    if age is None:
        return _AGE_UNKNOWN
    if age < 30:
        return "29岁及以下"
    if age < 40:
        return "30–39岁"
    if age < 50:
        return "40–49岁"
    if age < 60:
        return "50–59岁"
    return "60岁及以上"


@router.get("/filters", response_model=DriverFiltersOut)
def driver_filters(db: DbSession, _: CurrentUser) -> DriverFiltersOut:
    lt_rows = db.execute(
        select(Driver.license_type)
        .where(Driver.license_type != "")
        .distinct()
        .order_by(Driver.license_type.asc())
    ).all()
    return DriverFiltersOut(
        workshops=list_active_workshop_names(db),
        license_types=[r[0] for r in lt_rows],
    )


@router.get("/stats", response_model=DriverStatsOut)
def driver_stats(db: DbSession, _: CurrentUser) -> DriverStatsOut:
    total = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
    by_workshop: dict[str, int] = {}
    for wid, cnt in db.execute(select(Driver.workshop_id, func.count()).group_by(Driver.workshop_id)).all():
        key = _workshop_label(db, wid)
        by_workshop[key] = int(cnt)
    by_license_type: dict[str, int] = {}
    for lt, cnt in db.execute(select(Driver.license_type, func.count()).group_by(Driver.license_type)).all():
        key = (lt or "").strip() or "(未填)"
        by_license_type[key] = int(cnt)
    by_employment_status: dict[str, int] = {"本单位": 0, "外包": 0}
    for st, cnt in db.execute(select(Driver.status, func.count()).group_by(Driver.status)).all():
        bucket = _employment_status_bucket(st)
        if bucket in by_employment_status:
            by_employment_status[bucket] += int(cnt)

    by_age_group: dict[str, int] = {g: 0 for g in AGE_GROUP_ORDER}
    unknown_age = 0
    for (id_card,) in db.execute(select(Driver.id_card)).all():
        group = _age_group_bucket(_age_from_id_card(id_card))
        if group == _AGE_UNKNOWN:
            unknown_age += 1
        else:
            by_age_group[group] += 1
    if unknown_age:
        by_age_group[_AGE_UNKNOWN] = unknown_age

    return DriverStatsOut(
        total=total,
        by_workshop=by_workshop,
        by_license_type=by_license_type,
        by_employment_status=by_employment_status,
        by_age_group=by_age_group,
    )


@router.get("", response_model=DriverListOut)
def list_drivers(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    q: Annotated[str | None, Query(max_length=128)] = None,
    workshop: Annotated[str | None, Query(max_length=64, description="车间标准名（精确匹配）")] = None,
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
    if workshop is not None and workshop.strip():
        ws_name = workshop.strip()
        if ws_name in ("(未分配)", "未分配"):
            conds.append(Driver.workshop_id.is_(None))
        else:
            ws = db.scalar(select(Workshop).where(Workshop.name == ws_name, Workshop.is_active.is_(True)))
            if ws:
                conds.append(Driver.workshop_id == ws.id)
            else:
                conds.append(Driver.workshop_id == -1)
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
    return DriverListOut(items=drivers_to_out_list(db, items), total=total)


@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(db: DbSession, current: FleetUser, body: DriverCreate) -> Driver:
    workshop_id = body.workshop_id
    if workshop_id:
        ws = get_workshop_by_id(db, workshop_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间不存在")
    row = Driver(
        sort_no=body.sort_no,
        name=body.name.strip(),
        phone=body.phone.strip(),
        license_type=(body.license_type or "").strip(),
        vehicle_type_label=(body.vehicle_type_label or "").strip(),
        status=(body.status or "").strip(),
        id_card=(body.id_card or "").strip() or None,
        health_check_report=body.health_check_report,
        outsourcing_onboarding=body.outsourcing_onboarding,
        first_hire_date=body.first_hire_date,
        workshop_id=workshop_id,
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
    return driver_to_out(db, row)


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(db: DbSession, _: CurrentUser, driver_id: int) -> DriverOut:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    return driver_to_out(db, row)


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(db: DbSession, _: FleetUser, driver_id: int, body: DriverUpdate) -> DriverOut:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    data = body.model_dump(exclude_unset=True)
    if "workshop_id" in data and data["workshop_id"] is not None:
        ws = get_workshop_by_id(db, int(data["workshop_id"]))
        if not ws:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间不存在")
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
    return driver_to_out(db, row)


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
