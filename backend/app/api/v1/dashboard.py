from fastapi import APIRouter
from sqlalchemy import and_, func, or_, select

from app.core.deps import CurrentUser, DbSession
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
from app.services.trip_acl import driver_id_for_user, trips_query_filtered

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: DbSession, current: CurrentUser) -> DashboardSummary:
    vehicles_total = int(db.scalar(select(func.count()).select_from(Vehicle)) or 0)
    drivers_total = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
    maintenance_records_total = int(db.scalar(select(func.count()).select_from(MaintenanceRecord)) or 0)
    # 业务口径：工作台“油卡数量”以余额台账中的卡数为准
    fuel_cards_total = int(db.scalar(select(func.count()).select_from(FuelBalance)) or 0)
    fuel_records_total = int(db.scalar(select(func.count()).select_from(FuelRecord)) or 0)

    if is_fleet_management(current.role):
        trip_requests_total = int(db.scalar(select(func.count()).select_from(TripRequest)) or 0)
        pending_trip_requests = int(
            db.scalar(select(func.count()).select_from(TripRequest).where(TripRequest.status == "pending")) or 0
        )
    elif current.role in (LEGACY_STAFF, "staff"):
        trip_requests_total = int(
            db.scalar(select(func.count()).select_from(TripRequest).where(TripRequest.created_by == current.id)) or 0
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
            trip_requests_total = int(db.scalar(select(func.count()).select_from(TripRequest).where(scope)) or 0)
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
                db.scalar(select(func.count()).select_from(TripRequest).where(TripRequest.created_by == current.id))
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

    # 兼容新旧 FuelRecord 字段，分析失败时降级为空分析，避免影响工作台主卡片统计。
    try:
        fuel_rows = db.scalars(select(FuelRecord).order_by(FuelRecord.id.asc())).all()
        analysis = build_fuel_analysis(fuel_rows, {})
    except Exception:
        analysis = build_fuel_analysis([], {})

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


def build_fuel_analysis(rows: list[FuelRecord], vehicle_map: dict[int, str]) -> FuelAnalysis:
    base = {
        "total_liters": 0.0,
        "total_amount": 0.0,
        "total_mileage": 0.0,
        "records": 0,
        "valid_segments": 0,
        "invalid_segments": 0,
    }
    yearly: dict[int, dict] = {}
    monthly: dict[tuple[int, int], dict] = {}
    quarterly: dict[tuple[int, int], dict] = {}
    vehicle_yearly: dict[tuple[int, int], dict] = {}
    prev_mileage_by_vehicle: dict[int, int] = {}

    for row in rows:
        liters_raw = getattr(row, "liters", None)
        if liters_raw is None:
            liters_raw = getattr(row, "volumn", 0)
        liters = float(liters_raw or 0)
        amount = float(getattr(row, "amount", 0) or 0)

        dt = getattr(row, "transaction_date", None)
        if dt is None:
            dt = getattr(row, "occur_time", None)
        if dt is None:
            continue
        if hasattr(dt, "date"):
            date_obj = dt.date() if hasattr(dt, "hour") else dt
        else:
            continue

        year = date_obj.year
        month = date_obj.month
        quarter = (month - 1) // 3 + 1
        mileage_delta = 0.0

        vehicle_id = int(getattr(row, "vehicle_id", 0) or 0)
        mileage_now = int(getattr(row, "mileage_snapshot", 0) or 0)
        prev = prev_mileage_by_vehicle.get(vehicle_id)
        if prev is not None:
            delta = mileage_now - prev
            if delta > 0:
                mileage_delta = float(delta)
                base["valid_segments"] += 1
            else:
                base["invalid_segments"] += 1
        prev_mileage_by_vehicle[vehicle_id] = mileage_now

        def bump(bucket: dict) -> None:
            bucket["total_liters"] += liters
            bucket["total_amount"] += amount
            bucket["total_mileage"] += mileage_delta
            bucket["records"] += 1

        base["total_liters"] += liters
        base["total_amount"] += amount
        base["total_mileage"] += mileage_delta
        base["records"] += 1

        bump(yearly.setdefault(year, {"total_liters": 0.0, "total_amount": 0.0, "total_mileage": 0.0, "records": 0}))
        bump(
            monthly.setdefault(
                (year, month),
                {"total_liters": 0.0, "total_amount": 0.0, "total_mileage": 0.0, "records": 0},
            )
        )
        bump(
            quarterly.setdefault(
                (year, quarter),
                {"total_liters": 0.0, "total_amount": 0.0, "total_mileage": 0.0, "records": 0},
            )
        )
        bump(
            vehicle_yearly.setdefault(
                (year, vehicle_id),
                {"total_liters": 0.0, "total_amount": 0.0, "total_mileage": 0.0, "records": 0},
            )
        )

    def avg_100km(v: dict) -> float:
        return round(v["total_liters"] * 100 / v["total_mileage"], 2) if v["total_mileage"] > 0 else 0.0

    years = sorted(yearly.keys())
    yearly_stats = [
        FuelYearStat(
            year=year,
            total_liters=round(v["total_liters"], 2),
            total_amount=round(v["total_amount"], 2),
            total_mileage=round(v["total_mileage"], 1),
            avg_l_per_100km=avg_100km(v),
            records=v["records"],
        )
        for year, v in sorted(yearly.items())
    ]
    monthly_stats = [
        FuelMonthStat(
            year=year,
            month=month,
            total_liters=round(v["total_liters"], 2),
            total_amount=round(v["total_amount"], 2),
            total_mileage=round(v["total_mileage"], 1),
            avg_l_per_100km=avg_100km(v),
        )
        for (year, month), v in sorted(monthly.items())
    ]
    quarterly_stats = [
        FuelQuarterStat(
            year=year,
            quarter=quarter,
            total_liters=round(v["total_liters"], 2),
            total_amount=round(v["total_amount"], 2),
            total_mileage=round(v["total_mileage"], 1),
            avg_l_per_100km=avg_100km(v),
        )
        for (year, quarter), v in sorted(quarterly.items())
    ]
    vehicle_stats = [
        FuelVehicleStat(
            year=year,
            vehicle_id=vehicle_id,
            plate_number=vehicle_map.get(vehicle_id, f"#{vehicle_id}"),
            total_liters=round(v["total_liters"], 2),
            total_amount=round(v["total_amount"], 2),
            total_mileage=round(v["total_mileage"], 1),
            avg_l_per_100km=avg_100km(v),
            records=v["records"],
        )
        for (year, vehicle_id), v in sorted(vehicle_yearly.items(), key=lambda item: (item[0][0], -item[1]["total_amount"]))
    ]

    overview = FuelOverview(
        total_liters=round(base["total_liters"], 2),
        total_amount=round(base["total_amount"], 2),
        total_mileage=round(base["total_mileage"], 1),
        avg_l_per_100km=avg_100km(base),
        records=base["records"],
        valid_segments=base["valid_segments"],
        invalid_segments=base["invalid_segments"],
    )

    return FuelAnalysis(
        years=years,
        overview=overview,
        yearly=yearly_stats,
        monthly=monthly_stats,
        quarterly=quarterly_stats,
        vehicles=vehicle_stats,
    )
