#!/usr/bin/env python3
"""将开发库 bus_system_test 全量复制到生产库（覆盖生产数据）。"""
from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine

from app.db.base import Base

import app.models  # noqa: F401

# 仅迁移时使用外网地址（日常运行请用集群内网，见 deploy/database.env.example）：
#   set -a && source ../deploy/database.env.example  # 或自行 export
#   export DEV_DATABASE_URL="postgresql://postgres:***@dbconn.sealosbja.site:39754/bus_system_test"
#   export PROD_DATABASE_URL="postgresql://postgres:***@dbconn.sealosbja.site:48528/bus_system_test"
#   python scripts/migrate_dev_db_to_prod.py
import os

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
    if not raw.strip():
        return 0
    buf.seek(0)
    with dst.cursor() as dc:
        dc.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH (FORMAT csv, HEADER true)").format(sql.Identifier(table)),
            buf,
        )
    return raw.count("\n") - 1


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


def main() -> None:
    ensure_prod_schema()
    print("连接开发库与生产库…")
    src = psycopg2.connect(DEV_DSN)
    dst = psycopg2.connect(PROD_DSN)
    src.autocommit = False
    dst.autocommit = False
    try:
        tables = list_public_tables(src)
        print(f"共 {len(tables)} 张表: {', '.join(tables)}")

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
    except Exception:
        dst.rollback()
        src.rollback()
        raise
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"迁移失败: {e}", file=sys.stderr)
        sys.exit(1)
