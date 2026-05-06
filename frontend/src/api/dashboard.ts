import { http } from '@/api/http'
import type { DashboardSummary } from '@/api/types'

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await http.get<DashboardSummary>('/dashboard/summary')
  return data
}
