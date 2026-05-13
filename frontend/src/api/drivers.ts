import { http } from '@/api/http'
import type { Driver } from '@/api/types'

export type DriverListResponse = {
  items: Driver[]
  total: number
}

export type DriverFilters = {
  statuses: string[]
  license_types: string[]
}

export type DriverStats = {
  total: number
  by_status: Record<string, number>
  by_license_type: Record<string, number>
  /** bus_driver.vehicle_type_label 聚合 */
  by_vehicle_type_label: Record<string, number>
}

export async function listDrivers(params?: {
  q?: string
  skip?: number
  limit?: number
  status?: string
  license_type?: string
}): Promise<DriverListResponse> {
  const { data } = await http.get<DriverListResponse>('/drivers', { params })
  return data
}

export async function getDriverFilters(): Promise<DriverFilters> {
  const { data } = await http.get<DriverFilters>('/drivers/filters')
  return data
}

export async function getDriverStats(): Promise<DriverStats> {
  const { data } = await http.get<DriverStats>('/drivers/stats')
  return data
}

export async function createDriver(payload: Record<string, unknown>): Promise<Driver> {
  const { data } = await http.post<Driver>('/drivers', payload)
  return data
}

export async function updateDriver(id: number, payload: Record<string, unknown>): Promise<Driver> {
  const { data } = await http.patch<Driver>(`/drivers/${id}`, payload)
  return data
}

export async function deleteDriver(id: number): Promise<void> {
  await http.delete(`/drivers/${id}`)
}
