from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
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


def upload_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    sub = root / settings.repair_upload_subdir
    sub.mkdir(parents=True, exist_ok=True)
    return sub


def save_upload_file(upload_dir: Path, file) -> str:
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload.bin").suffix or ".jpg"
    name = f"{uuid.uuid4().hex}{suffix}"
    dest = upload_dir / name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest)


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
    skip: int = 0,
    limit: int = 50,
    vehicle_id: int | None = None,
) -> tuple[list[RepairRecordOut], int]:
    stmt = select(RepairRecord).options(
        joinedload(RepairRecord.settlement).joinedload(RepairSettlement.lines)
    )
    count_stmt = select(func.count()).select_from(RepairRecord)
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
    if vehicle_id:
        stmt = stmt.where(RepairRecord.vehicle_id == vehicle_id)
    if status:
        stmt = stmt.where(RepairSettlement.recognition_status == status)

    rows = list(db.execute(stmt.order_by(RepairSettlement.id.desc())).unique().all())
    summaries: list[SettlementSummaryOut] = []
    category_totals: dict[str, float] = {}

    for settlement, record, plate in rows:
        lines = list(
            db.scalars(
                select(RepairSettlementLine).where(RepairSettlementLine.settlement_id == settlement.id)
            ).all()
        )
        cat_sum: dict[str, float] = {}
        for line in lines:
            key = line.category_l1 or "未分类"
            cat_sum[key] = cat_sum.get(key, 0.0) + float(line.amount or 0)
            category_totals[key] = category_totals.get(key, 0.0) + float(line.amount or 0)
        summaries.append(
            SettlementSummaryOut(
                id=settlement.id,
                repair_record_id=record.id,
                vehicle_id=record.vehicle_id,
                plate_number=plate,
                order_no=settlement.order_no,
                service_date=settlement.service_date,
                total_amount=settlement.total_amount,
                mileage_in=settlement.mileage_in,
                shop_name=settlement.shop_name,
                recognition_status=settlement.recognition_status,
                line_count=len(lines),
                category_summary={k: round(v, 2) for k, v in cat_sum.items()},
                created_at=settlement.created_at,
            )
        )

    total = len(summaries)
    page = summaries[skip : skip + limit]
    return page, total, {k: round(v, 2) for k, v in category_totals.items()}


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
