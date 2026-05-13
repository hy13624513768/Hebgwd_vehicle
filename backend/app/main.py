from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import bootstrap_admin_if_needed
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.migrate import run_runtime_migrations
from app.db.session import SessionLocal, engine
from app import models  # noqa: F401
from app.services import seed_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_runtime_migrations()
    db = SessionLocal()
    try:
        bootstrap_admin_if_needed(db)
        seed_service.seed_nav_presets_if_empty(db)
        if settings.demo_seeding_enabled:
            seed_service.seed_standard_accounts(db)
            seed_service.seed_demo_if_empty(db)
            seed_service.link_demo_driver_accounts(db)
    finally:
        db.close()
    yield


app = FastAPI(title="哈尔滨工务段汽车管理信息系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}
