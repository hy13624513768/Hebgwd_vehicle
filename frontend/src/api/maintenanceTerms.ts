import { http } from '@/api/http'

export type MaintenanceTerm = {
  id: number
  parent_id: number | null
  level: 1 | 2 | 3
  code: string
  name: string
  aliases: string[]
  keywords: string[]
  sort_order: number
  is_active: boolean
  standard_hours: string | null
  reference_cost: string | null
  remarks: string | null
}

export type MaintenanceTermTreeNode = MaintenanceTerm & {
  children: MaintenanceTermTreeNode[]
}

export type MaintenanceTermStats = {
  level1: number
  level2: number
  level3: number
  active_terms: number
  total: number
}

export type MaintenanceTermTreeResponse = {
  items: MaintenanceTermTreeNode[]
  stats: MaintenanceTermStats
}

export type MaintenanceTermListResponse = {
  items: MaintenanceTerm[]
  total: number
}

export type MaintenanceTermPayload = {
  parent_id?: number | null
  level: 1 | 2 | 3
  name: string
  code?: string
  aliases?: string[]
  keywords?: string[]
  sort_order?: number
  is_active?: boolean
  standard_hours?: number | null
  reference_cost?: number | null
  remarks?: string | null
}

export async function getMaintenanceTermTree(activeOnly = false): Promise<MaintenanceTermTreeResponse> {
  const { data } = await http.get<MaintenanceTermTreeResponse>('/maintenance-terms/tree', {
    params: { active_only: activeOnly },
  })
  return data
}

export async function listMaintenanceTerms(params?: {
  parent_id?: number
  level?: number
  q?: string
  active_only?: boolean
  skip?: number
  limit?: number
}): Promise<MaintenanceTermListResponse> {
  const { data } = await http.get<MaintenanceTermListResponse>('/maintenance-terms', { params })
  return data
}

export async function createMaintenanceTerm(payload: MaintenanceTermPayload): Promise<MaintenanceTerm> {
  const { data } = await http.post<MaintenanceTerm>('/maintenance-terms', payload)
  return data
}

export async function updateMaintenanceTerm(
  id: number,
  payload: Partial<MaintenanceTermPayload>,
): Promise<MaintenanceTerm> {
  const { data } = await http.patch<MaintenanceTerm>(`/maintenance-terms/${id}`, payload)
  return data
}

export async function deleteMaintenanceTerm(id: number): Promise<void> {
  await http.delete(`/maintenance-terms/${id}`)
}

export async function seedMaintenanceTermsPreset(force = false): Promise<{
  ok: boolean
  created: number
  skipped: boolean
  message: string
}> {
  const { data } = await http.post('/maintenance-terms/seed-preset', null, {
    params: { force },
  })
  return data
}
