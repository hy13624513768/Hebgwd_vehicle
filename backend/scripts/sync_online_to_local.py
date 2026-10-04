"""只读复制 PostgreSQL 开发库到本地 SQLite。

在 backend 目录执行：

    $env:SOURCE_DATABASE_URL = "postgresql+psycopg2://.../hebgwd_development"
    python scripts/sync_online_to_local.py

源库连接串仅从环境变量读取。脚本先生成并校验临时数据库，成功后备份并替换
``data/local-dev.db``，不会修改源库。
"""

from __future__ import annotations

import os
import shutil
import sys
import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, insert, select, text, update

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.structure import POSTGRES_SEARCH_PATH_OPTION
from app import models  # noqa: F401  确保所有 ORM 表注册到 Base.metadata
from app.core.config import settings
from app.core.security import hash_password


DATA_DIR = ROOT / "data"
TARGET_PATH = DATA_DIR / "local-dev.db"
TEMP_PATH = DATA_DIR / "local-dev.syncing.db"


def _source_url() -> str:
    value = os.environ.get("SOURCE_DATABASE_URL", "").strip()
    if not value:
        raise SystemExit("请通过 SOURCE_DATABASE_URL 提供线上 PostgreSQL 连接串。")
    if not value.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise SystemExit("SOURCE_DATABASE_URL 必须是 PostgreSQL 连接串。")
    return value.replace("postgresql://", "postgresql+psycopg2://", 1)


def _backup_existing() -> Path | None:
    if not TARGET_PATH.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DATA_DIR / f"local-dev.before-sync-{stamp}.db"
    shutil.copy2(TARGET_PATH, backup)
    return backup


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="复制线上 PostgreSQL 到本地 SQLite")
    parser.add_argument(
        "--reset-local-admin",
        action="store_true",
        help="仅在本地副本中把管理员密码重置为 backend/.env 的 BOOTSTRAP_ADMIN_PASSWORD",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if TEMP_PATH.exists():
        TEMP_PATH.unlink()

    source_engine = create_engine(
        _source_url(),
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={POSTGRES_SEARCH_PATH_OPTION}"},
    )
    target_engine = create_engine(f"sqlite:///{TEMP_PATH.as_posix()}")
    copied: dict[str, int] = {}

    try:
        Base.metadata.create_all(target_engine)
        source_meta = MetaData()

        with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
            source_conn.execute(text("SET TRANSACTION READ ONLY"))
            target_conn.execute(text("PRAGMA foreign_keys=OFF"))

            for target_table in Base.metadata.sorted_tables:
                source_table = Table(target_table.name, source_meta, autoload_with=source_conn)
                target_columns = {column.name for column in target_table.columns}
                rows = []
                statement = select(source_table)
                if source_table.primary_key.columns:
                    statement = statement.order_by(*source_table.primary_key.columns)
                for source_row in source_conn.execute(statement).mappings():
                    rows.append({key: value for key, value in source_row.items() if key in target_columns})
                if rows:
                    target_conn.execute(insert(target_table), rows)
                copied[target_table.name] = len(rows)

            if args.reset_local_admin:
                user_table = Base.metadata.tables["users"]
                result = target_conn.execute(
                    update(user_table)
                    .where(user_table.c.username == settings.bootstrap_admin_username)
                    .values(
                        password_hash=hash_password(settings.bootstrap_admin_password),
                        failed_attempts=0,
                        lock_until=None,
                        is_active=True,
                    )
                )
                if result.rowcount != 1:
                    raise RuntimeError("源库中未找到配置的管理员账号，无法重置本地密码")

            violations = target_conn.execute(text("PRAGMA foreign_key_check")).all()
            if violations:
                sample = ", ".join(str(row) for row in violations[:5])
                raise RuntimeError(f"本地数据库外键校验失败：{sample}")

        target_engine.dispose()
        backup = _backup_existing()
        TEMP_PATH.replace(TARGET_PATH)

        print(f"copied_tables={len(copied)}")
        print(f"copied_rows={sum(copied.values())}")
        for table, count in copied.items():
            print(f"{table}={count}")
        if backup:
            print(f"backup={backup.name}")
        print(f"local_admin_reset={args.reset_local_admin}")
        print(f"target={TARGET_PATH}")
    finally:
        source_engine.dispose()
        target_engine.dispose()
        if TEMP_PATH.exists():
            TEMP_PATH.unlink()


if __name__ == "__main__":
    main()
