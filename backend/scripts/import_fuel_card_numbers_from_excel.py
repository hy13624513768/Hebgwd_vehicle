"""从 Excel 导入油卡主数据到 bus_fuel_card（B/C/D 列）。

默认文件：D:\\Desktop\\获取油卡余额\\卡号.xlsx
列约定：B=卡号，C、D 原样入库到 bus_fuel_card.col_c / col_d。

用法（在 backend 目录）：
  python scripts/import_fuel_card_numbers_from_excel.py
  python scripts/import_fuel_card_numbers_from_excel.py --file "D:\\path\\卡号.xlsx" --dry-run
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from openpyxl import load_workbook  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.fuel import FuelCard  # noqa: E402

DEFAULT_XLSX = Path(r"D:\Desktop\获取油卡余额\卡号.xlsx")


def cell_str(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return str(v).strip()
    if isinstance(v, int):
        return str(v)
    return str(v).strip()


def normalize_card_no(val) -> str | None:
    """从单元格得到规范卡号字符串；过滤表头与空行。"""
    s = cell_str(val)
    if not s:
        return None
    # 纯数字卡号（允许 Excel 科学计数法已转坏的情况尽量用原字符串）
    if re.fullmatch(r"\d{8,32}", s):
        return s
    return None


def data_start_row(ws) -> int:
    """第 1 行若 B 列不是有效卡号而第 2 行是，则视为表头跳过。"""
    if normalize_card_no(ws.cell(1, 2).value):
        return 1
    if ws.max_row >= 2 and normalize_card_no(ws.cell(2, 2).value):
        return 2
    return 1


def import_excel(path: Path, *, dry_run: bool) -> tuple[int, int, int]:
    if not path.is_file():
        raise SystemExit(f"文件不存在: {path}")

    wb = load_workbook(path, data_only=True)
    try:
        ws = wb.active
        n_num = n_new_card = n_upd_card = 0
        start_row = data_start_row(ws)

        db = SessionLocal()
        try:
            pending_numbers: list[tuple[str, str, str]] = []
            for r in range(start_row, ws.max_row + 1):
                b = ws.cell(r, 2).value
                c = ws.cell(r, 3).value
                d = ws.cell(r, 4).value
                cn = normalize_card_no(b)
                if not cn:
                    continue
                col_c = cell_str(c)
                col_d = cell_str(d)
                pending_numbers.append((cn, col_c, col_d))

            if dry_run:
                print(f"dry-run：将处理 {len(pending_numbers)} 条卡号记录（不写库）")
                return len(pending_numbers), 0, 0

            for cn, col_c, col_d in pending_numbers:
                fc = db.scalar(select(FuelCard).where(FuelCard.card_no == cn))
                if fc:
                    fc.col_c = col_c
                    fc.col_d = col_d
                    n_upd_card += 1
                else:
                    db.add(
                        FuelCard(
                            card_no=cn,
                            col_c=col_c,
                            col_d=col_d,
                        )
                    )
                    n_new_card += 1
                n_num += 1

            db.commit()
            return n_num, n_new_card, n_upd_card
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    finally:
        wb.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="导入 Excel B/C/D 列到 bus_fuel_card")
    ap.add_argument("--file", type=Path, default=DEFAULT_XLSX, help="xlsx 路径")
    ap.add_argument("--dry-run", action="store_true", help="只统计行数，不写库")
    args = ap.parse_args()

    n_num, n_new, n_upd = import_excel(args.file, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"完成：bus_fuel_card 写入/更新 {n_num} 条")
        print(f"  bus_fuel_card：新建 {n_new} 条，更新 {n_upd} 条")


if __name__ == "__main__":
    main()
