from fastapi import APIRouter

from app.api.v1 import auth, dashboard, drivers, fuel, maintenance, nav_presets, reports, trip_requests, users, vehicles

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(vehicles.router)
api_router.include_router(drivers.router)
api_router.include_router(trip_requests.router)
api_router.include_router(maintenance.router)
api_router.include_router(fuel.router)
api_router.include_router(reports.router)
api_router.include_router(nav_presets.router)
