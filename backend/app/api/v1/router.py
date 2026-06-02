from fastapi import APIRouter

from app.api.v1 import (
    auth,
    dashboard,
    drivers,
    fuel,
    maintenance,
    maintenance_terms,
    nav_presets,
    repair_records,
    reports,
    trip_requests,
    users,
    vehicles,
    workshops,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dashboard.router)
api_router.include_router(vehicles.router)
api_router.include_router(drivers.router)
api_router.include_router(trip_requests.router)
api_router.include_router(maintenance.router)
api_router.include_router(maintenance_terms.router)
api_router.include_router(repair_records.router)
api_router.include_router(fuel.router)
api_router.include_router(reports.router)
api_router.include_router(nav_presets.router)
api_router.include_router(workshops.router)
