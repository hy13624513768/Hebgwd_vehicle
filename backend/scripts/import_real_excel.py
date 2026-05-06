"""
从本地 Excel 台账批量导入初始业务数据（车辆/油卡/加油/维保/费用）。

默认目录：C:\\Users\\HY\\Desktop\\数据
文件按文件名关键词分类（UTF-8）：保险、燃油、停车/过路、年检/审验、维修/维保、明细(公务用车)。

用法（在 backend 目录）：
  python scripts/import_real_excel.py --clear
  python scripts/import_real_excel.py --dir "D:\\data" --dry-run
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.driver import Driver  # noqa: E402
from app.models.fuel import FuelCard, FuelRecord  # noqa: E402
from app.models.maintenance import MaintenanceRecord  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.vehicle import Vehicle  # noqa: E402


def classify_file(path: Path) -> str:
    n = path.name
    if "保险" in n:
        return "insurance"
    if "燃油" in n or "油费" in n:
        return "fuel"
    if "停车" in n or "过路" in n:
        return "parking"
    if "年检" in n or "审验" in n:
        return "inspection"
    if "维修" in n or "维保" in n:
        return "maintenance"
    if "明细" in n:
        return "vehicles"
    return "unknown"


def header_row_map(ws, row: int) -> dict[str, int]:
    m: dict[str, int] = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row, c).value
        if v is None:
            continue
        key = str(v).strip()
        if key:
            m[key] = c
    return m


def vehicle_header_map(ws) -> tuple[dict[str, int], int] | tuple[None, None]:
    """车辆明细表的表头可能在第1行或第2行，自动探测。"""
    candidates = ("车牌号", "牌照号", "车号", "号牌号码")
    for r in range(1, min(ws.max_row, 6) + 1):
        h = header_row_map(ws, r)
        if not h:
            continue
        norm_keys = {_norm_header_key(k): k for k in h}
        for key in candidates:
            if key in h or _norm_header_key(key) in norm_keys:
                return h, r
    return None, None


def cell(ws, r: int, h: Mapping[str, int], name: str):
    c = h.get(name)
    if not c:
        return None
    return ws.cell(r, c).value


def norm_plate(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip().upper().replace(" ", "")
    return s or None


def parse_decimal(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    s = str(v).strip().replace(",", "")
    if not s:
        return Decimal("0")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")


def _norm_header_key(s: str) -> str:
    return (
        str(s)
        .strip()
        .replace("\u3000", "")
        .replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
    )


def _parse_registered_at_excel_serial(val: float | int) -> datetime | None:
    """Excel 将日期存为数字序列时（data_only 可能为 float）。"""
    try:
        import openpyxl.utils.datetime as xl_dt
    except ImportError:
        return None
    try:
        num = float(val)
        if not math.isfinite(num):
            return None
        conv = xl_dt.from_excel(num)
    except Exception:
        return None
    if isinstance(conv, datetime):
        if conv.tzinfo is None:
            return conv.replace(tzinfo=timezone.utc)
        return conv.astimezone(timezone.utc)
    if isinstance(conv, date):
        return datetime(conv.year, conv.month, conv.day, tzinfo=timezone.utc)
    return None


def parse_registered_at(val) -> datetime | None:
    """Excel 注册登记时间：单元格可为 datetime / date / 字符串 / 序列号。"""
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day, tzinfo=timezone.utc)
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        dt = _parse_registered_at_excel_serial(val)
        if dt is not None:
            return dt
    s = str(val).strip()
    if not s:
        return None
    norm = (
        s.replace("年", "-")
        .replace("月", "-")
        .replace("日", "")
        .replace("/", "-")
        .replace(".", "-")
    )
    head = norm[:10]
    try:
        parts = [p for p in head.split("-")[:3] if p]
        if len(parts) < 3:
            return None
        y, mo, d = (int(parts[0]), int(parts[1]), int(parts[2]))
        return datetime(y, mo, d, tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def reg_time_header_key(h: Mapping[str, int]) -> str | None:
    explicit = (
        "注册登记时间",
        "注册登记日期",
        "注册日期",
        "登记日期",
        "机动车注册日期",
        "机动车登记日期",
        "车辆注册日期",
        "车辆登记日期",
        "行驶证注册日期",
        "行驶证登记日期",
        "注册时间",
        "登记时间",
        "初次登记日期",
        "初次登记时间",
    )
    for key in explicit:
        if key in h:
            return key
    norm_to_orig = {_norm_header_key(k): k for k in h}
    for cand in explicit:
        cn = _norm_header_key(cand)
        if cn in norm_to_orig:
            return norm_to_orig[cn]
    for k in h.keys():
        kn = _norm_header_key(k)
        if len(kn) < 4:
            continue
        if ("注册" in kn or "登记" in kn) and ("日期" in kn or "时间" in kn):
            return k
    return None


def reg_time_value(ws, r: int, h: Mapping[str, int], rk: str | None):
    """优先用匹配列；未命中时按用户台账固定取 O 列（第 15 列）。"""
    if rk:
        return cell(ws, r, h, rk)
    return ws.cell(r, 15).value


def parse_int(v, default: int = 0) -> int:
    if v is None or v == "":
        return default
    if isinstance(v, int):
        return v
    try:
        return int(float(str(v).strip()))
    except ValueError:
        return default


def parse_seats_from_spec(v) -> int:
    if v is None:
        return 5
    s = str(v)
    m = re.search(r"(\d+)\s*座", s)
    if m:
        return max(1, min(60, int(m.group(1))))
    m2 = re.search(r"(\d+)", s)
    if m2:
        return max(1, min(60, int(m2.group(1))))
    return 5


def to_date(v) -> date:
    if v is None:
        return date.today()
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def to_dt_utc(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        dt = v
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[: len(fmt) + 5], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def clear_business_tables(db: Session) -> None:
    db.execute(
        text(
            "TRUNCATE TABLE "
            "bus_fuel_record, bus_maintenance, bus_trip_request, "
            "bus_fuel_card, bus_driver, bus_vehicle "
            "RESTART IDENTITY CASCADE"
        )
    )
    db.commit()


def get_admin_id(db: Session) -> int:
    u = db.query(User).filter(User.username == "admin").first()
    if not u:
        raise SystemExit("数据库中不存在 admin 用户，请先启动过后端完成初始化。")
    return u.id


def import_vehicles(db: Session, path: Path, uid: int, dry: bool) -> int:
    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    h, header_row = vehicle_header_map(ws)
    if not h:
        print(f"  跳过（未识别到车辆表头）: {path.name}")
        return 0
    plate_key = (
        "车牌号"
        if "车牌号" in h
        else ("牌照号" if "牌照号" in h else ("车号" if "车号" in h else "号牌号码"))
    )
    n = 0
    seen: set[str] = set()
    for r in range((header_row or 2) + 1, ws.max_row + 1):
        plate = norm_plate(cell(ws, r, h, plate_key))
        if not plate or plate in seen:
            continue
        seen.add(plate)
        org = str(cell(ws, r, h, "使用单位") or "").strip()
        vcls = str(cell(ws, r, h, "种类") or "").strip()
        vtype = str(cell(ws, r, h, "车辆类型") or "").strip()
        hist = str(cell(ws, r, h, "历史车牌号") or "").strip()
        brand = str(cell(ws, r, h, "车辆品牌") or "").strip()
        model = str(cell(ws, r, h, "车辆型号") or "").strip()
        vin = str(cell(ws, r, h, "车架号") or "").strip() or None
        engine = str(cell(ws, r, h, "发动机号") or "").strip()
        emission = str(cell(ws, r, h, "排放标准") or "").strip()
        disp = str(cell(ws, r, h, "排量") or "").strip()
        spec = cell(ws, r, h, "车辆规格")
        seats = parse_seats_from_spec(spec)
        purchase = parse_decimal(cell(ws, r, h, "购车发票金额"))
        if purchase == 0:
            purchase_dec: Decimal | None = None
        else:
            purchase_dec = purchase

        rk = reg_time_header_key(h)
        registered_at = parse_registered_at(reg_time_value(ws, r, h, rk))

        row = Vehicle(
            plate_number=plate,
            brand=brand or "—",
            model=model or "—",
            vin=vin,
            color="",
            seats=seats,
            mileage=0,
            status="active",
            remarks=None,
            org_unit=org,
            vehicle_class=vcls,
            vehicle_type_label=vtype,
            history_plate=hist,
            engine_no=engine,
            emission_std=emission,
            displacement=disp,
            purchase_amount=purchase_dec,
            registered_at=registered_at,
            created_by=uid,
        )
        if not dry:
            db.add(row)
        n += 1
    if not dry:
        db.flush()
    print(f"  车辆档案: {n} 条 ← {path.name}（表头行：{header_row}）")
    return n


def backfill_vehicle_registered_at(db: Session, path: Path, dry: bool) -> int:
    """已为在库车辆按车牌补写 registered_at（不新增车辆）。"""
    wb = load_workbook(path, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]
        h, header_row = vehicle_header_map(ws)
        if not h:
            print(f"  跳过补全（未识别到车辆表头）: {path.name}")
            return 0
        plate_key = (
            "车牌号"
            if "车牌号" in h
            else ("牌照号" if "牌照号" in h else ("车号" if "车号" in h else "号牌号码"))
        )
        rk = reg_time_header_key(h)
        n = 0
        for r in range((header_row or 2) + 1, ws.max_row + 1):
            plate = norm_plate(cell(ws, r, h, plate_key))
            if not plate:
                continue
            reg_dt = parse_registered_at(reg_time_value(ws, r, h, rk))
            if reg_dt is None:
                continue
            v = db.query(Vehicle).filter(Vehicle.plate_number == plate).one_or_none()
            if v is None:
                continue
            if not dry:
                v.registered_at = reg_dt
            n += 1
        print(
            f"  补全注册登记时间: {n} 条 ← {path.name}"
            f"（表头行：{header_row}，列：{rk or 'O(15)'}）"
        )
        return n
    finally:
        wb.close()


def vehicle_id_by_plate(db: Session) -> dict[str, int]:
    return {v.plate_number: v.id for v in db.query(Vehicle).all()}


def ensure_driver(db: Session, name: str, uid: int, cache: dict[str, int], dry: bool) -> int | None:
    name = (name or "").strip()
    if not name or name in ("", "-"):
        return None
    if name in cache:
        return cache[name]
    if dry:
        cache[name] = len(cache) + 1
        return cache[name]
    d = (
        db.query(Driver)
        .filter(Driver.name == name)
        .first()
    )
    if d:
        cache[name] = d.id
        return d.id
    fake_id = 880000 + len(cache)
    d = Driver(
        name=name,
        phone=f"138{fake_id % 10_000_000:07d}",
        id_card=f"IMPORT-{fake_id}",
        license_type="C1",
        status="在岗",
        health_check_report=None,
        outsourcing_onboarding=None,
        first_hire_date=None,
        sort_no=None,
        created_by=uid,
    )
    db.add(d)
    db.flush()
    cache[name] = d.id
    return d.id


def import_inspection(db: Session, path: Path, plates: dict[str, int], uid: int, dry: bool) -> int:
    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    h = header_row_map(ws, 2)
    if "检车单号" not in h or "车牌号" not in h:
        print(f"  跳过: {path.name}")
        return 0
    n = 0
    for r in range(3, ws.max_row + 1):
        plate = norm_plate(cell(ws, r, h, "车牌号"))
        vid = plates.get(plate or "")
        if not vid:
            continue
        oid = str(cell(ws, r, h, "检车单号") or "").strip()
        cat = str(cell(ws, r, h, "检车类型") or "年检").strip() or "年检"
        amt = parse_decimal(cell(ws, r, h, "检车费用金额"))
        st_raw = cell(ws, r, h, "检车时间")
        svc_date = to_date(st_raw)
        vendor = str(cell(ws, r, h, "年检单位") or "").strip()
        agent = str(cell(ws, r, h, "经办人") or "").strip()
        note = str(cell(ws, r, h, "备注") or "").strip()
        desc = f"单号:{oid}"
        if agent:
            desc += f" 经办:{agent}"
        if note:
            desc += f" {note}"
        row = MaintenanceRecord(
            vehicle_id=vid,
            service_date=svc_date,
            category="年检" if "年检" in cat else cat[:32],
            amount=amt,
            mileage=0,
            vendor=vendor[:128],
            description=desc[:2000] if desc else None,
            created_by=uid,
        )
        if not dry:
            db.add(row)
        n += 1
    print(f"  年检/检车: {n} 条 ← {path.name}")
    return n


def import_maintenance(db: Session, path: Path, plates: dict[str, int], uid: int, dry: bool) -> int:
    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    h = header_row_map(ws, 2)
    if "维修单号" not in h:
        print(f"  跳过: {path.name}")
        return 0
    n = 0
    for r in range(3, ws.max_row + 1):
        plate = norm_plate(cell(ws, r, h, "车牌号"))
        vid = plates.get(plate or "")
        if not vid:
            continue
        oid = str(cell(ws, r, h, "维修单号") or "").strip()
        item = str(cell(ws, r, h, "维修项点") or "").strip()
        vendor = str(cell(ws, r, h, "维修厂家") or "").strip()
        mileage = parse_int(cell(ws, r, h, "里程表数"))
        start = cell(ws, r, h, "开始日期")
        svc_date = to_date(start)
        applicant = str(cell(ws, r, h, "申请人") or "").strip()
        dept = str(cell(ws, r, h, "车辆所属部门") or "").strip()
        desc = f"单号:{oid}"
        if item:
            desc += f" {item}"
        if applicant:
            desc += f" 申请:{applicant}"
        if dept:
            desc += f" 部门:{dept}"
        row = MaintenanceRecord(
            vehicle_id=vid,
            service_date=svc_date,
            category="维修",
            amount=Decimal("0"),
            mileage=mileage,
            vendor=vendor[:128],
            description=desc[:2000] if desc else None,
            created_by=uid,
        )
        if not dry:
            db.add(row)
        n += 1
    print(f"  维修保养明细: {n} 条 ← {path.name}")
    return n


def import_insurance(db: Session, path: Path, plates: dict[str, int], uid: int, dry: bool) -> int:
    """原写入 bus_expense；费用登记模块已移除，跳过。"""
    print(f"  跳过（费用登记已移除）: {path.name}")
    return 0


def import_fuel(
    db: Session,
    path: Path,
    plates: dict[str, int],
    uid: int,
    dry: bool,
    card_map: dict[str, int],
    driver_cache: dict[str, int],
) -> int:
    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    h = header_row_map(ws, 2)
    if "油卡号" not in h or "车牌号" not in h:
        print(f"  跳过: {path.name}")
        return 0
    n = 0
    for r in range(3, ws.max_row + 1):
        card_no = str(cell(ws, r, h, "油卡号") or "").strip()
        plate = norm_plate(cell(ws, r, h, "车牌号"))
        vid = plates.get(plate or "")
        if not vid or not card_no:
            continue
        unit = str(cell(ws, r, h, "单位") or "").strip()
        if card_no not in card_map and not dry:
            c = FuelCard(
                card_no=card_no,
                col_c=unit or "—",
                col_d=plate or "—",
            )
            db.add(c)
            db.flush()
            card_map[card_no] = c.id
        elif card_no not in card_map:
            card_map[card_no] = len(card_map) + 1

        cid = card_map[card_no]
        liters = parse_decimal(cell(ws, r, h, "升数"))
        amount = parse_decimal(cell(ws, r, h, "金额"))
        if liters > 0 and amount > 0:
            unit_price = (amount / liters).quantize(Decimal("0.01"))
        else:
            unit_price = Decimal("0")
        t_raw = cell(ws, r, h, "加油时间")
        tdt = to_dt_utc(t_raw)
        tdate = tdt.date() if tdt else to_date(t_raw)
        station = str(cell(ws, r, h, "地点") or "").strip()
        mileage = parse_int(cell(ws, r, h, "里程表数"))
        driver_name = str(cell(ws, r, h, "驾驶员") or "").strip()
        ensure_driver(db, driver_name, uid, driver_cache, dry)
        trip_no = str(cell(ws, r, h, "派车单号") or "").strip()
        oid = str(cell(ws, r, h, "单号") or "").strip()
        notes = f"单号:{oid}"
        if trip_no:
            notes += f" 派车:{trip_no}"
        fr = FuelRecord(
            card_id=cid,
            vehicle_id=vid,
            transaction_date=tdate,
            liters=liters,
            unit_price=unit_price,
            amount=amount,
            station_name=station[:128],
            mileage_snapshot=mileage,
            notes=notes[:2000],
            created_by=uid,
        )
        if not dry:
            db.add(fr)
        n += 1
    print(f"  加油流水: {n} 条 ← {path.name}")
    return n


def import_parking(
    db: Session,
    path: Path,
    plates: dict[str, int],
    uid: int,
    dry: bool,
    driver_cache: dict[str, int],
) -> int:
    """原写入 bus_expense；费用登记模块已移除，跳过。"""
    print(f"  跳过（费用登记已移除）: {path.name}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="从 Excel 导入真实台账数据")
    ap.add_argument(
        "--dir",
        type=Path,
        default=Path(r"C:\Users\HY\Desktop\数据"),
        help="Excel 所在目录",
    )
    ap.add_argument("--clear", action="store_true", help="导入前清空业务表（保留 sys_user）")
    ap.add_argument("--dry-run", action="store_true", help="只解析统计，不写库")
    ap.add_argument(
        "--backfill-registration",
        action="store_true",
        help="仅从公务用车明细 xlsx 为已有车辆补写 registered_at（不新增、不清空；可先 --dry-run 看条数）",
    )
    args = ap.parse_args()

    root: Path = args.dir
    if not root.is_dir():
        raise SystemExit(f"目录不存在: {root}")

    files = sorted(root.glob("*.xlsx"))
    if not files:
        raise SystemExit(f"未找到 xlsx: {root}")

    by_kind: dict[str, list[Path]] = {}
    for p in files:
        k = classify_file(p)
        by_kind.setdefault(k, []).append(p)

    print("识别文件:")
    for k, ps in sorted(by_kind.items()):
        for p in ps:
            print(f"  [{k}] {p.name}")

    db = SessionLocal()
    try:
        if args.backfill_registration:
            if "vehicles" not in by_kind:
                raise SystemExit("未识别到车辆明细类 xlsx（文件名须含「明细」），无法补全登记日期。")
            total = 0
            for p in by_kind["vehicles"]:
                total += backfill_vehicle_registered_at(db, p, args.dry_run)
            if not args.dry_run:
                db.commit()
            mode = "dry-run（未写库）" if args.dry_run else "已提交"
            print(f"完成（{mode}）：补全登记时间 {total} 条。")
            return

        uid = 1 if args.dry_run else get_admin_id(db)
        if args.clear and not args.dry_run:
            print("清空业务表…")
            clear_business_tables(db)

        driver_cache: dict[str, int] = {}
        card_map: dict[str, int] = {}

        if "vehicles" in by_kind:
            for p in by_kind["vehicles"]:
                import_vehicles(db, p, uid, args.dry_run)
            if not args.dry_run:
                db.commit()
        else:
            print("警告: 未识别到「公务用车明细」类文件，车辆表可能为空。")

        plates = vehicle_id_by_plate(db) if not args.dry_run else {}

        if args.dry_run:
            print("dry-run：已统计车辆解析行数；不写库，未导入其它台账。")
            return

        for p in by_kind.get("inspection", []):
            import_inspection(db, p, plates, uid, args.dry_run)
        for p in by_kind.get("maintenance", []):
            import_maintenance(db, p, plates, uid, args.dry_run)
        for p in by_kind.get("insurance", []):
            import_insurance(db, p, plates, uid, args.dry_run)

        for c in db.query(FuelCard).all():
            card_map[c.card_no] = c.id

        for p in by_kind.get("fuel", []):
            import_fuel(db, p, plates, uid, args.dry_run, card_map, driver_cache)
        for p in by_kind.get("parking", []):
            import_parking(db, p, plates, uid, args.dry_run, driver_cache)

        db.commit()
        print("完成：已提交数据库。")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
