from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.repair_record import RepairRecord, RepairSettlement
from app.models.vehicle import Vehicle
from app.schemas.repair_record import (
    RecognizeOut,
    RepairRecordListOut,
    RepairRecordOut,
    RepairSettlementOut,
    SettlementSummaryListOut,
)
from app.services import repair_record_service as svc
from app.services.settlement_recognition_service import recognize_and_save

router = APIRouter(prefix="/repair-records", tags=["repair-records"])

_RECORD_LOAD = joinedload(RepairRecord.settlement).joinedload(RepairSettlement.lines)


def _get_record(db: DbSession, record_id: int) -> RepairRecord | None:
    return db.scalar(select(RepairRecord).where(RepairRecord.id == record_id).options(_RECORD_LOAD))


@router.get("", response_model=RepairRecordListOut)
def list_repair_records(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    vehicle_id: Annotated[int | None, Query(ge=1)] = None,
) -> RepairRecordListOut:
    items, total = svc.list_records(db, skip=skip, limit=limit, vehicle_id=vehicle_id)
    return RepairRecordListOut(items=items, total=total)


@router.get("/settlements/summary", response_model=SettlementSummaryListOut)
def list_settlement_summaries(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    vehicle_id: Annotated[int | None, Query(ge=1)] = None,
    recognition_status: Annotated[str | None, Query()] = None,
) -> SettlementSummaryListOut:
    items, total, category_totals = svc.list_settlement_summaries(
        db,
        skip=skip,
        limit=limit,
        vehicle_id=vehicle_id,
        status=recognition_status,
    )
    return SettlementSummaryListOut(items=items, total=total, category_totals=category_totals)


@router.get("/settlements/{settlement_id}", response_model=RepairSettlementOut)
def get_settlement(db: DbSession, _: CurrentUser, settlement_id: int) -> RepairSettlementOut:
    row = svc.get_settlement_detail(db, settlement_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="结算单不存在")
    out = RepairSettlementOut.model_validate(row)
    out.lines = sorted(out.lines, key=lambda x: x.line_no)
    return out


@router.get("/files/{record_id}/{filename}")
def get_repair_file(
    _: CurrentUser,
    record_id: int,
    filename: str,
    db: DbSession,
):
    row = db.get(RepairRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    allowed = {
        Path(row.photo_duo_path or "").name,
        Path(row.photo_item_path or "").name,
        Path(row.photo_item_video_path or "").name,
        Path(row.photo_settlement_path or "").name,
    }
    if filename not in allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    path = svc.upload_root() / str(record_id) / filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return FileResponse(path)


@router.get("/{record_id}", response_model=RepairRecordOut)
def get_repair_record(db: DbSession, _: CurrentUser, record_id: int) -> RepairRecordOut:
    row = _get_record(db, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="维修记录不存在")
    return svc.enrich_record(db, row)


@router.post("", response_model=RepairRecordOut, status_code=status.HTTP_201_CREATED)
async def create_repair_record(
    db: DbSession,
    current: CurrentUser,
    vehicle_id: Annotated[int, Form()],
    repair_order_no: Annotated[str, Form()],
    driver_id: Annotated[int | None, Form()] = None,
    auto_recognize: Annotated[bool, Form()] = True,
    photo_duo: UploadFile | None = File(None),
    photo_item: UploadFile | None = File(None),
    photo_item_video: UploadFile | None = File(None),
    photo_settlement: UploadFile | None = File(None),
) -> RepairRecordOut:
    order = repair_order_no.strip()
    if not order:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写维修单号")

    row = RepairRecord(
        vehicle_id=vehicle_id,
        driver_id=driver_id or None,
        repair_order_no=order,
        status="submitted",
        created_by=current.id,
    )
    db.add(row)
    db.flush()

    upload_dir = svc.upload_root() / str(row.id)
    if photo_duo and photo_duo.filename:
        row.photo_duo_path = svc.save_upload_file(upload_dir, photo_duo)
    if photo_item and photo_item.filename:
        row.photo_item_path = svc.save_upload_file(upload_dir, photo_item)
    if photo_item_video and photo_item_video.filename:
        row.photo_item_video_path = svc.save_upload_file(upload_dir, photo_item_video)
    if photo_settlement and photo_settlement.filename:
        row.photo_settlement_path = svc.save_upload_file(upload_dir, photo_settlement)

    db.commit()

    if auto_recognize and row.photo_settlement_path:
        try:
            row = _get_record(db, row.id)
            if row:
                recognize_and_save(db, row)
                db.commit()
        except Exception:
            db.rollback()

    row = _get_record(db, row.id)
    return svc.enrich_record(db, row)  # type: ignore[arg-type]


@router.post("/upload-settlement-test", response_model=RepairRecordOut, status_code=status.HTTP_201_CREATED)
async def upload_settlement_test(
    db: DbSession,
    current: FleetUser,
    photo_settlement: Annotated[UploadFile, File(description="结算单照片")],
    vehicle_id: Annotated[int | None, Form()] = None,
) -> RepairRecordOut:
    """从本地上传一张结算单样例，立即 AI 识别并归类（逐张测试用）。"""
    if not photo_settlement.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择一张图片")

    vehicle = None
    if vehicle_id:
        vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        vehicle = db.scalar(select(Vehicle).limit(1))
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先登记至少一辆车")

    from datetime import datetime

    order_no = f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    row = RepairRecord(
        vehicle_id=vehicle.id,
        repair_order_no=order_no,
        status="submitted",
        created_by=current.id,
    )
    db.add(row)
    db.flush()

    upload_dir = svc.upload_root() / str(row.id)
    row.photo_settlement_path = svc.save_upload_file(upload_dir, photo_settlement)
    db.commit()

    try:
        row = _get_record(db, row.id)
        if row:
            recognize_and_save(db, row)
            db.commit()
    except Exception as exc:
        db.rollback()
        row = _get_record(db, row.id)
        if row:
            return svc.enrich_record(db, row)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    row = _get_record(db, row.id)
    return svc.enrich_record(db, row)  # type: ignore[arg-type]


@router.post("/{record_id}/recognize-settlement", response_model=RecognizeOut)
def recognize_settlement_endpoint(db: DbSession, _: FleetUser, record_id: int) -> RecognizeOut:
    try:
        settlement = svc.trigger_recognition(db, record_id)
        db.commit()
        return RecognizeOut(ok=True, settlement_id=settlement.id, message="结算单识别完成")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        return RecognizeOut(ok=False, message=str(exc))
