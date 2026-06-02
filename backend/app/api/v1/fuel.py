from datetime import date, datetime
from io import BytesIO
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import and_, case, func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, DbSession
from app.core.rbac import FleetUser
from app.models.fuel import FuelBalance, FuelCard, FuelRecord
from app.services.fuel_sync_service import stream_fuel_sync
from app.services.workshop_service import (
    apply_workshop_name_to_fuel_record,
    list_active_workshop_names,
    resolve_workshop_filter,
)
from app.schemas.fuel import (
    FuelBalancePage,
    FuelBalanceOut,
    FuelCardCreate,
    FuelCardOut,
    FuelCardUpdate,
    FuelRecordCreate,
    FuelRecordOut,
    FuelRecordPage,
    FuelSyncRequest,
)

router = APIRouter(prefix="/fuel", tags=["fuel"])


@router.post("/sync")
async def sync_fuel_from_platform(_: CurrentUser, body: FuelSyncRequest) -> StreamingResponse:
    """登录中国石油拉取油卡余额与流水，写入数据库（NDJSON 流式返回进度）。"""
    return StreamingResponse(
        stream_fuel_sync(body.date_from, body.date_to),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/balance-workshops", response_model=list[str])
def list_balance_workshops(db: DbSession, _: CurrentUser) -> list[str]:
    return list_active_workshop_names(db)


@router.get("/balances", response_model=FuelBalancePage)
def list_balances(
    db: DbSession,
    _: CurrentUser,
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数")] = 15,
    workshop: Annotated[str | None, Query(max_length=128, description="车间名称模糊匹配")] = None,
    amount_bucket: Annotated[str | None, Query(pattern="^(zero|low|high)$")] = None,
    sort_by: Annotated[
        Literal["card_no", "workshop", "vehicle_no", "amount", "reserve_fund", "total"],
        Query(description="排序字段"),
    ] = "card_no",
    sort_dir: Annotated[Literal["asc", "desc"], Query(description="排序方向")] = "asc",
) -> FuelBalancePage:
    base_conds: list = []
    ws = resolve_workshop_filter(db, workshop)
    if ws:
        base_conds.append(FuelBalance.workshop == ws)

    data_conds = list(base_conds)
    if amount_bucket == "zero":
        data_conds.append(FuelBalance.total == 0)
    elif amount_bucket == "low":
        data_conds.append(and_(FuelBalance.total > 0, FuelBalance.total <= 500))
    elif amount_bucket == "high":
        data_conds.append(FuelBalance.total > 500)

    cnt_stmt = select(func.count()).select_from(FuelBalance)
    sum_stmt = select(func.coalesce(func.sum(FuelBalance.total), 0)).select_from(FuelBalance)
    stat_stmt = select(
        func.coalesce(func.sum(case((FuelBalance.total == 0, 1), else_=0)), 0),
        func.coalesce(
            func.sum(case((and_(FuelBalance.total > 0, FuelBalance.total <= 500), 1), else_=0)),
            0,
        ),
        func.coalesce(func.sum(case((FuelBalance.total > 500, 1), else_=0)), 0),
        func.coalesce(func.sum(case((FuelBalance.total == 0, FuelBalance.total), else_=0)), 0),
        func.coalesce(
            func.sum(case((and_(FuelBalance.total > 0, FuelBalance.total <= 500), FuelBalance.total), else_=0)),
            0,
        ),
        func.coalesce(func.sum(case((FuelBalance.total > 500, FuelBalance.total), else_=0)), 0),
    ).select_from(FuelBalance)
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
    count_zero, count_low, count_high, sum_zero, sum_low, sum_high = db.execute(stat_stmt).one()
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
        count_zero=int(count_zero or 0),
        count_low=int(count_low or 0),
        count_high=int(count_high or 0),
        sum_zero=sum_zero or 0,
        sum_low=sum_low or 0,
        sum_high=sum_high or 0,
    )


@router.get("/cards", response_model=list[FuelCardOut])
def list_cards(
    db: DbSession,
    _: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[FuelCard]:
    stmt = select(FuelCard).order_by(FuelCard.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


@router.post("/cards", response_model=FuelCardOut, status_code=status.HTTP_201_CREATED)
def create_card(db: DbSession, _: FleetUser, body: FuelCardCreate) -> FuelCard:
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
def update_card(db: DbSession, _: FleetUser, card_id: int, body: FuelCardUpdate) -> FuelCard:
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
def delete_card(db: DbSession, _: FleetUser, card_id: int) -> None:
    row = db.get(FuelCard, card_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="油卡不存在")
    card = db.get(FuelCard, card_id)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="油卡不存在")
    cnt = int(db.scalar(select(func.count()).select_from(FuelRecord).where(FuelRecord.card_asn == card.card_no)) or 0)
    if cnt:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="请先删除该油卡下的加油流水")
    db.delete(row)
    db.commit()


@router.get("/records", response_model=FuelRecordPage)
def list_records(
    db: DbSession,
    _: CurrentUser,
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
    cnt_stmt = select(func.count()).select_from(FuelRecord)
    stmt = select(FuelRecord)
    card = (card_asn or "").strip()
    if card:
        conds.append(FuelRecord.card_asn == card)
    ws = resolve_workshop_filter(db, workshop)
    if ws:
        conds.append(FuelRecord.workshop == ws)
    if date_from is not None:
        conds.append(FuelRecord.occur_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        conds.append(FuelRecord.occur_time <= datetime.combine(date_to, datetime.max.time()))
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
        conds.append(FuelRecord.occur_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        conds.append(FuelRecord.occur_time <= datetime.combine(date_to, datetime.max.time()))
    return conds


@router.get("/record-workshops", response_model=list[str])
def list_record_workshops(db: DbSession, _: CurrentUser) -> list[str]:
    return list_active_workshop_names(db)


@router.get("/record-cards", response_model=list[str])
def list_record_cards(db: DbSession, _: CurrentUser) -> list[str]:
    rows = db.execute(
        select(FuelRecord.card_asn)
        .where(FuelRecord.card_asn != "")
        .distinct()
        .order_by(FuelRecord.card_asn.asc())
    ).all()
    return [card.strip() for (card,) in rows if card and card.strip()]


@router.get("/records/export.xlsx")
def export_records_xlsx(
    db: DbSession,
    _: CurrentUser,
    card_asn: Annotated[str | None, Query(max_length=64)] = None,
    workshop: Annotated[str | None, Query(max_length=128)] = None,
    date_from: Annotated[date | None, Query(description="交易日期起（含）")] = None,
    date_to: Annotated[date | None, Query(description="交易日期止（含）")] = None,
) -> StreamingResponse:
    conds = _record_conditions(db, card_asn, workshop, date_from, date_to)
    stmt = select(FuelRecord)
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


@router.post("/records", response_model=FuelRecordOut, status_code=status.HTTP_201_CREATED)
def create_record(db: DbSession, _: FleetUser, body: FuelRecordCreate) -> FuelRecord:
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
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(db: DbSession, _: FleetUser, record_id: int) -> None:
    row = db.get(FuelRecord, record_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="加油记录不存在")
    db.delete(row)
    db.commit()
