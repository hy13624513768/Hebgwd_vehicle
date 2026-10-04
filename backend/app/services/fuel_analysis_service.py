"""加油金额/升数聚合；缺失里程时油耗为 null，不推测缺失业务数据。"""
from app.models.fuel import FuelRecord
from app.schemas.dashboard import FuelAnalysis, FuelMonthStat, FuelOverview, FuelQuarterStat, FuelVehicleStat, FuelYearStat


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
    vehicle_yearly: dict[tuple[int, str], dict] = {}
    prev_mileage_by_vehicle: dict[str, int] = {}
    vehicle_id_by_plate = {plate: vehicle_id for vehicle_id, plate in vehicle_map.items()}

    for row in rows:
        liters_raw = getattr(row, "liters", None)
        if liters_raw is None:
            liters_raw = getattr(row, "volumn", 0)
        liters = float(liters_raw or 0)
        amount = float(getattr(row, "amount", 0) or 0)

        dt = getattr(row, "transaction_date", None)
        if dt is None:
            dt = getattr(row, "occur_time", None)
        if dt is not None and hasattr(dt, "date"):
            date_obj = dt.date() if hasattr(dt, "hour") else dt
            year = date_obj.year
            month = date_obj.month
        else:
            year = int(getattr(row, "year", 0) or 0)
            month = int(getattr(row, "month", 0) or 0)
            if year <= 0 or month not in range(1, 13):
                continue
        quarter = (month - 1) // 3 + 1
        mileage_delta = 0.0
        record_count = int(getattr(row, "record_count", 1) or 0)

        vehicle_id = (getattr(row, "car_no", "") or "").strip() or f"未关联车辆（卡 {row.card_asn}）"
        mileage_now = int(getattr(row, "mileage_snapshot", 0) or 0)
        prev = prev_mileage_by_vehicle.get(vehicle_id) if mileage_now > 0 else None
        if prev is not None:
            delta = mileage_now - prev
            if delta > 0:
                mileage_delta = float(delta)
                base["valid_segments"] += 1
            else:
                base["invalid_segments"] += 1
        if mileage_now > 0:
            prev_mileage_by_vehicle[vehicle_id] = mileage_now

        def bump(bucket: dict) -> None:
            bucket["total_liters"] += liters
            bucket["total_amount"] += amount
            bucket["total_mileage"] += mileage_delta
            bucket["records"] += record_count

        base["total_liters"] += liters
        base["total_amount"] += amount
        base["total_mileage"] += mileage_delta
        base["records"] += record_count

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

    def avg_100km(v: dict) -> float | None:
        return round(v["total_liters"] * 100 / v["total_mileage"], 2) if v["total_mileage"] > 0 else None

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
            vehicle_id=vehicle_id_by_plate.get(vehicle_id),
            plate_number=vehicle_id,
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
