from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.structure import POSTGRES_SEARCH_PATH_OPTION

engine_options: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    # FastAPI 的同步依赖可能跨线程使用连接；SQLite 本地开发需要关闭线程检查。
    engine_options["connect_args"] = {"check_same_thread": False}
elif settings.database_url.startswith("postgresql"):
    engine_options.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        pool_use_lifo=True,
    )
    engine_options["connect_args"] = {
        "connect_timeout": settings.database_connect_timeout_seconds,
        "application_name": "hebgwd_vehicle_api",
        "options": (
            f"-csearch_path={POSTGRES_SEARCH_PATH_OPTION} "
            f"-cstatement_timeout={settings.database_statement_timeout_ms} "
            f"-cidle_in_transaction_session_timeout={settings.database_idle_transaction_timeout_ms}"
        ),
    }

engine = create_engine(settings.database_url, **engine_options)


if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
