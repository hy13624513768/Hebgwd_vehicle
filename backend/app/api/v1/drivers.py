import re
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.core.data_scope import require_workshop_access
from app.core.roles import is_account_admin
from app.models.driver import Driver
from app.models.media_asset import MediaAsset
from app.models.workshop import Workshop
from app.schemas.driver import (
    DriverCreate,
    DriverDocumentOut,
    DriverFiltersOut,
    DriverListOut,
    DriverOut,
    DriverStatsOut,
    DriverUpdate,
)
from app.services.driver_service import driver_to_out, drivers_to_out_list, validate_driver_account
from app.services.media_storage_service import StoredMedia, delete_media, download_response, save_upload
from app.services.workshop_service import get_workshop_by_id, list_active_workshop_names

router = APIRouter(prefix="/drivers", tags=["drivers"])

DriverDocumentKind = Literal["health_check_report", "outsourcing_onboarding"]
_DOCUMENT_FIELDS: dict[DriverDocumentKind, str] = {
    "health_check_report": "health_check_report",
    "outsourcing_onboarding": "outsourcing_onboarding",
}


def _driver_or_404(db: Session, driver_id: int) -> Driver:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    return row


def _require_driver_document_view(db: Session, current, row: Driver) -> None:
    if driver_to_out(db, row, current).is_restricted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该驾驶员档案附件")


def _stored_from_asset(asset: MediaAsset) -> StoredMedia:
    return StoredMedia(
        reference=f"media://{asset.storage_backend}/_/{asset.object_key}",
        backend=asset.storage_backend,
        bucket=asset.bucket,
        object_key=asset.object_key,
        original_name=asset.original_name,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
    )


def _document_assets(db: Session, driver_id: int, kind: DriverDocumentKind) -> list[MediaAsset]:
    return list(
        db.scalars(
            select(MediaAsset).where(
                MediaAsset.owner_type == "driver",
                MediaAsset.owner_id == driver_id,
                MediaAsset.kind == kind,
            )
        ).all()
    )


def _cleanup_replaced_assets(db: Session, assets: list[MediaAsset]) -> None:
    """新引用提交成功后清理旧对象；删除失败时保留元数据供运维重试。"""
    removed: list[MediaAsset] = []
    for asset in assets:
        try:
            delete_media(_stored_from_asset(asset))
        except Exception:
            continue
        removed.append(asset)
    if not removed:
        return
    for asset in removed:
        db.delete(asset)
    db.commit()


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
def driver_filters(db: DbSession, current: CurrentUser) -> DriverFiltersOut:
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
def driver_stats(db: DbSession, current: CurrentUser) -> DriverStatsOut:
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
    current: CurrentUser,
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
                *([Driver.id_card.ilike(like)] if is_account_admin(current.role) else []),
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
    stmt = stmt.order_by(Driver.workshop_id.asc().nulls_last(), Driver.sort_no.asc().nulls_last(), Driver.id.asc()).offset(skip).limit(limit)
    items = list(db.scalars(stmt).all())
    return DriverListOut(items=drivers_to_out_list(db, items, current), total=total)


@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(db: DbSession, current: FleetUser, body: DriverCreate) -> Driver:
    workshop_id = body.workshop_id
    require_workshop_access(current, workshop_id)
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
        first_hire_date=body.first_hire_date,
        workshop_id=workshop_id,
        user_id=body.user_id,
        created_by=current.id,
    )
    validate_driver_account(db, current, row.user_id, row.workshop_id)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号或绑定用户冲突")
    db.refresh(row)
    return driver_to_out(db, row, current)


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(db: DbSession, current: CurrentUser, driver_id: int) -> DriverOut:
    row = _driver_or_404(db, driver_id)
    return driver_to_out(db, row, current)


@router.post(
    "/{driver_id}/documents/{kind}",
    response_model=DriverDocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_driver_document(
    db: DbSession,
    current: FleetUser,
    driver_id: int,
    kind: DriverDocumentKind,
    file: UploadFile = File(...),
) -> DriverDocumentOut:
    """上传或替换驾驶员档案图片；结构化引用入库，文件进入私有媒体存储。"""
    row = _driver_or_404(db, driver_id)
    require_workshop_access(current, row.workshop_id)
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择图片")
    if not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="档案附件只支持图片")

    old_assets = _document_assets(db, driver_id, kind)
    stored = save_upload(file, prefix=f"drivers/{driver_id}/{kind}")
    asset = MediaAsset(
        owner_type="driver",
        owner_id=driver_id,
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
    try:
        setattr(row, _DOCUMENT_FIELDS[kind], stored.reference)
        db.add(asset)
        db.commit()
        db.refresh(asset)
    except Exception:
        db.rollback()
        try:
            delete_media(stored)
        except Exception:
            pass
        raise

    _cleanup_replaced_assets(db, old_assets)
    return DriverDocumentOut(
        kind=kind,
        original_name=asset.original_name,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        created_at=asset.created_at,
    )


@router.get("/{driver_id}/documents/{kind}")
def download_driver_document(
    db: DbSession,
    current: CurrentUser,
    driver_id: int,
    kind: DriverDocumentKind,
):
    row = _driver_or_404(db, driver_id)
    _require_driver_document_view(db, current, row)
    reference = getattr(row, _DOCUMENT_FIELDS[kind])
    if not reference or not reference.startswith("media://"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该档案尚未上传图片")
    asset = db.scalar(
        select(MediaAsset)
        .where(
            MediaAsset.owner_type == "driver",
            MediaAsset.owner_id == driver_id,
            MediaAsset.kind == kind,
            MediaAsset.object_key.is_not(None),
        )
        .order_by(MediaAsset.id.desc())
    )
    return download_response(reference, download_name=asset.original_name if asset else None)


@router.delete("/{driver_id}/documents/{kind}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver_document(
    db: DbSession,
    current: FleetUser,
    driver_id: int,
    kind: DriverDocumentKind,
) -> None:
    row = _driver_or_404(db, driver_id)
    require_workshop_access(current, row.workshop_id)
    assets = _document_assets(db, driver_id, kind)
    setattr(row, _DOCUMENT_FIELDS[kind], None)
    db.commit()
    _cleanup_replaced_assets(db, assets)


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(db: DbSession, current: FleetUser, driver_id: int, body: DriverUpdate) -> DriverOut:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    require_workshop_access(current, row.workshop_id)
    data = body.model_dump(exclude_unset=True)
    if {"user_id", "workshop_id"} & data.keys():
        validate_driver_account(db, current, data.get("user_id", row.user_id), data.get("workshop_id", row.workshop_id))
    if "workshop_id" in data and data["workshop_id"] is not None:
        ws = get_workshop_by_id(db, int(data["workshop_id"]))
        if not ws:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="车间不存在")
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    require_workshop_access(current, row.workshop_id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="手机号或绑定用户冲突")
    db.refresh(row)
    return driver_to_out(db, row, current)


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(db: DbSession, current: FleetUser, driver_id: int) -> None:
    row = db.get(Driver, driver_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="驾驶员不存在")
    require_workshop_access(current, row.workshop_id)
    document_assets = _document_assets(db, driver_id, "health_check_report") + _document_assets(
        db, driver_id, "outsourcing_onboarding"
    )
    db.delete(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该驾驶员仍被用车申请引用，无法删除",
        )
    _cleanup_replaced_assets(db, document_assets)
