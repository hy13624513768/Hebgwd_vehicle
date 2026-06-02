from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.driver import Driver
from app.models.fuel import FuelBalance, FuelCard, FuelRecord
from app.models.maintenance import MaintenanceRecord
from app.models.nav_preset import NavPreset
from app.models.trip_request import TripRequest
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.workshop import Workshop
from app.data.workshop_canonical import CANONICAL_WORKSHOP_NAMES
from app.services.workshop_service import get_or_create_workshop, workshop_admin_account_name

# 与 link_demo_driver_accounts、历史种子一致，便于演示账号绑定
_DEMO_PHONE_ZHANG = "13800000001"
_DEMO_PHONE_LI = "13800000002"
_DEMO_PLATE_1 = "京A12345"
_DEMO_PLATE_2 = "京B67890"
_DEMO_FUEL_CARD = "DEMO-FUEL-CARD-001"
_DEMO_BALANCE_CARD = "DEMO-BALANCE-001"


def _admin_actor_id(db: Session) -> int:
    admin = db.scalar(select(User).where(User.username == "admin"))
    return int(admin.id) if admin else 1


def seed_demo_if_empty(db: Session) -> None:
    """库中各业务表为空时补齐演示数据；已有车辆但缺驾驶员/派车等时也会补全，避免前端列表全空。"""
    uid = _admin_actor_id(db)
    did_any = False

    vcount = int(db.scalar(select(func.count()).select_from(Vehicle)) or 0)
    if vcount == 0:
        v1 = Vehicle(
            plate_number=_DEMO_PLATE_1,
            brand="红旗",
            model="H9",
            color="黑色",
            seats=5,
            mileage=12000,
            status="active",
            remarks="演示：机关事务管理局公务车",
            created_by=uid,
        )
        v2 = Vehicle(
            plate_number=_DEMO_PLATE_2,
            brand="丰田",
            model="考斯特",
            color="白色",
            seats=19,
            mileage=56000,
            status="repairing",
            remarks="演示：维修中",
            created_by=uid,
        )
        db.add_all([v1, v2])
        db.flush()
        first_vehicle = v1
        did_any = True
    else:
        first_vehicle = db.scalar(select(Vehicle).order_by(Vehicle.id.asc()).limit(1))

    if first_vehicle is None:
        if did_any:
            db.commit()
        return

    dcount = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
    if dcount == 0:
        d1 = Driver(
            sort_no=1,
            name="张三",
            phone=_DEMO_PHONE_ZHANG,
            license_type="A1",
            status="在岗",
            id_card="110101199001011234",
            health_check_report=None,
            outsourcing_onboarding=None,
            first_hire_date=date(2018, 5, 1),
            created_by=uid,
        )
        d2 = Driver(
            sort_no=2,
            name="李四",
            phone=_DEMO_PHONE_LI,
            license_type="C1",
            status="在岗",
            id_card="110101199202022345",
            health_check_report=None,
            outsourcing_onboarding=None,
            first_hire_date=date(2021, 3, 15),
            created_by=uid,
        )
        db.add_all([d1, d2])
        db.flush()
        first_driver = d1
        did_any = True
    else:
        first_driver = db.scalar(select(Driver).order_by(Driver.id.asc()).limit(1))

    tcount = int(db.scalar(select(func.count()).select_from(TripRequest)) or 0)
    if tcount == 0:
        now = datetime.now(timezone.utc)
        t1 = TripRequest(
            purpose="赴市会议中心参加年度工作会议（演示）",
            applicant_name="办公室-王五",
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=4),
            origin="总部大院",
            destination="市会议中心",
            passenger_count=6,
            status="pending",
            vehicle_id=None,
            driver_id=None,
            notes="演示：待调度",
            created_by=uid,
        )
        db.add(t1)
        if first_driver is not None:
            t2 = TripRequest(
                purpose="接待上级单位调研（演示）",
                applicant_name="综合处-赵六",
                start_at=now + timedelta(days=2),
                end_at=now + timedelta(days=2, hours=6),
                origin="总部大院",
                destination="高新区产业园",
                passenger_count=4,
                status="approved",
                vehicle_id=first_vehicle.id,
                driver_id=first_driver.id,
                notes="演示：已批车批人",
                created_by=uid,
            )
            db.add(t2)
        did_any = True

    mcount = int(db.scalar(select(func.count()).select_from(MaintenanceRecord)) or 0)
    if mcount == 0:
        db.add(
            MaintenanceRecord(
                vehicle_id=first_vehicle.id,
                service_date=date.today() - timedelta(days=10),
                category="保养",
                amount=Decimal("1280.50"),
                mileage=max(0, first_vehicle.mileage - 200),
                vendor="集团定点维修厂",
                description="演示：更换机油机滤，全车检查",
                created_by=uid,
            )
        )
        did_any = True

    if int(db.scalar(select(func.count()).select_from(FuelCard)) or 0) == 0:
        db.add(
            FuelCard(
                card_no=_DEMO_FUEL_CARD,
                col_c="演示类别",
                col_d=first_vehicle.plate_number,
            )
        )
        did_any = True

    if int(db.scalar(select(func.count()).select_from(FuelBalance)) or 0) == 0:
        db.add(
            FuelBalance(
                card_no=_DEMO_BALANCE_CARD,
                workshop="演示车间",
                vehicle_no=first_vehicle.plate_number,
                amount=Decimal("1200.00"),
                reserve_fund=Decimal("300.00"),
                total=Decimal("1500.00"),
            )
        )
        did_any = True

    if int(db.scalar(select(func.count()).select_from(FuelRecord)) or 0) == 0:
        db.add(
            FuelRecord(
                card_asn=_DEMO_FUEL_CARD,
                car_no=first_vehicle.plate_number,
                occur_time=datetime.now(timezone.utc) - timedelta(days=3),
                volumn=Decimal("45.00"),
                amount=Decimal("355.05"),
                balance=Decimal("12000.00"),
                workshop="演示车间",
                org_name="演示单位",
                gift_name="",
            )
        )
        did_any = True

    if did_any:
        db.commit()


def _ensure_user(
    db: Session,
    username: str,
    password: str,
    display_name: str,
    role: str,
    *,
    reset_password: bool = False,
) -> User | None:
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        changed = False
        if existing.role != role:
            existing.role = role
            changed = True
        if existing.display_name != display_name:
            existing.display_name = display_name
            changed = True
        if reset_password and password:
            existing.password_hash = hash_password(password)
            changed = True
        if changed:
            db.commit()
        return existing
    if not password:
        return None
    u = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def collect_workshop_names(db: Session) -> list[str]:
    """车间总表标准名称列表。"""
    rows = db.scalars(
        select(Workshop.name).where(Workshop.is_active.is_(True)).order_by(Workshop.sort_order.asc())
    ).all()
    return list(rows) if rows else list(CANONICAL_WORKSHOP_NAMES)


def seed_workshop_admin_accounts(
    db: Session,
    *,
    password: str = "hebgwd_123",
    reset_password: bool = False,
) -> list[str]:
    """
    为每个车间创建 workshop_admin 账号。
    返回本次新建的用户名列表（已存在且未重置密码的不计入）。
    """
    from app.core.roles import WORKSHOP_ADMIN

    created: list[str] = []
    for workshop_name in collect_workshop_names(db):
        ws = get_or_create_workshop(db, workshop_name)
        if not ws:
            continue
        account = workshop_admin_account_name(ws.name)
        existed = db.scalar(select(User).where(User.username == account)) is not None
        user = _ensure_user(
            db,
            account,
            password,
            account,
            WORKSHOP_ADMIN,
            reset_password=reset_password,
        )
        if user:
            user.workshop_id = ws.id
            db.commit()
        if not existed:
            created.append(account)
    return created


def seed_standard_accounts(db: Session) -> None:
    """演示账号：车管 / 驾驶员 / 普通用户（密码均满足复杂度要求）。"""
    _ensure_user(db, "fleet_mgr", "FleetMgr123!@#", "车队管理员", "section_admin")
    _ensure_user(db, "driver1", "DriverUsr123!@#", "驾驶员张三", "vehicle_driver")
    _ensure_user(db, "staff1", "StaffUsr123!@#", "普通用户", "vehicle_driver")


def link_demo_driver_accounts(db: Session) -> None:
    """将演示驾驶员“张三”绑定到 driver1 账号，便于驾驶员角色体验派车任务。"""
    u = db.scalar(select(User).where(User.username == "driver1"))
    d = db.scalar(select(Driver).where(Driver.phone == _DEMO_PHONE_ZHANG))
    if u and d and d.user_id is None:
        d.user_id = u.id
        db.commit()


_NAV_PRESET_SEED: list[tuple[str, float, float]] = [
    ("哈尔滨工务段", 126.57466, 45.706031),
    ("哈双路", 126.5836, 45.6891),
    ("京哈高速1235公里725米作业门", 126.539952, 45.657708),
]


def seed_nav_presets_if_empty(db: Session) -> None:
    """段内导航预设点：表为空时写入与前端默认一致的演示数据。"""
    count = int(db.scalar(select(func.count()).select_from(NavPreset)) or 0)
    if count > 0:
        return
    for order, (name, lng, lat) in enumerate(_NAV_PRESET_SEED):
        db.add(NavPreset(sort_order=order, name=name, lng=lng, lat=lat, is_locked=True))
    db.commit()


def seed_maintenance_terms_if_empty(db: Session) -> None:
    """维修词条：表为空时导入预置三级分类。"""
    from app.services.maintenance_term_service import seed_preset_if_empty

    created, skipped = seed_preset_if_empty(db, force=False)
    if not skipped:
        db.commit()

