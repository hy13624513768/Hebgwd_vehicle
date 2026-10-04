#!/usr/bin/env python3
"""将开发库 vehicles（及 workshops 车间主表）同步到生产库。

按车牌号 upsert，保留车辆 id，不影响维修/用车申请等关联表。
车间 workshop_id 按车间名称映射到生产库。

用法（内网，在 backend 目录）：
    export DEV_DATABASE_URL="postgresql://postgres:***@hebgwd-fullstack-db-postgresql.ns-1ht608x0.svc:5432/hebgwd_development"
    export PROD_DATABASE_URL="postgresql://postgres:***@PRODUCTION_DB_HOST:5432/PRODUCTION_DB_NAME"
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
from app.db.structure import POSTGRES_SEARCH_PATH_OPTION

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
        raise SystemExit(f"请设置环境变量 {name}（postgresql://.../DATABASE_NAME）")
    return val.replace("postgresql+psycopg2://", "postgresql://", 1)


def _sqlalchemy_url(dsn: str) -> str:
    return dsn.replace("postgresql://", "postgresql+psycopg2://", 1)


def ensure_prod_schema(prod_dsn: str) -> None:
    prod_engine = create_engine(
        _sqlalchemy_url(prod_dsn),
        connect_args={"options": f"-csearch_path={POSTGRES_SEARCH_PATH_OPTION}"},
    )
    print("同步生产库表结构…")
    old_engine = migrate_mod.engine
    try:
        migrate_mod.engine = prod_engine
        migrate_mod.run_pre_create_migrations()
        Base.metadata.create_all(bind=prod_engine)
        migrate_mod.run_runtime_migrations()
    finally:
        migrate_mod.engine = old_engine
    prod_engine.dispose()


def _fetch_workshops(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cols = ", ".join(WORKSHOP_COLUMNS)
        cur.execute(f"SELECT {cols} FROM workshops ORDER BY sort_order, name")
        return cur.fetchall()


def _fetch_vehicles(conn) -> list[tuple]:
    with conn.cursor() as cur:
        cols = ", ".join(["id", *VEHICLE_COLUMNS])
        cur.execute(f"SELECT {cols} FROM vehicles ORDER BY id")
        return cur.fetchall()


def sync_workshops(src, dst) -> dict[str, int]:
    """按名称 upsert 车间，返回生产库 名称→id 映射。"""
    dev_rows = _fetch_workshops(src)
    name_to_id: dict[str, int] = {}

    with dst.cursor() as cur:
        for row in dev_rows:
            name, code, sort_order, is_active, remarks, created_at, updated_at = row
            cur.execute("SELECT id FROM workshops WHERE name = %s", (name,))
            hit = cur.fetchone()
            if hit:
                wid = hit[0]
                cur.execute(
                    """
                    UPDATE workshops
                    SET code = %s, sort_order = %s, is_active = %s, remarks = %s, updated_at = %s
                    WHERE id = %s
                    """,
                    (code, sort_order, is_active, remarks, updated_at, wid),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO workshops (name, code, sort_order, is_active, remarks, created_at, updated_at)
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
                DELETE FROM workshops
                WHERE name <> ALL(%s)
                  AND id NOT IN (SELECT workshop_id FROM vehicles WHERE workshop_id IS NOT NULL)
                  AND id NOT IN (SELECT workshop_id FROM drivers WHERE workshop_id IS NOT NULL)
                  AND id NOT IN (SELECT workshop_id FROM users WHERE workshop_id IS NOT NULL)
                """,
                (dev_names,),
            )

    return name_to_id


def migrate_vehicles(dev_dsn: str, prod_dsn: str) -> None:
    ensure_prod_schema(prod_dsn)

    options = f"-c search_path={POSTGRES_SEARCH_PATH_OPTION}"
    src = psycopg2.connect(dev_dsn, options=options)
    dst = psycopg2.connect(prod_dsn, options=options)
    src.autocommit = False
    dst.autocommit = False
    try:
        with src.cursor() as sc:
            sc.execute("SELECT COUNT(*) FROM vehicles")
            dev_n = sc.fetchone()[0]
        print(f"开发库车辆 {dev_n} 条，开始同步…")

        # 开发库 车间 id → 名称
        with src.cursor() as sc:
            sc.execute("SELECT id, name FROM workshops")
            dev_ws = {r[0]: r[1] for r in sc.fetchall()}

        prod_ws_by_name = sync_workshops(src, dst)
        print(f"  ✓ workshops: {len(prod_ws_by_name)} 个标准车间")

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
            dc.execute("SELECT plate_number FROM vehicles")
            prod_plates = {r[0] for r in dc.fetchall()}
            dev_plates = {r[0] for r in upsert_rows}

            update_cols = [c for c in VEHICLE_COLUMNS if c != "plate_number"]
            set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
            insert_cols = ", ".join(VEHICLE_COLUMNS)
            execute_values(
                dc,
                f"""
                INSERT INTO vehicles ({insert_cols})
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
                    DELETE FROM vehicles
                    WHERE plate_number = ANY(%s)
                      AND id NOT IN (SELECT vehicle_id FROM maintenance_records WHERE vehicle_id IS NOT NULL)
                      AND id NOT IN (SELECT vehicle_id FROM trip_requests WHERE vehicle_id IS NOT NULL)
                    """,
                    (list(extra_plates),),
                )
                print(f"  已删除生产库多余车辆 {dc.rowcount} 条")

        with dst.cursor() as dc:
            dc.execute("SELECT COUNT(*) FROM vehicles")
            prod_n = dc.fetchone()[0]

        dst.commit()
        src.commit()
        print(f"\n完成：生产库 vehicles 现为 {prod_n} 条（开发库 {dev_n} 条）。")
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
