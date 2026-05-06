import { http } from '@/api/http'
import type { Vehicle } from '@/api/types'

/** 统一登记时间字段：兼容 snake_case / camelCase，避免图表统计读不到日期 */
function normalizeVehicle(raw: Record<string, unknown>): Vehicle {
  const base = raw as unknown as Vehicle
  const regRaw = raw.registered_at ?? raw.registeredAt
  let registered_at: string | null | undefined
  if (regRaw == null || regRaw === '') {
    registered_at = null
  } else if (typeof regRaw === 'string') {
    registered_at = regRaw.trim() || null
  } else if (typeof regRaw === 'number' && Number.isFinite(regRaw)) {
    const d = new Date(regRaw)
    registered_at = Number.isNaN(d.getTime()) ? null : d.toISOString()
  } else {
    registered_at = String(regRaw)
  }
  return { ...base, registered_at }
}

export async function listVehicles(params?: { q?: string; skip?: number; limit?: number }): Promise<Vehicle[]> {
  const { data } = await http.get<Record<string, unknown>[]>('/vehicles', { params })
  if (!Array.isArray(data)) return []
  return data.map(normalizeVehicle)
}

export async function createVehicle(payload: Partial<Vehicle> & { plate_number: string }): Promise<Vehicle> {
  const { data } = await http.post<Vehicle>('/vehicles', payload)
  return data
}

export async function updateVehicle(id: number, payload: Record<string, unknown>): Promise<Vehicle> {
  const { data } = await http.patch<Vehicle>(`/vehicles/${id}`, payload)
  return data
}

export async function deleteVehicle(id: number): Promise<void> {
  await http.delete(`/vehicles/${id}`)
}
