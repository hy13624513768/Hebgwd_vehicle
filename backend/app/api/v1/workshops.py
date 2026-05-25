from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.data.workshop_canonical import CANONICAL_SET, resolve_canonical_workshop_name
from app.models.workshop import Workshop
from app.schemas.workshop import WorkshopCreate, WorkshopListOut, WorkshopOut, WorkshopUpdate

router = APIRouter(prefix="/workshops", tags=["workshops"])


@router.get("", response_model=WorkshopListOut)
def list_workshops(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    active_only: Annotated[bool, Query(description="仅返回启用车间")] = True,
) -> WorkshopListOut:
    stmt = select(Workshop)
    count_stmt = select(func.count()).select_from(Workshop)
    if active_only:
        stmt = stmt.where(Workshop.is_active.is_(True))
        count_stmt = count_stmt.where(Workshop.is_active.is_(True))
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(stmt.order_by(Workshop.sort_order.asc(), Workshop.name.asc()).offset(skip).limit(limit)).all()
    )
    return WorkshopListOut(items=[WorkshopOut.model_validate(r) for r in rows], total=total)


@router.get("/{workshop_id}", response_model=WorkshopOut)
def get_workshop(db: DbSession, _: CurrentUser, workshop_id: int) -> Workshop:
    row = db.get(Workshop, workshop_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车间不存在")
    return row


@router.post("", response_model=WorkshopOut, status_code=status.HTTP_201_CREATED)
def create_workshop(db: DbSession, _: FleetUser, body: WorkshopCreate) -> Workshop:
    canon = resolve_canonical_workshop_name(body.name.strip())
    if canon not in CANONICAL_SET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="车间名称必须在系统总表范围内",
        )
    row = Workshop(
        name=canon,
        code=body.code.strip(),
        sort_order=body.sort_order,
        is_active=body.is_active,
        remarks=body.remarks,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间名称已存在")
    db.refresh(row)
    return row


@router.patch("/{workshop_id}", response_model=WorkshopOut)
def update_workshop(db: DbSession, _: FleetUser, workshop_id: int, body: WorkshopUpdate) -> Workshop:
    row = db.get(Workshop, workshop_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="车间不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        canon = resolve_canonical_workshop_name(str(data["name"]).strip())
        if canon not in CANONICAL_SET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="车间名称必须在系统总表范围内",
            )
        data["name"] = canon
    if "code" in data and data["code"] is not None:
        data["code"] = data["code"].strip()
    for k, v in data.items():
        setattr(row, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间名称已存在")
    db.refresh(row)
    return row
