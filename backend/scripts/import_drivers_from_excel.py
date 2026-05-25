"""从 Excel 导入驾驶员到 bus_driver。

支持两种 Sheet1 格式（按表头自动识别）：
- 6 列：车间、姓名、状态、准驾车型、电话号码、身份证号
- 5 列：车间、姓名、状态、准驾车型或身份证号、电话号码

默认文件：仓库 `data/导入系统驾驶员名单.xlsx`

在 backend 目录执行：
    python scripts/import_drivers_from_excel.py
    python scripts/import_drivers_from_excel.py --file /path/to/档案.xlsx
    python scripts/import_drivers_from_excel.py --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from openpyxl import load_workbook
from sqlalchemy import delete, func, select, update

from app import models  # noqa: F401
from app.data.workshop_canonical import resolve_canonical_workshop_name
from app.db.migrate import run_runtime_migrations
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.driver import Driver
from app.models.trip_request import TripRequest
from app.models.workshop import Workshop
from app.services.workshop_service import ensure_canonical_workshop_master, get_or_create_workshop

DEFAULT_XLSX = _root.parent / "data" / "导入系统驾驶员名单.xlsx"

EMPLOYMENT_STATUSES = frozenset({"本单位", "外包"})


@dataclass
class DriverRow:
    sort_no: int
    workshop_raw: str
    name: str
    status: str
    license_type: str
    id_card: str | None
    phone: str | None


def _norm_status(raw: str) -> str:
    t = (raw or "").strip()
    if t in EMPLOYMENT_STATUSES:
        return t
    if "外包" in t:
        return "外包"
    return "本单位"


def _norm_id_card(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).strip().upper().replace(" ", "")
    return s or None


def _looks_like_id_card(raw: str) -> bool:
    s = str(raw or "").strip().upper().replace(" ", "")
    if re.fullmatch(r"\d{15}(\d{2}[\dX])?", s):
        return True
    # 档案中偶发 19 位纯数字（录入多一位），仍归入身份证号
    return bool(s.isdigit() and len(s) >= 15)


def _parse_col_d(raw) -> tuple[str, str | None]:
    """旧版 5 列：D 列多数为准驾车型，少数外包人员为身份证号。"""
    s = str(raw or "").strip()
    if not s or s in {"#N/A", "None"}:
        return "", None
    if _looks_like_id_card(s):
        return "", _norm_id_card(s)
    return s, None


def _norm_license(raw) -> str:
    s = str(raw or "").strip()
    if not s or s in {"#N/A", "None"}:
        return ""
    if _looks_like_id_card(s):
        return ""
    return s


def _norm_phone(raw) -> str | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        s = str(int(raw))
    else:
        s = str(raw).strip()
        if s in {"#N/A", "None"}:
            return None
    digits = re.sub(r"\D", "", s)
    return digits if len(digits) >= 3 else None


def _placeholder_phone(sort_no: int) -> str:
    return f"199{sort_no:08d}"[-11:]  # 无电话列时的占位号


def load_rows(path: Path) -> list[DriverRow]:
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        if "Sheet1" not in wb.sheetnames:
            raise ValueError(f"未找到 Sheet1，当前工作表：{wb.sheetnames}")
        ws = wb["Sheet1"]
        out: list[DriverRow] = []
        sort_no = 0
        has_id_col = False
        for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
            cells = list(row) + [None, None, None, None, None, None]
            if i == 1:
                header = [str(c or "").strip() for c in cells]
                has_id_col = "身份证号" in header
                continue
            workshop_raw = str(cells[0] or "").strip()
            name = str(cells[1] or "").strip()
            status_raw = str(cells[2] or "").strip()
            if has_id_col:
                license_type = _norm_license(cells[3])
                phone = _norm_phone(cells[4])
                id_card = _norm_id_card(cells[5])
            else:
                license_type, id_card = _parse_col_d(cells[3])
                phone = _norm_phone(cells[4])
            if not name:
                continue
            sort_no += 1
            out.append(
                DriverRow(
                    sort_no=sort_no,
                    workshop_raw=workshop_raw,
                    name=name,
                    status=_norm_status(status_raw),
                    license_type=license_type,
                    id_card=id_card,
                    phone=phone,
                )
            )
        return out
    finally:
        wb.close()


def _workshop_id_map(db) -> dict[str, int]:
    ensure_canonical_workshop_master(db)
    rows = db.scalars(select(Workshop).where(Workshop.is_active.is_(True))).all()
    return {w.name: w.id for w in rows}


def import_drivers(path: Path, *, dry_run: bool = False, fresh: bool = False) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"找不到 Excel 文件：{path}")

    rows = load_rows(path)
    if not rows:
        print("Excel 中无驾驶员数据行。")
        return

    db = SessionLocal()
    try:
        ws_map = _workshop_id_map(db)
        inserted = updated = skipped = 0
        errors: list[str] = []

        if fresh:
            old_n = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
            if dry_run:
                print(f"[试运行] --fresh 将清空现有 {old_n} 条驾驶员后重新导入 {len(rows)} 条")
            else:
                db.execute(update(TripRequest).where(TripRequest.driver_id.isnot(None)).values(driver_id=None))
                db.execute(delete(Driver))
                db.flush()
                print(f"已清空原驾驶员 {old_n} 条（用车申请中的 driver_id 已置空）。")

        for r in rows:
            canon_ws = resolve_canonical_workshop_name(r.workshop_raw)
            ws_id = ws_map.get(canon_ws)
            if not ws_id:
                ws = get_or_create_workshop(db, canon_ws)
                if ws:
                    ws_id = ws.id
                    ws_map[canon_ws] = ws_id
            if not ws_id:
                errors.append(f"#{r.sort_no} {r.name}：无法解析车间「{r.workshop_raw}」")
                skipped += 1
                continue

            existing = None
            if not fresh:
                existing = db.scalar(
                    select(Driver).where(Driver.name == r.name, Driver.workshop_id == ws_id)
                )
                if not existing:
                    by_name = list(db.scalars(select(Driver).where(Driver.name == r.name)).all())
                    if len(by_name) == 1:
                        existing = by_name[0]
            phone = r.phone or _placeholder_phone(r.sort_no)
            if existing:
                if dry_run:
                    updated += 1
                    continue
                existing.sort_no = r.sort_no
                existing.status = r.status
                existing.workshop_id = ws_id
                existing.license_type = r.license_type
                if r.id_card:
                    existing.id_card = r.id_card
                elif existing.id_card and not _looks_like_id_card(existing.id_card):
                    existing.id_card = None
                if r.phone:
                    existing.phone = r.phone
                elif not existing.phone or re.match(r"^199\d{8}$", existing.phone):
                    existing.phone = phone
                updated += 1
            else:
                if dry_run:
                    inserted += 1
                    continue
                db.add(
                    Driver(
                        sort_no=r.sort_no,
                        name=r.name,
                        phone=phone,
                        license_type=r.license_type,
                        vehicle_type_label="",
                        status=r.status,
                        id_card=r.id_card,
                        workshop_id=ws_id,
                    )
                )
                inserted += 1

        if dry_run:
            print(f"[试运行] 将新增 {inserted} 条，更新 {updated} 条，跳过 {skipped} 条（共读取 {len(rows)} 条）")
        else:
            db.commit()
            total = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
            print(f"导入完成：新增 {inserted} 条，更新 {updated} 条，跳过 {skipped} 条。")
            print(f"Excel 共 {len(rows)} 条，当前库内驾驶员 {total} 条。")

        if errors:
            print("以下行未导入：")
            for e in errors[:20]:
                print(" ", e)
            if len(errors) > 20:
                print(f"  … 另有 {len(errors) - 20} 条")

        # Sheet2/3 无车辆数据提示
        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            for sn in wb.sheetnames:
                if sn == "Sheet1":
                    continue
                ws = wb[sn]
                if (ws.max_row or 0) <= 1:
                    print(f"提示：工作表「{sn}」无车辆数据，本次仅导入驾驶员。")
        finally:
            wb.close()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="从 Excel 导入驾驶员档案")
    ap.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_XLSX,
        help="Excel 路径（默认：项目根目录下同名文件）",
    )
    ap.add_argument("--dry-run", action="store_true", help="只统计不写入数据库")
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="清空 bus_driver 后按 Excel 全量导入（推荐首次对齐档案）",
    )
    args = ap.parse_args()

    Base.metadata.create_all(bind=engine)
    run_runtime_migrations()
    import_drivers(args.file.resolve(), dry_run=args.dry_run, fresh=args.fresh)


if __name__ == "__main__":
    main()
