from datetime import date, datetime, timedelta
from app.core.datetime_utils import shanghai_day_start
from decimal import Decimal
from io import BytesIO
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import and_, case, func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.core.data_scope import scoped, require_vehicle_access, require_workshop_access, require_global_management, validate_workshop
from app.models.fuel import FuelBalance, FuelCard, FuelEntry, FuelRecord
from app.models.media_asset import MediaAsset
from app.models.vehicle import Vehicle
from app.services.fuel_sync_service import stream_fuel_sync
from app.services.fuel_sync_stats_service import get_fuel_sync_stats
from app.services.workshop_service import (
    apply_workshop_name_to_fuel_record,
    list_active_workshop_names,
    resolve_workshop_filter,
)
from app.schemas.fuel import (
    FuelBalanceBucket,
    FuelBalancePage,
    FuelBalanceOut,
    FuelCardCreate,
    FuelCardOut,
    FuelCardUpdate,
    FuelEntryOut,
    FuelRecordCreate,
    FuelRecordOut,
    FuelRecordPage,
    FuelSyncRequest,
    FuelSyncStatsOut,
)
from app.services.media_storage_service import delete_media, download_response, save_upload

router = APIRouter(prefix="/fuel", tags=["fuel"])

# 余额区间档位定义（按“合计”total 划分）。
# stat 表示统计条件类型：zero -> total==0；range -> lower < total <= upper；high -> total > lower。
# filter_min / filter_max 是前端点击图表时用于筛选表格的边界（total >= filter_min 且 total <= filter_max）。
_BALANCE_BUCKETS: list[dict] = [
    {"key": "zero", "label": "= 0", "stat": "zero", "lower": None, "upper": None, "filter_min": 0, "filter_max": 0},
    {"key": "b1", "label": "0 - 200", "stat": "range", "lower": 0, "upper": 200, "filter_min": Decimal("0.01"), "filter_max": 200},
    {"key": "b2", "label": "200 - 500", "stat": "range", "lower": 200, "upper": 500, "filter_min": Decimal("200.01"), "filter_max": 500},
    {"key": "b3", "label": "500 - 1000", "stat": "range", "lower": 500, "upper": 1000, "filter_min": Decimal("500.01"), "filter_max": 1000},
    {"key": "b4", "label": "1000 - 2000", "stat": "range", "lower": 1000, "upper": 2000, "filter_min": Decimal("1000.01"), "filter_max": 2000},
    {"key": "b5", "label": "2000 - 5000", "stat": "range", "lower": 2000, "upper": 5000, "filter_min": Decimal("2000.01"), "filter_max": 5000},
    {"key": "b6", "label": "5000 以上", "stat": "high", "lower": 5000, "upper": None, "filter_min": Decimal("5000.01"), "filter_max": None},
]


def _bucket_stat_cond(bucket: dict):
    """根据档位定义构造该档的统计过滤条件。"""
    if bucket["stat"] == "zero":
        return FuelBalance.total == 0
    if bucket["stat"] == "high":
        return FuelBalance.total > bucket["lower"]
    return and_(FuelBalance.total > bucket["lower"], FuelBalance.total <= bucket["upper"])


@router.post("/sync")
async def sync_fuel_from_platform(current: CurrentUser, body: FuelSyncRequest) -> StreamingResponse:
    """允许所有已登录账号调用本地昆仑司机卡接口刷新余额。"""
    return StreamingResponse(
        stream_fuel_sync(body.date_from, body.date_to, user_id=current.id),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/sync-stats", response_model=FuelSyncStatsOut)
def fuel_sync_stats(db: DbSession, current: CurrentUser) -> FuelSyncStatsOut:
    """今日油卡余额同步次数与上次刷新时间。"""
    stats = get_fuel_sync_stats(db)
    return FuelSyncStatsOut(**stats)


@router.get("/balance-workshops", response_model=list[str])
def list_balance_workshops(db: DbSession, current: CurrentUser) -> list[str]:
    return [name for name in list_active_workshop_names(db) if name.strip() != "留存"]


@router.get("/balance-vehicles", response_model=list[str])
def list_balance_vehicles(db: DbSession, current: CurrentUser) -> list[str]:
    conds: list = [
        FuelBalance.vehicle_no != "",
        func.trim(FuelBalance.workshop) != "留存",
        func.trim(FuelBalance.vehicle_no) != "留存",
    ]
    stmt = (
        select(FuelBalance.vehicle_no)
        .where(and_(*conds))
        .distinct()
        .order_by(FuelBalance.vehicle_no.asc())
    )
    return list(db.scalars(stmt).all())


@router.get("/balances", response_model=FuelBalancePage)
def list_balances(
    db: DbSession,
    current: CurrentUser,
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数")] = 15,
    workshop: Annotated[str | None, Query(max_length=128, description="车间名称模糊匹配")] = None,
    vehicle_no: Annotated[str | None, Query(max_length=64, description="车牌号精确匹配")] = None,
    total_min: Annotated[float | None, Query(description="合计余额下限（含）")] = None,
    total_max: Annotated[float | None, Query(description="合计余额上限（含）")] = None,
    sort_by: Annotated[
        Literal["card_no", "workshop", "vehicle_no", "amount", "reserve_fund", "total"],
        Query(description="排序字段"),
    ] = "card_no",
    sort_dir: Annotated[Literal["asc", "desc"], Query(description="排序方向")] = "asc",
) -> FuelBalancePage:
    # “留存”是内部保留卡。现有数据主要记录在 vehicle_no，兼容旧数据中记录在 workshop 的情况。
    # 它不参与页面列表、合计和区间统计。
    base_conds: list = [
        func.trim(FuelBalance.workshop) != "留存",
        func.trim(FuelBalance.vehicle_no) != "留存",
    ]
    # 油卡余额是全段共享查询数据，所有已登录账号都查看完整列表；
    # workshop / vehicle_no 仅作为用户主动选择的筛选条件。
    ws = resolve_workshop_filter(db, workshop)
    if ws:
        base_conds.append(FuelBalance.workshop == ws)
    vehicle = (vehicle_no or "").strip()
    if vehicle:
        base_conds.append(FuelBalance.vehicle_no == vehicle)

    # 表格与“共X张/合计”随价格区间变化；区间分布图（buckets）随车间和车牌变化。
    data_conds = list(base_conds)
    if total_min is not None:
        data_conds.append(FuelBalance.total >= total_min)
    if total_max is not None:
        data_conds.append(FuelBalance.total <= total_max)

    cnt_stmt = select(func.count()).select_from(FuelBalance)
    sum_stmt = select(func.coalesce(func.sum(FuelBalance.total), 0)).select_from(FuelBalance)

    stat_cols = []
    for b in _BALANCE_BUCKETS:
        cond = _bucket_stat_cond(b)
        stat_cols.append(func.coalesce(func.sum(case((cond, 1), else_=0)), 0))
        stat_cols.append(func.coalesce(func.sum(case((cond, FuelBalance.total), else_=0)), 0))
    stat_stmt = select(*stat_cols).select_from(FuelBalance)

    stmt = select(FuelBalance)
    if base_conds:
        w = and_(*base_conds)
        stat_stmt = stat_stmt.where(w)
    if data_conds:
        w = and_(*data_conds)
        cnt_stmt = cnt_stmt.where(w)
        sum_stmt = sum_stmt.where(w)
        stmt = stmt.where(w)

    total = int(db.scalar(cnt_stmt) or 0)
    total_amount = db.scalar(sum_stmt) or 0

    stat_row = db.execute(stat_stmt).one()
    buckets: list[FuelBalanceBucket] = []
    for idx, b in enumerate(_BALANCE_BUCKETS):
        cnt = int(stat_row[idx * 2] or 0)
        amt = stat_row[idx * 2 + 1] or 0
        buckets.append(
            FuelBalanceBucket(
                key=b["key"],
                label=b["label"],
                filter_min=b["filter_min"],
                filter_max=b["filter_max"],
                count=cnt,
                sum=amt,
            )
        )

    offset = (page - 1) * page_size
    sort_col_map = {
        "card_no": FuelBalance.card_no,
        "workshop": FuelBalance.workshop,
        "vehicle_no": FuelBalance.vehicle_no,
        "amount": FuelBalance.amount,
        "reserve_fund": FuelBalance.reserve_fund,
        "total": FuelBalance.total,
    }
    col = sort_col_map[sort_by]
    order_col = col.asc() if sort_dir == "asc" else col.desc()
    stmt = stmt.order_by(order_col, FuelBalance.id.asc()).offset(offset).limit(page_size)
    items = list(db.scalars(stmt).all())
    return FuelBalancePage(
        items=items,
        total=total,
        total_amount=total_amount,
        buckets=buckets,
    )


@router.get("/cards", response_model=list[FuelCardOut])
def list_cards(
    db: DbSession,
    current: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[FuelCard]:
    stmt = select(FuelCard).order_by(FuelCard.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("/cards", response_model=FuelCardOut, status_code=status.HTTP_201_CREATED)
def create_card(db: DbSession, current: FleetUser, body: FuelCardCreate) -> FuelCard:
    require_global_management(current)
    row = FuelCard(
        card_no=body.card_no.strip(),
        col_c=body.col_c.strip(),
        col_d=body.col_d.strip(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="油卡卡号已存在")
    db.refresh(row)
    return row


@router.patch("/cards/{card_id}", response_model=FuelCardOut)
def update_card(db: DbSession, current: FleetUser, card_id: int, body: FuelCardUpdate) -> FuelCard:
    require_global_management(current)
    row = db.get(FuelCard, card_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="油卡不存在")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(db: DbSession, current: FleetUser, card_id: int) -> None:
    require_global_management(current)
    row = db.get(FuelCard, card_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="油卡不存在")
    card = db.get(FuelCard, card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="油卡不存在")
    cnt = int(db.scalar(scoped(select(func.count()).select_from(FuelRecord), FuelRecord, current).where(FuelRecord.card_asn == card.card_no)) or 0)
    if cnt:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先删除该油卡下的加油流水")
    db.delete(row)
    db.commit()


@router.get("/records", response_model=FuelRecordPage)
def list_records(
    db: DbSession,
    current: CurrentUser,
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数")] = 20,
    card_asn: Annotated[str | None, Query(max_length=64, description="卡号（精确匹配）")] = None,
    workshop: Annotated[str | None, Query(max_length=128, description="车间（按流水记录 workshop 精确匹配）")] = None,
    date_from: Annotated[date | None, Query(description="交易日期起（含）")] = None,
    date_to: Annotated[date | None, Query(description="交易日期止（含）")] = None,
    sort_by: Annotated[
        Literal["occur_time", "workshop", "amount", "volumn", "car_no", "card_asn"],
        Query(description="排序字段"),
    ] = "card_asn",
    sort_dir: Annotated[Literal["asc", "desc"], Query(description="排序方向")] = "asc",
) -> FuelRecordPage:
    conds: list = []
    cnt_stmt = scoped(select(func.count()).select_from(FuelRecord), FuelRecord, current)
    stmt = scoped(select(FuelRecord), FuelRecord, current)
    card = (card_asn or "").strip()
    if card:
        conds.append(FuelRecord.card_asn == card)
    ws = resolve_workshop_filter(db, workshop)
    if ws:
        conds.append(FuelRecord.workshop == ws)
    if date_from is not None:
        conds.append(FuelRecord.occur_time >= shanghai_day_start(date_from))
    if date_to is not None:
        conds.append(FuelRecord.occur_time < shanghai_day_start(date_to + timedelta(days=1)))
    if conds:
        w = and_(*conds)
        cnt_stmt = cnt_stmt.where(w)
        stmt = stmt.where(w)
    total = int(db.scalar(cnt_stmt) or 0)
    offset = (page - 1) * page_size
    sort_col_map = {
        "occur_time": FuelRecord.occur_time,
        "workshop": FuelRecord.workshop,
        "amount": FuelRecord.amount,
        "volumn": FuelRecord.volumn,
        "car_no": FuelRecord.car_no,
        "card_asn": FuelRecord.card_asn,
    }
    col = sort_col_map[sort_by]
    order_col = col.asc() if sort_dir == "asc" else col.desc()
    stmt = stmt.order_by(order_col, FuelRecord.id.asc()).offset(offset).limit(page_size)
    items = list(db.scalars(stmt).all())
    return FuelRecordPage(items=items, total=total)


def _record_conditions(
    db: DbSession,
    card_asn: str | None,
    workshop: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list:
    conds: list = []
    card = (card_asn or "").strip()
    if card:
        conds.append(FuelRecord.card_asn == card)
    ws = resolve_workshop_filter(db, workshop)
    if ws:
        conds.append(FuelRecord.workshop == ws)
    if date_from is not None:
        conds.append(FuelRecord.occur_time >= shanghai_day_start(date_from))
    if date_to is not None:
        conds.append(FuelRecord.occur_time < shanghai_day_start(date_to + timedelta(days=1)))
    return conds


@router.get("/record-workshops", response_model=list[str])
def list_record_workshops(db: DbSession, current: CurrentUser) -> list[str]:
    return list_active_workshop_names(db)


@router.get("/record-cards", response_model=list[str])
def list_record_cards(db: DbSession, current: CurrentUser) -> list[str]:
    rows = db.execute(
        scoped(select(FuelRecord.card_asn), FuelRecord, current)
        .where(FuelRecord.card_asn != "")
        .distinct()
        .order_by(FuelRecord.card_asn.asc())
    ).all()
    return [card.strip() for (card,) in rows if card and card.strip()]


@router.get("/records/export.xlsx")
def export_records_xlsx(
    db: DbSession,
    current: CurrentUser,
    card_asn: Annotated[str | None, Query(max_length=64)] = None,
    workshop: Annotated[str | None, Query(max_length=128)] = None,
    date_from: Annotated[date | None, Query(description="交易日期起（含）")] = None,
    date_to: Annotated[date | None, Query(description="交易日期止（含）")] = None,
) -> StreamingResponse:
    conds = _record_conditions(db, card_asn, workshop, date_from, date_to)
    stmt = scoped(select(FuelRecord), FuelRecord, current)
    if conds:
        stmt = stmt.where(and_(*conds))
    rows = list(db.scalars(stmt.order_by(FuelRecord.id.desc())).all())

    wb = Workbook()
    ws = wb.active
    ws.title = "加油流水"
    ws.append(["ID", "油卡卡号", "车号", "车间", "发生时间", "升数", "单价", "金额", "机构", "卡余额", "油品"])
    for r in rows:
        vol = float(r.volumn or 0)
        amount = float(r.amount or 0)
        unit_price = round(amount / vol, 2) if vol > 0 else 0
        occur = r.occur_time.isoformat() if hasattr(r.occur_time, "isoformat") else str(r.occur_time or "")
        ws.append(
            [
                r.id,
                r.card_asn,
                r.car_no,
                r.workshop,
                occur,
                str(r.volumn),
                str(unit_price),
                str(r.amount),
                r.org_name,
                str(r.balance),
                r.gift_name,
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=fuel_records.xlsx"},
    )


def _fuel_entry_out(db: DbSession, row: FuelEntry) -> FuelEntryOut:
    vehicle = db.get(Vehicle, row.vehicle_id)
    out = FuelEntryOut.model_validate(row)
    out.plate_number = vehicle.plate_number if vehicle else ""
    out.has_photo = bool(row.photo_path)
    return out


@router.post("/entries", response_model=FuelEntryOut, status_code=status.HTTP_201_CREATED)
def create_fuel_entry(
    db: DbSession,
    current: CurrentUser,
    vehicle_id: Annotated[int, Form(ge=1)],
    odometer: Annotated[int, Form(ge=0, le=2_000_000_000)],
    fueled_at: Annotated[datetime, Form()],
    photo: UploadFile | None = File(None),
) -> FuelEntryOut:
    """保存移动端人工加油登记；业务字段入库，照片写入配置的私有媒体存储。"""
    require_vehicle_access(db, current, vehicle_id)
    if photo and photo.filename and not (photo.content_type or "").lower().startswith("image/"):
        raise HTTPException(400, "加油凭证只能上传图片")

    row = FuelEntry(
        vehicle_id=vehicle_id,
        odometer=odometer,
        fueled_at=fueled_at,
        created_by=current.id,
    )
    stored = None
    try:
        db.add(row)
        db.flush()
        if photo and photo.filename:
            stored = save_upload(photo, prefix=f"fuel/entries/{row.id}")
            row.photo_path = stored.reference
            db.add(
                MediaAsset(
                    owner_type="fuel_entry",
                    owner_id=row.id,
                    kind="fuel_photo",
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
        db.refresh(row)
    except Exception:
        db.rollback()
        if stored:
            try:
                delete_media(stored)
            except Exception:
                pass
        raise
    return _fuel_entry_out(db, row)


@router.get("/entries/{entry_id}/photo")
def get_fuel_entry_photo(db: DbSession, current: CurrentUser, entry_id: int):
    row = db.get(FuelEntry, entry_id)
    if not row:
        raise HTTPException(404, "加油记录不存在")
    require_vehicle_access(db, current, row.vehicle_id)
    if not row.photo_path:
        raise HTTPException(404, "该记录没有照片")
    return download_response(row.photo_path)


@router.post("/records", response_model=FuelRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(db: DbSession, current: FleetUser, body: FuelRecordCreate) -> FuelRecord:
    validate_workshop(db, body.workshop_id)
    row = FuelRecord(
        card_asn=body.card_asn.strip(),
        car_no=body.car_no.strip(),
        occur_time=body.occur_time,
        volumn=body.volumn,
        amount=body.amount,
        balance=body.balance,
        workshop=body.workshop.strip(),
        workshop_id=body.workshop_id,
        org_name=body.org_name.strip(),
        gift_name=body.gift_name.strip(),
    )
    if body.workshop_id is None:
        apply_workshop_name_to_fuel_record(db, row, body.workshop)
    else:
        from app.models.workshop import Workshop
        row.workshop = db.get(Workshop, body.workshop_id).name
    require_workshop_access(current, row.workshop_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(db: DbSession, current: FleetUser, record_id: int) -> None:
    row = db.get(FuelRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="加油记录不存在")
    require_workshop_access(current, row.workshop_id)
    db.delete(row)
    db.commit()
