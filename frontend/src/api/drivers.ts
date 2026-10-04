import { http } from '@/api/http'
import type { Driver } from '@/api/types'

export type DriverListResponse = {
  items: Driver[]
  total: number
}

export type DriverFilters = {
  workshops: string[]
  license_types: string[]
}

export type DriverStats = {
  total: number
  by_workshop: Record<string, number>
  by_license_type: Record<string, number>
  by_employment_status: Record<string, number>
  by_age_group: Record<string, number>
}

export async function listDrivers(params?: {
  q?: string
  skip?: number
  limit?: number
  workshop?: string
  license_type?: string
}): Promise<DriverListResponse> {
  const { data } = await http.get<DriverListResponse>('/drivers', { params })
  return data
}

export type DriverDocumentKind = 'health_check_report' | 'outsourcing_onboarding'

export type DriverDocument = {
  kind: DriverDocumentKind
  original_name: string
  content_type: string
  size_bytes: number
  created_at: string
}

/** 表单下拉需覆盖当前账号有权访问的全部驾驶员，按后端上限逐页获取。 */
export async function listAllDrivers(): Promise<Driver[]> {
  const items: Driver[] = []
  const seen = new Set<number>()
  for (let skip = 0; ; skip += 200) {
    const page = await listDrivers({ skip, limit: 200 })
    for (const driver of page.items) {
      if (!seen.has(driver.id)) {
        seen.add(driver.id)
        items.push(driver)
      }
    }
    if (page.items.length < 200 || items.length >= page.total) return items
  }
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

export async function uploadDriverDocument(
  driverId: number,
  kind: DriverDocumentKind,
  file: File,
): Promise<DriverDocument> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<DriverDocument>(`/drivers/${driverId}/documents/${kind}`, form)
  return data
}

export async function downloadDriverDocument(driverId: number, kind: DriverDocumentKind): Promise<Blob> {
  const { data } = await http.get<Blob>(`/drivers/${driverId}/documents/${kind}`, {
    responseType: 'blob',
  })
  return data
}

export async function deleteDriverDocument(driverId: number, kind: DriverDocumentKind): Promise<void> {
  await http.delete(`/drivers/${driverId}/documents/${kind}`)
}
