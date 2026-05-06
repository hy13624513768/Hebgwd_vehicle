from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FuelYearStat(BaseModel):
    year: int
    total_liters: float
    total_amount: float
    total_mileage: float
    avg_l_per_100km: float
    records: int


class FuelMonthStat(BaseModel):
    year: int
    month: int
    total_liters: float
    total_amount: float
    total_mileage: float
    avg_l_per_100km: float


class FuelQuarterStat(BaseModel):
    year: int
    quarter: int
    total_liters: float
    total_amount: float
    total_mileage: float
    avg_l_per_100km: float


class FuelVehicleStat(BaseModel):
    year: int
    vehicle_id: int
    plate_number: str
    total_liters: float
    total_amount: float
    total_mileage: float
    avg_l_per_100km: float
    records: int


class FuelOverview(BaseModel):
    total_liters: float
    total_amount: float
    total_mileage: float
    avg_l_per_100km: float
    records: int
    valid_segments: int
    invalid_segments: int


class FuelAnalysis(BaseModel):
    years: list[int]
    overview: FuelOverview
    yearly: list[FuelYearStat]
    monthly: list[FuelMonthStat]
    quarterly: list[FuelQuarterStat]
    vehicles: list[FuelVehicleStat]


class DashboardSummary(BaseModel):
    vehicles_total: int
    drivers_total: int
    trip_requests_total: int
    pending_trip_requests: int
    maintenance_records_total: int
    fuel_cards_total: int
    fuel_records_total: int
    fuel_analysis: FuelAnalysis
