import { http } from '@/api/http'

export type UserInfo = {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'fleet_manager' | 'driver' | 'staff' | string
}

export type LoginResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

export async function startSliderSession(): Promise<{ session_id: string }> {
  const { data } = await http.post<{ session_id: string }>('/auth/slider/start')
  return data
}

export async function completeSliderSession(sessionId: string): Promise<void> {
  await http.post('/auth/slider/complete', { session_id: sessionId })
}

export async function login(payload: {
  username: string
  password: string
  slider_session_id: string
}): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function me(): Promise<UserInfo> {
  const { data } = await http.get<UserInfo>('/auth/me')
  return data
}
