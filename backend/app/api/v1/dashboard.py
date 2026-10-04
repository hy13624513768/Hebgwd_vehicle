from fastapi import APIRouter
from sqlalchemy import Integer, and_, cast, func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.core.data_scope import scoped
from app.core.roles import LEGACY_DRIVER, LEGACY_STAFF, VEHICLE_DRIVER, is_fleet_management
from app.models.driver import Driver
from app.models.fuel import FuelBalance, FuelRecord
from app.models.maintenance import MaintenanceRecord
from app.models.trip_request import TripRequest
from app.models.vehicle import Vehicle
from app.schemas.dashboard import (
    DashboardSummary,
    FuelAnalysis,
    FuelMonthStat,
    FuelOverview,
    FuelQuarterStat,
    FuelVehicleStat,
    FuelYearStat,
)
from app.services.fuel_analysis_service import build_fuel_analysis
from app.services.trip_acl import driver_id_for_user, trips_query_filtered

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: DbSession, current: CurrentUser) -> DashboardSummary:
    # 工作台基础总览是全段统一口径：所有已登录账号均可查看车辆、驾驶员总数。
    # 仅放开聚合数字，车辆/驾驶员明细及其他业务统计仍按原数据范围控制。
    vehicles_total = int(db.scalar(select(func.count()).select_from(Vehicle)) or 0)
    drivers_total = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
    maintenance_records_total = int(db.scalar(scoped(select(func.count()).select_from(MaintenanceRecord), MaintenanceRecord, current)) or 0)
    # 业务口径：工作台“油卡数量”以余额台账中的卡数为准
    fuel_cards_total = int(db.scalar(scoped(select(func.count()).select_from(FuelBalance), FuelBalance, current)) or 0)
    fuel_records_total = int(db.scalar(scoped(select(func.count()).select_from(FuelRecord), FuelRecord, current)) or 0)

    if is_fleet_management(current.role):
        trip_requests_total = int(db.scalar(scoped(select(func.count()).select_from(TripRequest), TripRequest, current)) or 0)
        pending_trip_requests = int(
            db.scalar(scoped(select(func.count()).select_from(TripRequest), TripRequest, current).where(TripRequest.status == "pending")) or 0
        )
    elif current.role in (LEGACY_STAFF, "staff"):
        trip_requests_total = int(
            db.scalar(scoped(select(func.count()).select_from(TripRequest), TripRequest, current).where(TripRequest.created_by == current.id)) or 0
        )
        pending_trip_requests = int(
            db.scalar(
                select(func.count())
                .select_from(TripRequest)
                .where(and_(TripRequest.created_by == current.id, TripRequest.status == "pending"))
            )
            or 0
        )
    elif current.role in (VEHICLE_DRIVER, LEGACY_DRIVER, "driver"):
        did = driver_id_for_user(db, current.id)
        if did:
            scope = or_(TripRequest.driver_id == did, TripRequest.created_by == current.id)
            trip_requests_total = int(db.scalar(scoped(select(func.count()).select_from(TripRequest), TripRequest, current).where(scope)) or 0)
            pending_trip_requests = int(
                db.scalar(
                    select(func.count())
                    .select_from(TripRequest)
                    .where(and_(scope, TripRequest.status == "pending"))
                )
                or 0
            )
        else:
            trip_requests_total = int(
                db.scalar(scoped(select(func.count()).select_from(TripRequest), TripRequest, current).where(TripRequest.created_by == current.id))
                or 0
            )
            pending_trip_requests = int(
                db.scalar(
                    select(func.count())
                    .select_from(TripRequest)
                    .where(
                        and_(TripRequest.created_by == current.id, TripRequest.status == "pending"),
                    )
                )
                or 0
            )
    else:
        trip_requests_total = 0
        pending_trip_requests = 0

    fuel_year = cast(func.extract("year", FuelRecord.occur_time), Integer).label("year")
    fuel_month = cast(func.extract("month", FuelRecord.occur_time), Integer).label("month")
    fuel_query = select(
        fuel_year,
        fuel_month,
        FuelRecord.car_no,
        FuelRecord.card_asn,
        func.sum(FuelRecord.volumn).label("volumn"),
        func.sum(FuelRecord.amount).label("amount"),
        func.count().label("record_count"),
    )
    fuel_rows = db.execute(
        scoped(fuel_query, FuelRecord, current)
        .group_by(fuel_year, fuel_month, FuelRecord.car_no, FuelRecord.card_asn)
        .order_by(fuel_year.asc(), fuel_month.asc())
    ).all()
    vehicle_map = dict(db.execute(scoped(select(Vehicle.id, Vehicle.plate_number), Vehicle, current)).all())
    analysis = build_fuel_analysis(fuel_rows, vehicle_map)

    return DashboardSummary(
        vehicles_total=vehicles_total,
        drivers_total=drivers_total,
        trip_requests_total=trip_requests_total,
        pending_trip_requests=pending_trip_requests,
        maintenance_records_total=maintenance_records_total,
        fuel_cards_total=fuel_cards_total,
        fuel_records_total=fuel_records_total,
        fuel_analysis=analysis,
    )
