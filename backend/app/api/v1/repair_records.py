from __future__ import annotations

from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.core.data_scope import require_vehicle_access
from app.core.roles import is_fleet_management
from app.models.driver import Driver
from app.models.repair_record import RepairRecord, RepairSettlement
from app.models.media_asset import MediaAsset
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
from app.services.media_storage_service import delete_media, save_upload

router = APIRouter(prefix="/repair-records", tags=["repair-records"])

_RECORD_LOAD = joinedload(RepairRecord.settlement).joinedload(RepairSettlement.lines)


def _require_upload_family(file: UploadFile | None, family: str) -> None:
    if not file or not file.filename:
        return
    content_type = (file.content_type or "").lower()
    if not content_type.startswith(f"{family}/"):
        label = "图片" if family == "image" else "视频"
        raise HTTPException(400, f"该位置只能上传{label}文件")


def _get_record(db: DbSession, record_id: int) -> RepairRecord | None:
    return db.scalar(select(RepairRecord).where(RepairRecord.id == record_id).options(_RECORD_LOAD))


@router.get("", response_model=RepairRecordListOut)
def list_repair_records(
    db: DbSession,
    current: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    vehicle_id: Annotated[int | None, Query(ge=1)] = None,
) -> RepairRecordListOut:
    items, total = svc.list_records(db, user=current, skip=skip, limit=limit, vehicle_id=vehicle_id)
    return RepairRecordListOut(items=items, total=total)


@router.get("/settlements/summary", response_model=SettlementSummaryListOut)
def list_settlement_summaries(
    db: DbSession,
    current: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    vehicle_id: Annotated[int | None, Query(ge=1)] = None,
    recognition_status: Annotated[str | None, Query()] = None,
) -> SettlementSummaryListOut:
    items, total, category_totals = svc.list_settlement_summaries(
        db,
        user=current,
        skip=skip,
        limit=limit,
        vehicle_id=vehicle_id,
        status=recognition_status,
    )
    return SettlementSummaryListOut(items=items, total=total, category_totals=category_totals)


@router.get("/settlements/{settlement_id}", response_model=RepairSettlementOut)
def get_settlement(db: DbSession, current: CurrentUser, settlement_id: int) -> RepairSettlementOut:
    row = svc.get_settlement_detail(db, settlement_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="结算单不存在")
    _assert_record_access(db, current, row.repair_record)
    out = RepairSettlementOut.model_validate(row)
    out.lines = sorted(out.lines, key=lambda x: x.line_no)
    return out


@router.get("/files/{record_id}/{filename}")
def get_repair_file(
    current: CurrentUser,
    record_id: int,
    filename: str,
    db: DbSession,
):
    row = db.get(RepairRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    _assert_record_access(db, current, row)
    references = [
        row.photo_duo_path,
        row.photo_item_path,
        row.photo_item_video_path,
        row.photo_settlement_path,
    ]
    reference = next((ref for ref in references if ref and Path(ref).name == filename), None)
    if not reference:
        asset = db.scalar(
            select(MediaAsset).where(
                MediaAsset.owner_type == "repair_record",
                MediaAsset.owner_id == record_id,
                MediaAsset.object_key.endswith(f"/{filename}"),
            )
        )
        if asset:
            reference = (
                f"media://{asset.storage_backend}/"
                f"{quote(asset.bucket or '_', safe='')}/{quote(asset.object_key, safe='/')}"
            )
    if not reference:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return svc.repair_file_response(reference)


@router.get("/{record_id}", response_model=RepairRecordOut)
def get_repair_record(db: DbSession, current: CurrentUser, record_id: int) -> RepairRecordOut:
    row = _get_record(db, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="维修记录不存在")
    _assert_record_access(db, current, row)
    return svc.enrich_record(db, row)


@router.post("", response_model=RepairRecordOut, status_code=status.HTTP_201_CREATED)
def create_repair_record(
    db: DbSession,
    current: CurrentUser,
    vehicle_id: Annotated[int, Form()],
    repair_order_no: Annotated[str, Form()],
    driver_id: Annotated[int | None, Form()] = None,
    auto_recognize: Annotated[bool, Form()] = True,
    photo_duo: list[UploadFile] | None = File(None),
    photo_item: UploadFile | None = File(None),
    photo_item_video: UploadFile | None = File(None),
    photo_settlement: UploadFile | None = File(None),
) -> RepairRecordOut:
    order = repair_order_no.strip()
    if not order:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请填写维修单号")
    duo_uploads = [upload for upload in (photo_duo or []) if upload.filename]
    if len(duo_uploads) > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="驾驶员、车辆及维修材料合影最多上传5张")
    for upload in duo_uploads:
        _require_upload_family(upload, "image")
    _require_upload_family(photo_item, "image")
    _require_upload_family(photo_item_video, "video")
    _require_upload_family(photo_settlement, "image")

    require_vehicle_access(db, current, vehicle_id)
    if not is_fleet_management(current.role):
        own_driver = db.scalar(select(Driver).where(Driver.user_id == current.id))
        if driver_id and (not own_driver or own_driver.id != driver_id):
            raise HTTPException(403, "只能以本人身份上报维修")
        driver_id = own_driver.id if own_driver else None
    elif driver_id:
        driver = db.get(Driver, driver_id)
        if not driver:
            raise HTTPException(400, "驾驶员不存在")
        from app.core.data_scope import require_workshop_access
        require_workshop_access(current, driver.workshop_id)
    row = RepairRecord(
        vehicle_id=vehicle_id,
        driver_id=driver_id or None,
        repair_order_no=order,
        status="submitted",
        created_by=current.id,
    )
    db.add(row)
    db.flush()

    stored_objects = []
    try:
        for index, upload in enumerate(duo_uploads):
            stored = save_upload(upload, prefix=f"repair/records/{row.id}/driver_vehicle_photo")
            stored_objects.append(stored)
            if index == 0:
                row.photo_duo_path = stored.reference
            db.add(
                MediaAsset(
                    owner_type="repair_record",
                    owner_id=row.id,
                    kind="driver_vehicle_photo",
                    storage_backend=stored.backend,
                    bucket=stored.bucket,
                    object_key=stored.object_key,
                    original_name=stored.original_name,
                    content_type=stored.content_type,
                    size_bytes=stored.size_bytes,
                    sha256=stored.sha256,
                    created_by=current.id,
                )
            )
        uploads = (
            ("photo_item_path", "repair_item_photo", photo_item),
            ("photo_item_video_path", "repair_item_video", photo_item_video),
            ("photo_settlement_path", "settlement_photo", photo_settlement),
        )
        for field, kind, upload in uploads:
            if not upload or not upload.filename:
                continue
            stored = save_upload(upload, prefix=f"repair/records/{row.id}/{kind}")
            stored_objects.append(stored)
            setattr(row, field, stored.reference)
            db.add(
                MediaAsset(
                    owner_type="repair_record",
                    owner_id=row.id,
                    kind=kind,
                    storage_backend=stored.backend,
                    bucket=stored.bucket,
                    object_key=stored.object_key,
                    original_name=stored.original_name,
                    content_type=stored.content_type,
                    size_bytes=stored.size_bytes,
                    sha256=stored.sha256,
                    created_by=current.id,
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        for stored in stored_objects:
            try:
                delete_media(stored)
            except Exception:
                pass
        raise

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
def upload_settlement_test(
    db: DbSession,
    current: FleetUser,
    photo_settlement: Annotated[UploadFile, File(description="结算单照片")],
    vehicle_id: Annotated[int | None, Form()] = None,
) -> RepairRecordOut:
    """从本地上传一张结算单样例，立即 AI 识别并归类（逐张测试用）。"""
    if not photo_settlement.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择一张图片")
    _require_upload_family(photo_settlement, "image")

    vehicle = None
    if vehicle_id:
        vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(400, "请明确选择结算单所属车辆")
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先登记至少一辆车")

    require_vehicle_access(db, current, vehicle.id)

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

    stored = None
    try:
        stored = save_upload(photo_settlement, prefix=f"repair/records/{row.id}/settlement_photo")
        row.photo_settlement_path = stored.reference
        db.add(
            MediaAsset(
                owner_type="repair_record",
                owner_id=row.id,
                kind="settlement_photo",
                storage_backend=stored.backend,
                bucket=stored.bucket,
                object_key=stored.object_key,
                original_name=stored.original_name,
                content_type=stored.content_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                created_by=current.id,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if stored:
            try:
                delete_media(stored)
            except Exception:
                pass
        raise

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
def recognize_settlement_endpoint(db: DbSession, current: FleetUser, record_id: int) -> RecognizeOut:
    row = _get_record(db, record_id)
    if not row:
        raise HTTPException(404, "维修记录不存在")
    _assert_record_access(db, current, row)
    try:
        settlement = svc.trigger_recognition(db, record_id)
        db.commit()
        return RecognizeOut(ok=settlement.recognition_status == "done", settlement_id=settlement.id,
                            message="结算单识别完成" if settlement.recognition_status == "done" else settlement.recognition_error or "识别失败")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        return RecognizeOut(ok=False, message=str(exc))


def _assert_record_access(db, user, record):
    require_vehicle_access(db, user, record.vehicle_id)
    if not is_fleet_management(user.role) and record.created_by != user.id:
        raise HTTPException(404, "维修记录不存在")
