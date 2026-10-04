import { http } from '@/api/http'

export type UserInfo = {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'fleet_manager' | 'driver' | 'staff' | string
  workshop_id: number | null
}

export type LoginResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user: UserInfo
}

export async function login(payload: {
  username: string
  password: string
}): Promise<LoginResponse> {
  const { data } = await http.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function me(): Promise<UserInfo> {
  const { data } = await http.get<UserInfo>('/auth/me')
  return data
}

/** 校验当前登录账号的密码（用于敏感操作二次确认） */
export async function verifyCurrentPassword(payload: { password: string }): Promise<void> {
  await http.post('/auth/verify-password', payload)
}
