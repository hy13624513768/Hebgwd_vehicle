"""同步车间主表并回填各业务表 workshop_id。在 backend 目录执行：

    python scripts/sync_workshops.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from app.db.base import Base
from app.db.migrate import run_runtime_migrations
from app.db.session import SessionLocal, engine
from app import models  # noqa: F401
from app.services.workshop_service import ensure_canonical_workshop_master


def main() -> None:
    Base.metadata.create_all(bind=engine)
    run_runtime_migrations()
    db = SessionLocal()
    try:
        n = ensure_canonical_workshop_master(db)
        print(f"车间总表已对齐为标准名称，共 {n} 个车间。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
