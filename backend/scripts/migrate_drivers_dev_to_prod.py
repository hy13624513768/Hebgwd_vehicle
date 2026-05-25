#!/usr/bin/env python3
"""将开发库 bus_driver（及依赖的 bus_workshop）同步到生产库。

用法（内网，在 backend 目录）：
    export DEV_DATABASE_URL="postgresql://postgres:***@bus-system-postgresql.ns-1ht608x0.svc:5432/bus_system_test"
    export PROD_DATABASE_URL="postgresql://postgres:***@test-db-postgresql.ns-1ht608x0.svc:5432/bus_system_test"
    python scripts/migrate_drivers_dev_to_prod.py
"""
from __future__ import annotations

import os
import sys
from io import StringIO
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from sqlalchemy import create_engine, inspect, text

from app import models  # noqa: F401
from app.db.base import Base
from app.db import migrate as migrate_mod

DRIVER_COLUMNS = (
    "sort_no",
    "name",
    "phone",
    "license_type",
    "vehicle_type_label",
    "status",
    "id_card",
    "health_check_report",
    "outsourcing_onboarding",
    "first_hire_date",
    "workshop_id",
    "user_id",
    "created_by",
    "created_at",
    "updated_at",
)


def _require_dsn(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise SystemExit(f"请设置环境变量 {name}（postgresql://.../bus_system_test）")
    return val.replace("postgresql+psycopg2://", "postgresql://", 1)


def _sqlalchemy_url(dsn: str) -> str:
    return dsn.replace("postgresql://", "postgresql+psycopg2://", 1)


def ensure_prod_schema(prod_dsn: str) -> None:
    prod_engine = create_engine(_sqlalchemy_url(prod_dsn))
    print("同步生产库表结构…")
    Base.metadata.create_all(bind=prod_engine)
    old_engine = migrate_mod.engine
    try:
        migrate_mod.engine = prod_engine
        migrate_mod.run_runtime_migrations()
    finally:
        migrate_mod.engine = old_engine
    prod_engine.dispose()


def copy_table_with_ids(src, dst, table: str) -> int:
    buf = StringIO()
    with src.cursor() as sc:
        sc.copy_expert(
            sql.SQL("COPY {} TO STDOUT WITH (FORMAT csv, HEADER true)").format(sql.Identifier(table)),
            buf,
        )
    raw = buf.getvalue()
    if not raw.strip():
        return 0
    buf.seek(0)
    with dst.cursor() as dc:
        dc.execute(
            sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(sql.Identifier(table))
        )
        dc.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true)").format(sql.Identifier(table)),
            buf,
        )
    return raw.count("\n") - 1


def reset_sequence(conn, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT COALESCE(MAX(id), 1) FROM {}").format(sql.Identifier(table)),
        )
        max_id = cur.fetchone()[0]
        cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
        seq = cur.fetchone()[0]
        if seq:
            cur.execute("SELECT setval(%s, %s, true)", (seq, max_id))


def migrate_drivers(dev_dsn: str, prod_dsn: str) -> None:
    ensure_prod_schema(prod_dsn)

    src = psycopg2.connect(dev_dsn)
    dst = psycopg2.connect(prod_dsn)
    src.autocommit = False
    dst.autocommit = False
    try:
        with src.cursor() as sc:
            sc.execute("SELECT COUNT(*) FROM bus_driver")
            dev_n = sc.fetchone()[0]
        print(f"开发库驾驶员 {dev_n} 条，开始同步…")

        with dst.cursor() as dc:
            if inspect(create_engine(_sqlalchemy_url(prod_dsn))).has_table("bus_trip_request"):
                dc.execute("UPDATE bus_trip_request SET driver_id = NULL WHERE driver_id IS NOT NULL")
            dc.execute("TRUNCATE bus_driver RESTART IDENTITY CASCADE")

        ws_n = copy_table_with_ids(src, dst, "bus_workshop")
        print(f"  ✓ bus_workshop: {ws_n} 行")

        with src.cursor() as sc:
            cols = ", ".join(DRIVER_COLUMNS)
            sc.execute(f"SELECT {cols} FROM bus_driver ORDER BY sort_no ASC NULLS LAST, id ASC")
            rows = sc.fetchall()

        insert_cols = ", ".join(DRIVER_COLUMNS)
        with dst.cursor() as dc:
            execute_values(
                dc,
                f"INSERT INTO bus_driver ({insert_cols}) VALUES %s",
                rows,
                page_size=200,
            )

        reset_sequence(dst, "bus_driver")
        dst.commit()
        src.commit()

        with dst.cursor() as dc:
            dc.execute("SELECT COUNT(*) FROM bus_driver")
            prod_n = dc.fetchone()[0]
        print(f"\n完成：生产库 bus_driver 现为 {prod_n} 条（开发库 {dev_n} 条）。")
    except Exception:
        dst.rollback()
        src.rollback()
        raise
    finally:
        src.close()
        dst.close()


def main() -> None:
    dev_dsn = _require_dsn("DEV_DATABASE_URL")
    prod_dsn = _require_dsn("PROD_DATABASE_URL")
    migrate_drivers(dev_dsn, prod_dsn)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"迁移失败: {e}", file=sys.stderr)
        sys.exit(1)
