#!/usr/bin/env python3
"""将开发库 bus_system_test 复制到生产库（覆盖生产数据）。

默认迁移全部业务表。加 --exclude-nav 时保留生产库中的段内导航数据
（bus_nav_preset、bus_nav_preset_op_log 不覆盖）。

用法（内网）：
    export DEV_DATABASE_URL="postgresql://postgres:***@bus-system-postgresql.ns-1ht608x0.svc:5432/bus_system_test"
    export PROD_DATABASE_URL="postgresql://postgres:***@test-db-postgresql.ns-1ht608x0.svc:5432/bus_system_test"
    python scripts/migrate_dev_db_to_prod.py
    python scripts/migrate_dev_db_to_prod.py --exclude-nav
"""
from __future__ import annotations

import argparse
import sys
from io import StringIO
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import os

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine

from app.db.base import Base

import app.models  # noqa: F401

NAV_TABLES = frozenset({"bus_nav_preset", "bus_nav_preset_op_log"})

def _require_dsn(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise SystemExit(f"请设置环境变量 {name}（postgresql://.../bus_system_test）")
    return val.replace("postgresql+psycopg2://", "postgresql://", 1)


DEV_DSN = _require_dsn("DEV_DATABASE_URL")
PROD_DSN = _require_dsn("PROD_DATABASE_URL")
PROD_SQLALCHEMY = PROD_DSN.replace("postgresql://", "postgresql+psycopg2://", 1)


def list_public_tables(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        return [r[0] for r in cur.fetchall()]


def copy_table(src, dst, table: str) -> int:
    buf = StringIO()
    with src.cursor() as sc:
        sc.copy_expert(
            sql.SQL("COPY {} TO STDOUT WITH (FORMAT csv, HEADER true)").format(sql.Identifier(table)),
            buf,
        )
    raw = buf.getvalue()
    with dst.cursor() as dc:
        if not raw.strip():
            return 0
        buf.seek(0)
        dc.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true)").format(sql.Identifier(table)),
            buf,
        )
    return raw.count("\n") - 1 if raw.strip() else 0


def reset_sequences(conn, tables: list[str]) -> None:
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(
                """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass AND i.indisprimary
                """,
                (table,),
            )
            pk_cols = [r[0] for r in cur.fetchall()]
            if len(pk_cols) != 1 or pk_cols[0] != "id":
                continue
            cur.execute(
                sql.SQL("SELECT COALESCE(MAX(id), 1) FROM {}").format(sql.Identifier(table)),
            )
            max_id = cur.fetchone()[0]
            cur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (table,))
            seq = cur.fetchone()[0]
            if seq:
                cur.execute("SELECT setval(%s, %s, true)", (seq, max_id))


def ensure_prod_schema() -> None:
    print("同步生产库表结构（补齐缺失表）…")
    engine = create_engine(PROD_SQLALCHEMY)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


def migrate(*, exclude_nav: bool = False) -> None:
    ensure_prod_schema()
    print("连接开发库与生产库…")
    src = psycopg2.connect(DEV_DSN)
    dst = psycopg2.connect(PROD_DSN)
    src.autocommit = False
    dst.autocommit = False
    try:
        all_tables = list_public_tables(src)
        skip = NAV_TABLES if exclude_nav else frozenset()
        tables = [t for t in all_tables if t not in skip]
        kept = [t for t in all_tables if t in skip]

        print(f"共 {len(all_tables)} 张表，将迁移 {len(tables)} 张")
        if kept:
            print(f"保留生产库不动: {', '.join(kept)}")
        print(f"迁移表: {', '.join(tables)}")

        with dst.cursor() as cur:
            cur.execute("SET session_replication_role = replica")
            if tables:
                cur.execute(
                    sql.SQL("TRUNCATE {} RESTART IDENTITY CASCADE").format(
                        sql.SQL(", ").join(sql.Identifier(t) for t in tables)
                    )
                )

        total_rows = 0
        for table in tables:
            n = copy_table(src, dst, table)
            total_rows += max(n, 0)
            print(f"  ✓ {table}: {n} 行")

        reset_sequences(dst, tables)
        with dst.cursor() as cur:
            cur.execute("SET session_replication_role = DEFAULT")

        dst.commit()
        src.commit()
        print(f"\n完成：已向生产库写入约 {total_rows} 行数据。")
        if kept:
            with dst.cursor() as cur:
                for t in kept:
                    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(t)))
                    print(f"  保留 {t}: {cur.fetchone()[0]} 行（生产库原值）")
    except Exception:
        dst.rollback()
        src.rollback()
        raise
    finally:
        src.close()
        dst.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="开发库 → 生产库数据迁移")
    ap.add_argument(
        "--exclude-nav",
        action="store_true",
        help="不覆盖 bus_nav_preset / bus_nav_preset_op_log（保留生产环境导航数据）",
    )
    args = ap.parse_args()
    migrate(exclude_nav=args.exclude_nav)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"迁移失败: {e}", file=sys.stderr)
        sys.exit(1)
