from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.data_scope import scoped
from app.core.roles import is_fleet_management
from fastapi import HTTPException
from fastapi.responses import FileResponse
from app.models.driver import Driver
from app.models.repair_record import RepairRecord, RepairSettlement, RepairSettlementLine
from app.models.vehicle import Vehicle
from app.schemas.repair_record import (
    RepairRecordOut,
    RepairSettlementLineOut,
    RepairSettlementOut,
    SettlementSummaryOut,
)
from app.services.settlement_recognition_service import recognize_and_save
from app.services.media_storage_service import download_response


def repair_file_response(reference: str):
    """兼容历史本地绝对路径，并为新媒体引用返回鉴权后的下载响应。"""
    if reference.startswith("media://"):
        return download_response(reference)
    path = Path(reference)
    if not path.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(path)


def enrich_record(db: Session, row: RepairRecord) -> RepairRecordOut:
    plate = db.scalar(select(Vehicle.plate_number).where(Vehicle.id == row.vehicle_id)) or ""
    driver_name = ""
    if row.driver_id:
        driver_name = db.scalar(select(Driver.name).where(Driver.id == row.driver_id)) or ""
    settlement_out = None
    if row.settlement:
        settlement_out = RepairSettlementOut.model_validate(row.settlement)
        settlement_out.lines = [
            RepairSettlementLineOut.model_validate(x)
            for x in sorted(row.settlement.lines, key=lambda x: x.line_no)
        ]
    out = RepairRecordOut.model_validate(row)
    out.plate_number = plate
    out.driver_name = driver_name
    out.settlement = settlement_out
    return out


def list_records(
    db: Session,
    *,
    user=None,
    skip: int = 0,
    limit: int = 50,
    vehicle_id: int | None = None,
) -> tuple[list[RepairRecordOut], int]:
    stmt = select(RepairRecord).options(
        joinedload(RepairRecord.settlement).joinedload(RepairSettlement.lines)
    )
    count_stmt = select(func.count()).select_from(RepairRecord)
    if user is not None:
        stmt = scoped(stmt, RepairRecord, user)
        count_stmt = scoped(count_stmt, RepairRecord, user)
        if not is_fleet_management(user.role):
            stmt = stmt.where(RepairRecord.created_by == user.id)
            count_stmt = count_stmt.where(RepairRecord.created_by == user.id)
    if vehicle_id:
        stmt = stmt.where(RepairRecord.vehicle_id == vehicle_id)
        count_stmt = count_stmt.where(RepairRecord.vehicle_id == vehicle_id)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(stmt.order_by(RepairRecord.id.desc()).offset(skip).limit(limit)).unique().all()
    )
    return [enrich_record(db, r) for r in rows], total


def list_settlement_summaries(
    db: Session,
    *,
    user=None,
    skip: int = 0,
    limit: int = 100,
    vehicle_id: int | None = None,
    status: str | None = None,
) -> tuple[list[SettlementSummaryOut], int, dict[str, float]]:
    stmt = (
        select(RepairSettlement, RepairRecord, Vehicle.plate_number)
        .join(RepairRecord, RepairRecord.id == RepairSettlement.repair_record_id)
        .join(Vehicle, Vehicle.id == RepairRecord.vehicle_id)
    )
    if user is not None:
        stmt = scoped(stmt, RepairRecord, user)
        if not is_fleet_management(user.role):
            stmt = stmt.where(RepairRecord.created_by == user.id)
    if vehicle_id:
        stmt = stmt.where(RepairRecord.vehicle_id == vehicle_id)
    if status:
        stmt = stmt.where(RepairSettlement.recognition_status == status)

    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    settlement_ids = stmt.with_only_columns(RepairSettlement.id).order_by(None)
    category_totals = {
        category or "未分类": amount
        for category, amount in db.execute(
            select(RepairSettlementLine.category_l1, func.sum(RepairSettlementLine.amount))
            .where(RepairSettlementLine.settlement_id.in_(settlement_ids))
            .group_by(RepairSettlementLine.category_l1)
        ).all()
    }
    rows = db.execute(stmt.order_by(RepairSettlement.id.desc()).offset(skip).limit(limit)).all()
    ids = [settlement.id for settlement, _, _ in rows]
    line_groups = {}
    if ids:
        for line in db.scalars(select(RepairSettlementLine).where(RepairSettlementLine.settlement_id.in_(ids))).all():
            line_groups.setdefault(line.settlement_id, []).append(line)
    summaries = []
    for settlement, record, plate in rows:
        lines = line_groups.get(settlement.id, [])
        categories = {}
        for line in lines:
            category = line.category_l1 or "未分类"
            categories[category] = categories.get(category, 0) + line.amount
        summaries.append(SettlementSummaryOut(
            id=settlement.id, repair_record_id=record.id, vehicle_id=record.vehicle_id,
            plate_number=plate, order_no=settlement.order_no, service_date=settlement.service_date,
            total_amount=settlement.total_amount, mileage_in=settlement.mileage_in,
            shop_name=settlement.shop_name, recognition_status=settlement.recognition_status,
            line_count=len(lines), category_summary=categories, created_at=settlement.created_at,
        ))
    return summaries, total, category_totals


def get_settlement_detail(db: Session, settlement_id: int) -> RepairSettlement | None:
    return db.scalar(
        select(RepairSettlement)
        .where(RepairSettlement.id == settlement_id)
        .options(joinedload(RepairSettlement.lines), joinedload(RepairSettlement.repair_record))
    )


def trigger_recognition(db: Session, record_id: int) -> RepairSettlement:
    row = db.scalar(
        select(RepairRecord)
        .where(RepairRecord.id == record_id)
        .options(joinedload(RepairRecord.settlement).joinedload(RepairSettlement.lines))
    )
    if not row:
        raise ValueError("维修记录不存在")
    return recognize_and_save(db, row)
