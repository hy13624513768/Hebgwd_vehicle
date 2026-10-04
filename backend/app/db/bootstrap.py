"""数据库结构与基础数据初始化。

本地开发默认由 FastAPI lifespan 调用；生产环境应设置 AUTO_DB_INIT=false，
并在单独的 Sealos initContainer/Job 中运行 ``python -m app.db.bootstrap``。
"""

from app import models  # noqa: F401
from app.api.v1.auth import bootstrap_admin_if_needed
from app.core.config import settings
from app.db.base import Base
from app.db.migrate import run_pre_create_migrations, run_runtime_migrations
from app.db.session import SessionLocal, engine
from app.services import seed_service
from app.services.workshop_service import sync_workshops_master_and_links


def initialize_database() -> None:
    run_pre_create_migrations()
    Base.metadata.create_all(bind=engine)
    run_runtime_migrations()

    db = SessionLocal()
    try:
        bootstrap_admin_if_needed(db)
        sync_workshops_master_and_links(db)
        seed_service.seed_nav_presets_if_empty(db)
        seed_service.seed_maintenance_terms_if_empty(db)
        if settings.demo_seeding_enabled:
            seed_service.seed_standard_accounts(db)
            seed_service.seed_demo_if_empty(db)
            seed_service.link_demo_driver_accounts(db)
    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
