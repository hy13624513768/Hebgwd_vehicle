import { http } from './http'

export type Workshop = {
  id: number
  name: string
  code: string
  sort_order: number
  is_active: boolean
  remarks: string | null
}

export async function fetchWorkshops(activeOnly = true): Promise<Workshop[]> {
  const { data } = await http.get<{ items: Workshop[]; total: number }>('/workshops', {
    params: { limit: 500, active_only: activeOnly },
  })
  return data.items
}
