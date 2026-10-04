from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.bootstrap import initialize_database
from app.db.session import engine
from app.services.media_storage_service import assert_storage_ready


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_db_init:
        initialize_database()
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="哈尔滨工务段汽车管理信息系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"status": "ok", "environment": settings.environment, "health": "/health", "api": "/api/v1"}


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready")
def ready():
    """就绪检查：确认应用进程可以访问数据库。"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        assert_storage_ready()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database or media storage unavailable",
        ) from exc
    return {"status": "ready", "environment": settings.environment}
