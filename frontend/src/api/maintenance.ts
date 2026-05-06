import { http } from '@/api/http'
import type { MaintenanceRecord } from '@/api/types'

export async function listMaintenance(params?: {
  vehicle_id?: number
  skip?: number
  limit?: number
}): Promise<MaintenanceRecord[]> {
  const { data } = await http.get<MaintenanceRecord[]>('/maintenance-records', { params })
  return data
}

export async function createMaintenance(payload: Record<string, unknown>): Promise<MaintenanceRecord> {
  const { data } = await http.post<MaintenanceRecord>('/maintenance-records', payload)
  return data
}

export async function updateMaintenance(id: number, payload: Record<string, unknown>): Promise<MaintenanceRecord> {
  const { data } = await http.patch<MaintenanceRecord>(`/maintenance-records/${id}`, payload)
  return data
}

export async function deleteMaintenance(id: number): Promise<void> {
  await http.delete(`/maintenance-records/${id}`)
}
