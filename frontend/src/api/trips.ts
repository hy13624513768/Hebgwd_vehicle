import { http } from '@/api/http'
import type { TripRequest } from '@/api/types'

export async function listTrips(params?: {
  q?: string
  status?: string
  skip?: number
  limit?: number
}): Promise<TripRequest[]> {
  const { data } = await http.get<TripRequest[]>('/trip-requests', { params })
  return data
}

export async function createTrip(payload: Record<string, unknown>): Promise<TripRequest> {
  const { data } = await http.post<TripRequest>('/trip-requests', payload)
  return data
}

export async function updateTrip(id: number, payload: Record<string, unknown>): Promise<TripRequest> {
  const { data } = await http.patch<TripRequest>(`/trip-requests/${id}`, payload)
  return data
}

export async function deleteTrip(id: number): Promise<void> {
  await http.delete(`/trip-requests/${id}`)
}
