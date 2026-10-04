#!/usr/bin/env python3
"""只读核对 SQLite→PostgreSQL 全量迁移结果。"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.db.structure import POSTGRES_SEARCH_PATH_OPTION, TABLE_SCHEMAS  # noqa: E402


def main() -> None:
    source_path = Path(sys.argv[1]).resolve()
    source = create_engine(f"sqlite:///{source_path.as_posix()}")
    target = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"options": f"-csearch_path={POSTGRES_SEARCH_PATH_OPTION}"},
    )
    source_inspector = inspect(source)
    names = sorted(source_inspector.get_table_names())
    source_meta = MetaData()
    target_meta = MetaData()

    with source.connect() as src, target.connect() as dst:
        for name in names:
            source_table = Table(name, source_meta, autoload_with=src)
            target_table = Table(name, target_meta, autoload_with=dst)
            source_count = int(src.scalar(select(text("count(*)")).select_from(source_table)) or 0)
            target_count = int(dst.scalar(select(text("count(*)")).select_from(target_table)) or 0)
            if source_count != target_count:
                raise RuntimeError(f"COUNT_MISMATCH {name}: {source_count} != {target_count}")

            pk = source_inspector.get_pk_constraint(name).get("constrained_columns") or []
            if pk:
                source_keys = set(src.execute(select(*(source_table.c[column] for column in pk))).all())
                target_keys = set(dst.execute(select(*(target_table.c[column] for column in pk))).all())
                if source_keys != target_keys:
                    raise RuntimeError(f"PRIMARY_KEY_MISMATCH {name}")
            print(f"VERIFY {name}: {source_count}")

        local_users = src.execute(text("SELECT username, password_hash FROM users ORDER BY username")).all()
        prod_users = dst.execute(text("SELECT username, password_hash FROM users ORDER BY username")).all()
        if local_users != prod_users:
            raise RuntimeError("USER_PASSWORD_HASH_MISMATCH")
        digest = hashlib.sha256(
            "\n".join(f"{username}\0{password_hash}" for username, password_hash in local_users).encode()
        ).hexdigest()
        print(f"USER_PASSWORD_HASHES_OK count={len(local_users)} digest={digest}")

        orphan_total = 0
        target_inspector = inspect(dst)
        quote = dst.dialect.identifier_preparer.quote
        for table_name in names:
            for fk in target_inspector.get_foreign_keys(table_name):
                local_cols = fk.get("constrained_columns") or []
                remote_cols = fk.get("referred_columns") or []
                remote_table = fk.get("referred_table")
                if not local_cols or len(local_cols) != len(remote_cols) or not remote_table:
                    continue
                join = " AND ".join(
                    f"p.{quote(remote)} = c.{quote(local)}"
                    for local, remote in zip(local_cols, remote_cols)
                )
                present = " AND ".join(f"c.{quote(local)} IS NOT NULL" for local in local_cols)
                sql = text(
                    f"SELECT COUNT(*) FROM {quote(table_name)} c "
                    f"WHERE {present} AND NOT EXISTS "
                    f"(SELECT 1 FROM {quote(remote_table)} p WHERE {join})"
                )
                orphan_total += int(dst.scalar(sql) or 0)
        if orphan_total:
            raise RuntimeError(f"FOREIGN_KEY_ORPHANS={orphan_total}")
        print("FOREIGN_KEYS_OK orphans=0")

    source.dispose()
    target.dispose()
    print("VERIFICATION_OK")


if __name__ == "__main__":
    main()
