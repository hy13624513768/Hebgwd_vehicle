"""手动补全演示基础数据（与启动时 seed_demo_if_empty 逻辑一致）。在 backend 目录下执行：

    python scripts/seed_baseline.py

需已安装项目依赖并配置好数据库连接（.env）。"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.db.session import SessionLocal
from app.services.seed_service import link_demo_driver_accounts, seed_demo_if_empty, seed_standard_accounts


def main() -> None:
    db = SessionLocal()
    try:
        seed_standard_accounts(db)
        seed_demo_if_empty(db)
        link_demo_driver_accounts(db)
        print("baseline seed done")
    finally:
        db.close()


if __name__ == "__main__":
    main()
