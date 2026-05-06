from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.deps import DbSession
from app.core.rbac import ExporterUser
from app.models.driver import Driver
from app.models.fuel import FuelCard, FuelRecord
from app.models.maintenance import MaintenanceRecord
from app.models.trip_request import TripRequest
from app.models.vehicle import Vehicle

router = APIRouter(prefix="/reports", tags=["reports"])


def _csv_bytes(rows: list[list[object]], header: list[str]) -> bytes:
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def _attachment(name: str, data: bytes) -> StreamingResponse:
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/export/vehicles.csv")
def export_vehicles(db: DbSession, _: ExporterUser) -> StreamingResponse:
    rows_db = db.scalars(select(Vehicle).order_by(Vehicle.id)).all()
    header = ["id", "plate_number", "brand", "model", "vin", "color", "seats", "mileage", "status", "remarks"]
    rows = [
        [
            v.id,
            v.plate_number,
            v.brand,
            v.model,
            v.vin or "",
            v.color,
            v.seats,
            v.mileage,
            v.status,
            (v.remarks or "").replace("\n", " "),
        ]
        for v in rows_db
    ]
    return _attachment("vehicles.csv", _csv_bytes(rows, header))


@router.get("/export/drivers.csv")
def export_drivers(db: DbSession, _: ExporterUser) -> StreamingResponse:
    rows_db = db.scalars(select(Driver).order_by(Driver.sort_no.asc().nulls_last(), Driver.id.asc())).all()
    header = [
        "id",
        "sort_no",
        "name",
        "phone",
        "license_type",
        "status",
        "id_card",
        "health_check_report",
        "outsourcing_onboarding",
        "first_hire_date",
        "user_id",
    ]
    rows = [
        [
            d.id,
            d.sort_no if d.sort_no is not None else "",
            d.name,
            d.phone,
            d.license_type,
            d.status,
            d.id_card or "",
            (d.health_check_report or "").replace("\n", " "),
            (d.outsourcing_onboarding or "").replace("\n", " "),
            d.first_hire_date.isoformat() if d.first_hire_date else "",
            d.user_id or "",
        ]
        for d in rows_db
    ]
    return _attachment("drivers.csv", _csv_bytes(rows, header))


@router.get("/export/trip-requests.csv")
def export_trips(db: DbSession, _: ExporterUser) -> StreamingResponse:
    rows_db = db.scalars(select(TripRequest).order_by(TripRequest.id)).all()
    header = [
        "id",
        "purpose",
        "applicant_name",
        "start_at",
        "end_at",
        "origin",
        "destination",
        "passenger_count",
        "status",
        "vehicle_id",
        "driver_id",
        "created_by",
        "notes",
    ]
    rows = [
        [
            t.id,
            t.purpose,
            t.applicant_name,
            t.start_at.isoformat(),
            t.end_at.isoformat(),
            t.origin,
            t.destination,
            t.passenger_count,
            t.status,
            t.vehicle_id or "",
            t.driver_id or "",
            t.created_by,
            (t.notes or "").replace("\n", " "),
        ]
        for t in rows_db
    ]
    return _attachment("trip_requests.csv", _csv_bytes(rows, header))


@router.get("/export/maintenance.csv")
def export_maintenance(db: DbSession, _: ExporterUser) -> StreamingResponse:
    rows_db = db.scalars(select(MaintenanceRecord).order_by(MaintenanceRecord.id)).all()
    header = ["id", "vehicle_id", "service_date", "category", "amount", "mileage", "vendor", "description"]
    rows = [
        [
            m.id,
            m.vehicle_id,
            m.service_date.isoformat(),
            m.category,
            str(m.amount),
            m.mileage,
            m.vendor,
            (m.description or "").replace("\n", " "),
        ]
        for m in rows_db
    ]
    return _attachment("maintenance.csv", _csv_bytes(rows, header))


@router.get("/export/fuel-cards.csv")
def export_fuel_cards(db: DbSession, _: ExporterUser) -> StreamingResponse:
    rows_db = db.scalars(select(FuelCard).order_by(FuelCard.id)).all()
    header = ["id", "card_no", "col_c", "col_d"]
    rows = [[c.id, c.card_no, c.col_c, c.col_d] for c in rows_db]
    return _attachment("fuel_cards.csv", _csv_bytes(rows, header))


@router.get("/export/fuel-records.csv")
def export_fuel_records(db: DbSession, _: ExporterUser) -> StreamingResponse:
    rows_db = db.scalars(select(FuelRecord).order_by(FuelRecord.id)).all()
    header = [
        "id",
        "card_asn",
        "car_no",
        "occur_time",
        "volumn",
        "amount",
        "workshop",
        "org_name",
        "gift_name",
        "balance",
    ]
    rows = [
        [
            r.id,
            r.card_asn,
            r.car_no,
            r.occur_time.isoformat(),
            str(r.volumn),
            str(r.amount),
            r.workshop,
            r.org_name,
            r.gift_name,
            str(r.balance),
        ]
        for r in rows_db
    ]
    return _attachment("fuel_records.csv", _csv_bytes(rows, header))


@router.get("/export/summary.csv")
def export_summary(db: DbSession, _: ExporterUser) -> StreamingResponse:
    """一行汇总，便于领导快速浏览。"""
    now = datetime.now().isoformat(timespec="seconds")
    v = int(db.scalar(select(func.count()).select_from(Vehicle)) or 0)
    d = int(db.scalar(select(func.count()).select_from(Driver)) or 0)
    t = int(db.scalar(select(func.count()).select_from(TripRequest)) or 0)
    m = int(db.scalar(select(func.count()).select_from(MaintenanceRecord)) or 0)
    fc = int(db.scalar(select(func.count()).select_from(FuelCard)) or 0)
    fr = int(db.scalar(select(func.count()).select_from(FuelRecord)) or 0)
    header = ["exported_at", "vehicles", "drivers", "trips", "maintenance", "fuel_cards", "fuel_records"]
    rows = [[now, v, d, t, m, fc, fr]]
    return _attachment("summary.csv", _csv_bytes(rows, header))