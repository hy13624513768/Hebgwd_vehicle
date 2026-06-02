export type Vehicle = {
  id: number
  plate_number: string
  brand: string
  model: string
  vin: string | null
  color: string
  seats: number
  mileage: number
  status: string
  remarks: string | null
  org_unit: string
  workshop_id: number | null
  vehicle_class: string
  vehicle_type_label: string
  history_plate: string
  engine_no: string
  emission_std: string
  displacement: string
  purchase_amount: number | string | null
  /** 机动车注册登记时间（可空）；旧数据或未录入为 null */
  registered_at?: string | null
  created_by: number | null
  created_at: string
  updated_at: string
}

export type Driver = {
  id: number
  sort_no: number | null
  name: string
  phone: string
  license_type: string
  vehicle_type_label: string
  status: string
  id_card: string | null
  health_check_report: string | null
  outsourcing_onboarding: string | null
  first_hire_date: string | null
  workshop_id: number | null
  workshop_name: string | null
  user_id: number | null
  created_by: number | null
  created_at: string
  updated_at: string
}

export type TripRequest = {
  id: number
  purpose: string
  applicant_name: string
  start_at: string
  end_at: string
  origin: string
  destination: string
  passenger_count: number
  status: string
  vehicle_id: number | null
  driver_id: number | null
  notes: string | null
  created_by: number
  created_at: string
  updated_at: string
}

export type MaintenanceRecord = {
  id: number
  vehicle_id: number
  service_date: string
  category: string
  amount: string
  mileage: number
  vendor: string
  description: string | null
  created_by: number
  created_at: string
  updated_at: string
}

export type DashboardSummary = {
  vehicles_total: number
  drivers_total: number
  trip_requests_total: number
  pending_trip_requests: number
  maintenance_records_total: number
  fuel_cards_total: number
  fuel_records_total: number
  fuel_analysis: {
    years: number[]
    overview: {
      total_liters: number
      total_amount: number
      total_mileage: number
      avg_l_per_100km: number
      records: number
      valid_segments: number
      invalid_segments: number
    }
    yearly: Array<{
      year: number
      total_liters: number
      total_amount: number
      total_mileage: number
      avg_l_per_100km: number
      records: number
    }>
    monthly: Array<{
      year: number
      month: number
      total_liters: number
      total_amount: number
      total_mileage: number
      avg_l_per_100km: number
    }>
    quarterly: Array<{
      year: number
      quarter: number
      total_liters: number
      total_amount: number
      total_mileage: number
      avg_l_per_100km: number
    }>
    vehicles: Array<{
      year: number
      vehicle_id: number
      plate_number: string
      total_liters: number
      total_amount: number
      total_mileage: number
      avg_l_per_100km: number
      records: number
    }>
  }
}
