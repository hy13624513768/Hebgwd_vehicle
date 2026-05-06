"""从《驾驶员数据库表》Excel 导入 bus_driver。

默认文件：C:\\Users\\HY\\Desktop\\数据\\驾驶员数据库表.xlsx
首行表头：序号、姓名、电话、准驾、状态、身份证号、健康体检报告、外包人员入职手续、首次入职时间

用法：
  python scripts/import_drivers_from_excel.py              # 增量：同手机号则更新
  python scripts/import_drivers_from_excel.py --replace-all  # 清空表（并解除出车单驾驶员引用）后全量导入
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook  # noqa: E402
from sqlalchemy import delete, select, update  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.migrate import run_runtime_migrations  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models.driver import Driver  # noqa: E402
from app.models.trip_request import TripRequest  # noqa: E402

DEFAULT_XLSX = Path(r"C:\Users\HY\Desktop\数据\驾驶员数据库表.xlsx")

HEADER = [
    "序号",
    "姓名",
    "电话",
    "准驾",
    "状态",
    "身份证号",
    "健康体检报告",
    "外包人员入职手续",
    "首次入职时间",
]


def as_text(v: object) -> str:
    if v is None:
        return ""
    return str(v).strip()


def as_int(v: object) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v == int(v) else None
    s = as_text(v)
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_date(v: object) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = as_text(v)
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def run_import(path: Path, *, replace_all: bool, dry_run: bool) -> None:
    if not path.is_file():
        raise SystemExit(f"文件不存在: {path}")

    run_runtime_migrations()
    Base.metadata.create_all(bind=engine)

    wb = load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]

    header = [as_text(ws.cell(1, c).value) for c in range(1, ws.max_column + 1)]
    idx = {name: header.index(name) + 1 for name in HEADER if name in header}
    missing = [x for x in HEADER if x not in idx]
    if missing:
        raise SystemExit(f"缺少列: {missing}，当前表头: {header}")

    rows: list[dict[str, object]] = []
    for r in range(2, ws.max_row + 1):
        name = as_text(ws.cell(r, idx["姓名"]).value)
        phone = as_text(ws.cell(r, idx["电话"]).value)
        if not name and not phone:
            continue
        rows.append(
            {
                "sort_no": as_int(ws.cell(r, idx["序号"]).value),
                "name": name or phone,
                "phone": phone or name,
                "license_type": as_text(ws.cell(r, idx["准驾"]).value),
                "status": as_text(ws.cell(r, idx["状态"]).value),
                "id_card": as_text(ws.cell(r, idx["身份证号"]).value) or None,
                "health_check_report": as_text(ws.cell(r, idx["健康体检报告"]).value) or None,
                "outsourcing_onboarding": as_text(ws.cell(r, idx["外包人员入职手续"]).value) or None,
                "first_hire_date": parse_date(ws.cell(r, idx["首次入职时间"]).value),
            }
        )

    if dry_run:
        print(f"[dry-run] 解析 {len(rows)} 行，replace_all={replace_all}")
        return

    db = SessionLocal()
    try:
        if replace_all:
            db.execute(update(TripRequest).where(TripRequest.driver_id.isnot(None)).values(driver_id=None))
            db.execute(delete(Driver))
            db.commit()

        n_ins = 0
        n_upd = 0
        for row in rows:
            phone = str(row["phone"]).strip()
            name = str(row["name"]).strip()
            existing = db.scalar(select(Driver).where(Driver.phone == phone))
            if existing:
                existing.sort_no = row["sort_no"]  # type: ignore[assignment]
                existing.name = name
                existing.license_type = str(row["license_type"] or "")
                existing.status = str(row["status"] or "")
                existing.id_card = row["id_card"]  # type: ignore[assignment]
                existing.health_check_report = row["health_check_report"]  # type: ignore[assignment]
                existing.outsourcing_onboarding = row["outsourcing_onboarding"]  # type: ignore[assignment]
                existing.first_hire_date = row["first_hire_date"]  # type: ignore[assignment]
                n_upd += 1
            else:
                db.add(
                    Driver(
                        sort_no=row["sort_no"],  # type: ignore[arg-type]
                        name=name,
                        phone=phone,
                        license_type=str(row["license_type"] or ""),
                        status=str(row["status"] or ""),
                        id_card=row["id_card"],  # type: ignore[arg-type]
                        health_check_report=row["health_check_report"],  # type: ignore[arg-type]
                        outsourcing_onboarding=row["outsourcing_onboarding"],  # type: ignore[arg-type]
                        first_hire_date=row["first_hire_date"],  # type: ignore[arg-type]
                    )
                )
                n_ins += 1
        db.commit()
        print(f"完成：新增 {n_ins}，更新 {n_upd}，replace_all={replace_all}")
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx", nargs="?", type=Path, default=DEFAULT_XLSX)
    p.add_argument("--replace-all", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    run_import(args.xlsx, replace_all=args.replace_all, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
