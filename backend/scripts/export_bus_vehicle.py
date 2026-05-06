"""导出 public.bus_vehicle 的列信息与全表数据（CSV），供本地查看。

用法（在 backend 目录）：
  python scripts/export_bus_vehicle.py
  python scripts/export_bus_vehicle.py --out exports

依赖：与主项目相同的 database_url（.env 或默认）。
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "exports", help="输出目录")
    args = ap.parse_args()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(settings.database_url)

    schema_path = out_dir / "bus_vehicle_schema.txt"
    csv_path = out_dir / "bus_vehicle_data.csv"

    with engine.connect() as conn:
        cols = conn.execute(
            text(
                """
                SELECT column_name, data_type, character_maximum_length,
                       is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'bus_vehicle'
                ORDER BY ordinal_position
                """
            )
        ).mappings().all()

        lines = [
            f"database_url (masked): {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}",
            "",
            "public.bus_vehicle columns:",
            "column_name | data_type | max_len | nullable | default",
            "-" * 72,
        ]
        for c in cols:
            lines.append(
                f"{c['column_name']} | {c['data_type']} | {c['character_maximum_length']} | "
                f"{c['is_nullable']} | {c['column_default'] or ''}"
            )
        schema_path.write_text("\n".join(lines), encoding="utf-8")

        rows = conn.execute(text("SELECT * FROM public.bus_vehicle ORDER BY id")).mappings().all()
        if not rows:
            csv_path.write_text("", encoding="utf-8")
            print(f"已写入（无数据行）: {schema_path}\n{csv_path}")
            return

        fieldnames = list(rows[0].keys())
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: _cell(r[k]) for k in fieldnames})

    print(f"已写入:\n  {schema_path}\n  {csv_path}\n行数: {len(rows)}")


if __name__ == "__main__":
    main()
