import { http } from '@/api/http'

export type UserAdmin = {
  id: number
  username: string
  display_name: string
  role: string
  is_active: boolean
}

export type RoleDefinition = {
  code: string
  label: string
  rank: number
  description: string
}

export type UserAdminList = {
  items: UserAdmin[]
  total: number
}

export type DriverAccountItem = {
  driver_id: number
  name: string
  username: string | null
  status: string
  reason: string
}

export type DriverAccountBatchResult = {
  created: number
  skipped: number
  failed: number
  details: DriverAccountItem[]
}

export async function fetchRoleDefinitions(): Promise<RoleDefinition[]> {
  const { data } = await http.get<RoleDefinition[]>('/users/role-definitions')
  return data
}

export async function fetchAssignableRoles(): Promise<string[]> {
  const { data } = await http.get<string[]>('/users/assignable-roles')
  return data
}

export async function listUsers(params: {
  skip?: number
  limit?: number
  q?: string
  role?: string
}): Promise<UserAdminList> {
  const { data } = await http.get<UserAdminList>('/users', { params })
  return data
}

export async function createUser(body: {
  username: string
  password: string
  display_name: string
  role: string
  is_active: boolean
}): Promise<UserAdmin> {
  const { data } = await http.post<UserAdmin>('/users', body)
  return data
}

export async function updateUser(
  id: number,
  body: { display_name?: string; password?: string; role?: string; is_active?: boolean },
): Promise<UserAdmin> {
  const { data } = await http.patch<UserAdmin>(`/users/${id}`, body)
  return data
}

export async function deleteUser(id: number): Promise<void> {
  await http.delete(`/users/${id}`)
}

export async function generateDriverAccounts(): Promise<DriverAccountBatchResult> {
  const { data } = await http.post<DriverAccountBatchResult>('/users/generate-driver-accounts')
  return data
}
