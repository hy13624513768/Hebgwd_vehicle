from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.maintenance_term import MaintenanceTerm
from app.schemas.maintenance_term import (
    MaintenanceTermCreate,
    MaintenanceTermListOut,
    MaintenanceTermOut,
    MaintenanceTermSeedOut,
    MaintenanceTermStatsOut,
    MaintenanceTermTreeOut,
    MaintenanceTermUpdate,
)
from app.services import maintenance_term_service as svc

router = APIRouter(prefix="/maintenance-terms", tags=["maintenance-terms"])


@router.get("/tree", response_model=MaintenanceTermTreeOut)
def get_term_tree(
    db: DbSession,
    _: CurrentUser,
    active_only: Annotated[bool, Query(description="仅返回启用节点")] = False,
) -> MaintenanceTermTreeOut:
    items = svc.build_tree(db, active_only=active_only)
    stats = svc.get_stats(db)
    return MaintenanceTermTreeOut(items=items, stats=stats)


@router.get("/stats", response_model=MaintenanceTermStatsOut)
def get_term_stats(db: DbSession, _: CurrentUser) -> MaintenanceTermStatsOut:
    return svc.get_stats(db)


@router.get("", response_model=MaintenanceTermListOut)
def list_terms(
    db: DbSession,
    _: CurrentUser,
    parent_id: Annotated[int | None, Query(description="按上级筛选")] = None,
    level: Annotated[int | None, Query(ge=1, le=3, description="按层级筛选")] = None,
    q: Annotated[str | None, Query(description="名称/别名/关键词搜索")] = None,
    active_only: Annotated[bool, Query(description="仅启用")] = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> MaintenanceTermListOut:
    stmt = select(MaintenanceTerm)
    count_stmt = select(func.count()).select_from(MaintenanceTerm)

    if parent_id is not None:
        stmt = stmt.where(MaintenanceTerm.parent_id == parent_id)
        count_stmt = count_stmt.where(MaintenanceTerm.parent_id == parent_id)
    if level is not None:
        stmt = stmt.where(MaintenanceTerm.level == level)
        count_stmt = count_stmt.where(MaintenanceTerm.level == level)
    if active_only:
        stmt = stmt.where(MaintenanceTerm.is_active.is_(True))
        count_stmt = count_stmt.where(MaintenanceTerm.is_active.is_(True))
    if q and q.strip():
        kw = f"%{q.strip()}%"
        cond = or_(
            MaintenanceTerm.name.ilike(kw),
            MaintenanceTerm.aliases.ilike(kw),
            MaintenanceTerm.keywords.ilike(kw),
            MaintenanceTerm.code.ilike(kw),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(
                MaintenanceTerm.sort_order.asc(),
                MaintenanceTerm.id.asc(),
            )
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return MaintenanceTermListOut(
        items=[svc.term_to_out(r) for r in rows],
        total=total,
    )


@router.get("/{term_id}", response_model=MaintenanceTermOut)
def get_term(db: DbSession, _: CurrentUser, term_id: int) -> MaintenanceTermOut:
    row = db.get(MaintenanceTerm, term_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    return svc.term_to_out(row)


@router.post("", response_model=MaintenanceTermOut, status_code=status.HTTP_201_CREATED)
def create_term(db: DbSession, _: FleetUser, body: MaintenanceTermCreate) -> MaintenanceTermOut:
    try:
        row = svc.create_term(db, body)
        db.commit()
        db.refresh(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return svc.term_to_out(row)


@router.patch("/{term_id}", response_model=MaintenanceTermOut)
def update_term(
    db: DbSession,
    _: FleetUser,
    term_id: int,
    body: MaintenanceTermUpdate,
) -> MaintenanceTermOut:
    row = db.get(MaintenanceTerm, term_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    try:
        svc.update_term(db, row, body)
        db.commit()
        db.refresh(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return svc.term_to_out(row)


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_term(db: DbSession, _: FleetUser, term_id: int) -> None:
    row = db.get(MaintenanceTerm, term_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="词条不存在")
    try:
        svc.delete_term(db, row)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/seed-preset", response_model=MaintenanceTermSeedOut)
def seed_preset(
    db: DbSession,
    _: FleetUser,
    force: Annotated[bool, Query(description="清空后重新导入预置分类")] = False,
) -> MaintenanceTermSeedOut:
    try:
        created, skipped = svc.seed_preset_if_empty(db, force=force)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    if skipped:
        return MaintenanceTermSeedOut(
            ok=True,
            created=0,
            skipped=True,
            message="已有数据，未重复导入。如需覆盖请勾选「强制重新导入」。",
        )
    return MaintenanceTermSeedOut(
        ok=True,
        created=created,
        skipped=False,
        message=f"已导入预置分类，共 {created} 条记录。",
    )
