from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.roles import WORKSHOP_ADMIN, WORKSHOP_DIRECTOR
from app.data.workshop_canonical import (
    CANONICAL_WORKSHOP_NAMES,
    CANONICAL_SET,
    resolve_canonical_workshop_name,
)
from app.models.driver import Driver
from app.models.fuel import FuelBalance, FuelRecord
from app.models.trip_request import TripRequest
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop

WORKSHOP_SKIP_NAMES = frozenset({"/", ""})


def normalize_workshop_name(name: str | None) -> str:
    return (name or "").strip()


def get_workshop_by_id(db: Session, workshop_id: int | None) -> Workshop | None:
    if not workshop_id:
        return None
    return db.get(Workshop, workshop_id)


def get_workshop_by_name(db: Session, name: str) -> Workshop | None:
    canon = resolve_canonical_workshop_name(name)
    return db.scalar(select(Workshop).where(Workshop.name == canon, Workshop.is_active.is_(True)))


def list_active_workshop_names(db: Session) -> list[str]:
    """供筛选下拉等使用：仅返回总表中的标准车间名。"""
    rows = db.scalars(
        select(Workshop.name)
        .where(Workshop.is_active.is_(True))
        .order_by(Workshop.sort_order.asc(), Workshop.name.asc())
    ).all()
    return list(rows)


def get_or_create_workshop(db: Session, name: str) -> Workshop | None:
    canon = resolve_canonical_workshop_name(name)
    if canon not in CANONICAL_SET:
        return None
    existing = db.scalar(select(Workshop).where(Workshop.name == canon))
    if existing:
        if not existing.is_active:
            existing.is_active = True
        return existing
    row = Workshop(
        name=canon,
        sort_order=CANONICAL_WORKSHOP_NAMES.index(canon),
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def workshop_admin_account_name(workshop: str) -> str:
    canon = resolve_canonical_workshop_name(workshop)
    return f"{canon}管理员"


def ensure_canonical_workshop_master(db: Session) -> int:
    """
    将 bus_workshop 重置为 22 个标准车间，并把各业务表字符串与 workshop_id 全部对齐。
    """
    id_by_name: dict[str, int] = {}
    for idx, name in enumerate(CANONICAL_WORKSHOP_NAMES):
        row = db.scalar(select(Workshop).where(Workshop.name == name))
        if row:
            row.sort_order = idx
            row.is_active = True
            row.name = name
        else:
            row = Workshop(name=name, sort_order=idx, is_active=True)
            db.add(row)
            db.flush()
        id_by_name[name] = row.id

    # 停用不在总表中的旧车间行
    for row in db.scalars(select(Workshop)).all():
        if row.name not in CANONICAL_SET:
            row.is_active = False

    def bind(canonical: str) -> Workshop:
        ws = get_or_create_workshop(db, canonical)
        assert ws is not None
        return ws

    for v in db.scalars(select(Vehicle)).all():
        canon = resolve_canonical_workshop_name(v.org_unit)
        ws = bind(canon)
        v.workshop_id = ws.id
        v.org_unit = ws.name

    for r in db.scalars(select(FuelRecord)).all():
        canon = resolve_canonical_workshop_name(r.workshop)
        ws = bind(canon)
        r.workshop_id = ws.id
        r.workshop = ws.name

    for b in db.scalars(select(FuelBalance)).all():
        canon = resolve_canonical_workshop_name(b.workshop)
        ws = bind(canon)
        b.workshop_id = ws.id
        b.workshop = ws.name

    for d in db.scalars(select(Driver)).all():
        if d.workshop_id:
            old = db.get(Workshop, d.workshop_id)
            canon = resolve_canonical_workshop_name(old.name if old else "")
        else:
            canon = "办公室"
        ws = bind(canon)
        d.workshop_id = ws.id

    for t in db.scalars(select(TripRequest)).all():
        if t.vehicle_id:
            veh = db.get(Vehicle, t.vehicle_id)
            if veh and veh.workshop_id:
                t.workshop_id = veh.workshop_id
                continue
        if t.workshop_id:
            old = db.get(Workshop, t.workshop_id)
            canon = resolve_canonical_workshop_name(old.name if old else "")
        else:
            canon = "办公室"
        t.workshop_id = bind(canon).id

    existing_usernames = {
        (name or "").strip()
        for name in db.scalars(select(User.username)).all()
        if name and str(name).strip()
    }
    claimed_usernames: set[str] = set(existing_usernames)

    for u in db.scalars(select(User).order_by(User.id.asc())).all():
        _link_user_to_workshop(db, u, id_by_name)
        _maybe_rename_workshop_admin_username(db, u, id_by_name, claimed_usernames)

    db.commit()
    return len(CANONICAL_WORKSHOP_NAMES)


def sync_workshops_master_and_links(db: Session) -> int:
    """启动时调用：确保总表与业务关联一致。"""
    return ensure_canonical_workshop_master(db)


def _link_user_to_workshop(db: Session, user: User, id_by_name: dict[str, int]) -> None:
    if user.role not in (WORKSHOP_ADMIN, WORKSHOP_DIRECTOR):
        user.workshop_id = None
        return
    label = (user.display_name or user.username or "").strip()
    if label.endswith("管理员"):
        ws_label = label[: -len("管理员")].strip()
    else:
        ws_label = label
    canon = resolve_canonical_workshop_name(ws_label)
    user.workshop_id = id_by_name.get(canon)
    user.display_name = f"{canon}管理员"


def apply_workshop_name_to_vehicle(db: Session, vehicle: Vehicle, org_unit: str) -> None:
    canon = resolve_canonical_workshop_name(org_unit)
    ws = get_or_create_workshop(db, canon)
    vehicle.org_unit = canon
    vehicle.workshop_id = ws.id if ws else None


def apply_workshop_name_to_fuel_record(db: Session, record: FuelRecord, workshop: str) -> None:
    canon = resolve_canonical_workshop_name(workshop)
    ws = get_or_create_workshop(db, canon)
    record.workshop = canon
    record.workshop_id = ws.id if ws else None


def apply_workshop_name_to_fuel_balance(db: Session, balance: FuelBalance, workshop: str) -> None:
    canon = resolve_canonical_workshop_name(workshop)
    ws = get_or_create_workshop(db, canon)
    balance.workshop = canon
    balance.workshop_id = ws.id if ws else None


def apply_workshop_to_user(db: Session, user: User, workshop_id: int | None) -> None:
    user.workshop_id = workshop_id
    ws = get_workshop_by_id(db, workshop_id)
    if ws and user.role in (WORKSHOP_ADMIN, WORKSHOP_DIRECTOR):
        user.display_name = f"{ws.name}管理员"


def _maybe_rename_workshop_admin_username(
    db: Session,
    user: User,
    id_by_name: dict[str, int],
    claimed_usernames: set[str],
) -> None:
    if user.role not in (WORKSHOP_ADMIN, WORKSHOP_DIRECTOR) or not user.workshop_id:
        return
    canon = next((n for n, wid in id_by_name.items() if wid == user.workshop_id), None)
    if not canon:
        return
    new_username = f"{canon}管理员"
    if user.username == new_username:
        claimed_usernames.add(new_username)
        return
    if new_username in claimed_usernames:
        return
    taken = db.scalar(select(User.id).where(User.username == new_username, User.id != user.id))
    if taken:
        return
    if user.username:
        claimed_usernames.discard(user.username.strip())
    user.username = new_username
    claimed_usernames.add(new_username)


def resolve_workshop_filter(db: Session, workshop: str | None) -> str | None:
    """筛选参数中的车间名统一解析为标准名。"""
    if not workshop or not str(workshop).strip():
        return None
    return resolve_canonical_workshop_name(workshop)
