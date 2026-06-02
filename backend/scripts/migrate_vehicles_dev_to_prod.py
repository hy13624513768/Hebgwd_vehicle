#!/usr/bin/env python3
"""将开发库 bus_vehicle（及 bus_workshop 车间主表）同步到生产库。

按车牌号 upsert，保留车辆 id，不影响维修/用车申请等关联表。
车间 workshop_id 按车间名称映射到生产库。

用法（内网，在 backend 目录）：
    export DEV_DATABASE_URL="postgresql://postgres:***@bus-system-postgresql.ns-1ht608x0.svc:5432/bus_system_test"
    export PROD_DATABASE_URL="postgresql://postgres:***@test-db-postgresql.ns-1ht608x0.svc:5432/bus_system_test"
    python scripts/migrate_vehicles_dev_to_prod.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from sqlalchemy import create_engine

from app import models  # noqa: F401
from app.db.base import Base
from app.db import migrate as migrate_mod

WORKSHOP_COLUMNS = ("name", "code", "sort_order", "is_active", "remarks", "created_at", "updated_at")

VEHICLE_COLUMNS = (
    "plate_number",
    "brand",
    "model",
    "vin",
    "color",
    "seats",
    "mileage",
    "status",
    "remarks",
    "org_unit",
    "workshop_id",
    "vehicle_class",
    "vehicle_type_label",
    "history_plate",
    "engine_no",
    "emission_std",
    "displacement",
    "purchase_amount",
    "registered_at",
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


def _fetch_workshops(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cols = ", ".join(WORKSHOP_COLUMNS)
        cur.execute(f"SELECT {cols} FROM bus_workshop ORDER BY sort_order, name")
        return cur.fetchall()


def _fetch_vehicles(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cols = ", ".join(["id", *VEHICLE_COLUMNS])
        cur.execute(f"SELECT {cols} FROM bus_vehicle ORDER BY id")
        return cur.fetchall()


def sync_workshops(src, dst) -> dict[str, int]:
    """按名称 upsert 车间，返回生产库 名称→id 映射。"""
    dev_rows = _fetch_workshops(src)
    name_to_id: dict[str, int] = {}

    with dst.cursor() as cur:
        for row in dev_rows:
            name, code, sort_order, is_active, remarks, created_at, updated_at = row
            cur.execute("SELECT id FROM bus_workshop WHERE name = %s", (name,))
            hit = cur.fetchone()
            if hit:
                wid = hit[0]
                cur.execute(
                    """
                    UPDATE bus_workshop
                    SET code = %s, sort_order = %s, is_active = %s, remarks = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (code, sort_order, is_active, remarks, updated_at, wid),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO bus_workshop (name, code, sort_order, is_active, remarks, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, code, sort_order, is_active, remarks, created_at, updated_at),
                )
                wid = cur.fetchone()[0]
            name_to_id[name] = wid

        dev_names = list(name_to_id.keys())
        if dev_names:
            cur.execute(
                """
                DELETE FROM bus_workshop
                WHERE name <> ALL(%s)
                  AND id NOT IN (SELECT workshop_id FROM bus_vehicle WHERE workshop_id IS NOT NULL)
                  AND id NOT IN (SELECT workshop_id FROM bus_driver WHERE workshop_id IS NOT NULL)
                  AND id NOT IN (SELECT workshop_id FROM sys_user WHERE workshop_id IS NOT NULL)
                """,
                (dev_names,),
            )

    return name_to_id


def migrate_vehicles(dev_dsn: str, prod_dsn: str) -> None:
    ensure_prod_schema(prod_dsn)

    src = psycopg2.connect(dev_dsn)
    dst = psycopg2.connect(prod_dsn)
    src.autocommit = False
    dst.autocommit = False
    try:
        with src.cursor() as sc:
            sc.execute("SELECT COUNT(*) FROM bus_vehicle")
            dev_n = sc.fetchone()[0]
        print(f"开发库车辆 {dev_n} 条，开始同步…")

        # 开发库 车间 id → 名称
        with src.cursor() as sc:
            sc.execute("SELECT id, name FROM bus_workshop")
            dev_ws = {r[0]: r[1] for r in sc.fetchall()}

        prod_ws_by_name = sync_workshops(src, dst)
        print(f"  ✓ bus_workshop: {len(prod_ws_by_name)} 个标准车间")

        dev_vehicles = _fetch_vehicles(src)
        upsert_rows: list[tuple] = []
        for row in dev_vehicles:
            vid, *fields = row
            data = dict(zip(VEHICLE_COLUMNS, fields))
            dev_ws_id = data["workshop_id"]
            ws_name = dev_ws.get(dev_ws_id, data["org_unit"] or "")
            prod_ws_id = prod_ws_by_name.get(ws_name)
            data["workshop_id"] = prod_ws_id
            data["org_unit"] = ws_name or data["org_unit"]
            upsert_rows.append(tuple(data[c] for c in VEHICLE_COLUMNS))

        with dst.cursor() as dc:
            dc.execute("SELECT plate_number FROM bus_vehicle")
            prod_plates = {r[0] for r in dc.fetchall()}
            dev_plates = {r[0] for r in upsert_rows}

            update_cols = [c for c in VEHICLE_COLUMNS if c != "plate_number"]
            set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
            insert_cols = ", ".join(VEHICLE_COLUMNS)
            execute_values(
                dc,
                f"""
                INSERT INTO bus_vehicle ({insert_cols})
                VALUES %s
                ON CONFLICT (plate_number) DO UPDATE SET {set_clause}
                """,
                upsert_rows,
                page_size=100,
            )

            extra_plates = prod_plates - dev_plates
            if extra_plates:
                dc.execute(
                    """
                    DELETE FROM bus_vehicle
                    WHERE plate_number = ANY(%s)
                      AND id NOT IN (SELECT vehicle_id FROM bus_maintenance WHERE vehicle_id IS NOT NULL)
                      AND id NOT IN (SELECT vehicle_id FROM bus_trip_request WHERE vehicle_id IS NOT NULL)
                    """,
                    (list(extra_plates),),
                )
                print(f"  已删除生产库多余车辆 {dc.rowcount} 条")

        with dst.cursor() as dc:
            dc.execute("SELECT COUNT(*) FROM bus_vehicle")
            prod_n = dc.fetchone()[0]

        dst.commit()
        src.commit()
        print(f"\n完成：生产库 bus_vehicle 现为 {prod_n} 条（开发库 {dev_n} 条）。")
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
    migrate_vehicles(dev_dsn, prod_dsn)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"迁移失败: {e}", file=sys.stderr)
        sys.exit(1)
