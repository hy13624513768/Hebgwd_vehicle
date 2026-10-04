#!/usr/bin/env python3
"""将本地 SQLite 开发库完整复制到 PostgreSQL 生产库。

迁移在单个 PostgreSQL 事务中完成：任一表复制或校验失败都会整体回滚。
用户密码哈希按原值复制，不会降级为明文存储。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app import models  # noqa: F401,E402
from app.db.base import Base  # noqa: E402
from app.db.structure import POSTGRES_SEARCH_PATH_OPTION, TABLE_SCHEMAS  # noqa: E402


def _require_prod_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value or value.startswith("sqlite"):
        raise SystemExit("DATABASE_URL 必须指向 PostgreSQL 生产库")
    return value


def _ordered_business_tables(source_names: set[str]) -> list[str]:
    known = set(TABLE_SCHEMAS)
    unknown = sorted(source_names - known)
    if unknown:
        raise RuntimeError(f"SQLite 存在未纳入业务结构的表: {', '.join(unknown)}")
    ordered = [table.name for table in Base.metadata.sorted_tables if table.name in source_names]
    missing = sorted(source_names - set(ordered))
    if missing:
        raise RuntimeError(f"无法确定表依赖顺序: {', '.join(missing)}")
    return ordered


def _quote_table_list(conn, names: list[str]) -> str:
    preparer = conn.dialect.identifier_preparer
    return ", ".join(preparer.quote(name) for name in names)


def migrate(sqlite_path: Path, *, batch_size: int = 500) -> dict[str, int]:
    if not sqlite_path.is_file():
        raise FileNotFoundError(sqlite_path)

    source = create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    target = create_engine(
        _require_prod_url(),
        connect_args={"options": f"-csearch_path={POSTGRES_SEARCH_PATH_OPTION}"},
        pool_pre_ping=True,
    )
    source_inspector = inspect(source)
    source_names = set(source_inspector.get_table_names())
    ordered = _ordered_business_tables(source_names)
    source_meta = MetaData()
    source_tables = {
        name: Table(name, source_meta, autoload_with=source) for name in ordered
    }

    expected: dict[str, int] = {}
    with source.connect() as src:
        for name in ordered:
            expected[name] = int(src.scalar(select(text("count(*)")).select_from(source_tables[name])) or 0)

    with target.begin() as dst:
        dst.execute(text("SET LOCAL statement_timeout = 0"))
        target_inspector = inspect(dst)
        missing_tables = [name for name in ordered if not target_inspector.has_table(name)]
        if missing_tables:
            raise RuntimeError(f"生产库缺少表: {', '.join(missing_tables)}")

        target_meta = MetaData()
        target_tables = {name: Table(name, target_meta, autoload_with=dst) for name in ordered}
        for name in ordered:
            src_cols = set(source_tables[name].columns.keys())
            dst_cols = set(target_tables[name].columns.keys())
            extra = sorted(src_cols - dst_cols)
            if extra:
                raise RuntimeError(f"{name} 的开发库列在生产库不存在: {', '.join(extra)}")

        dst.execute(text("SET LOCAL session_replication_role = replica"))
        if ordered:
            dst.execute(text(f"TRUNCATE {_quote_table_list(dst, ordered)} RESTART IDENTITY CASCADE"))

        with source.connect() as src:
            for name in ordered:
                source_table = source_tables[name]
                target_table = target_tables[name]
                common = [column.name for column in source_table.columns if column.name in target_table.columns]
                result = src.execute(select(*(source_table.c[column] for column in common)))
                copied = 0
                while rows := result.mappings().fetchmany(batch_size):
                    dst.execute(target_table.insert(), [dict(row) for row in rows])
                    copied += len(rows)
                if copied != expected[name]:
                    raise RuntimeError(f"{name} 复制数量异常: {copied} != {expected[name]}")
                print(f"COPY {name}: {copied}")

        for name in ordered:
            if "id" not in target_tables[name].columns:
                continue
            sequence = dst.scalar(text("SELECT pg_get_serial_sequence(:table_name, 'id')"), {"table_name": name})
            if sequence:
                maximum = int(dst.scalar(text(f'SELECT COALESCE(MAX(id), 0) FROM "{name}"')) or 0)
                if maximum:
                    dst.execute(text("SELECT setval(:sequence, :value, true)"), {"sequence": sequence, "value": maximum})
                else:
                    dst.execute(text("SELECT setval(:sequence, 1, false)"), {"sequence": sequence})

        dst.execute(text("SET LOCAL session_replication_role = DEFAULT"))
        for name in ordered:
            actual = int(dst.scalar(text(f'SELECT COUNT(*) FROM "{name}"')) or 0)
            if actual != expected[name]:
                raise RuntimeError(f"{name} 生产校验失败: {actual} != {expected[name]}")

    source.dispose()
    target.dispose()
    return expected


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite 开发库全量迁移到 PostgreSQL 生产库")
    parser.add_argument("sqlite_path", type=Path)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    counts = migrate(args.sqlite_path.resolve(), batch_size=args.batch_size)
    print(f"MIGRATION_OK tables={len(counts)} rows={sum(counts.values())}")


if __name__ == "__main__":
    main()
