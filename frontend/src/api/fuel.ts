import { http } from '@/api/http'
import { getAccessToken } from '@/lib/authToken'

export type FuelCard = {
  id: number
  card_no: string
  col_c: string
  col_d: string
  created_at: string
  updated_at: string
}

export type FuelRecord = {
  id: number
  card_asn: string
  car_no: string
  occur_time: string
  volumn: string
  volume_available: boolean
  balance_available: boolean
  amount: string
  workshop: string
  org_name: string
  balance: string
  gift_name: string
  created_at: string
  updated_at: string
}

export type FuelRecordDetail = FuelRecord & {
  platform_data: Record<string, unknown> | null
  product_detail_error: string | null
}

export async function getFuelRecordDetail(id: number): Promise<FuelRecordDetail> {
  const { data } = await http.get<FuelRecordDetail>(`/fuel/records/${id}`, { timeout: 120000 })
  return data
}

export type FuelBalance = {
  id: number
  card_no: string
  workshop: string
  vehicle_no: string
  amount: string
  reserve_fund: string
  total: string
  created_at: string
  updated_at: string
}

export type FuelBalanceBucket = {
  key: string
  label: string
  filter_min: string | number | null
  filter_max: string | number | null
  count: number
  sum: string
}

export type FuelBalancePage = {
  items: FuelBalance[]
  total: number
  total_amount: string
  buckets: FuelBalanceBucket[]
}

export type FuelSyncResult = {
  ok: boolean
  balance_written?: number
  record_written?: number
  balance_matched?: number
  record_matched?: number
  record_inserted?: number
  record_updated?: number
  record_missing_volume?: number
  record_missing_card?: number
  date_from?: string
  date_to?: string
  error?: string
}

function apiBaseUrl(): string {
  const apiRoot = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
  return apiRoot ? `${apiRoot}/api/v1` : '/api/v1'
}

export type FuelSyncStats = {
  today_count: number
  last_synced_at: string | null
}

export async function fetchFuelSyncStats(): Promise<FuelSyncStats> {
  const { data } = await http.get<FuelSyncStats>('/fuel/sync-stats')
  return data
}

export async function syncFuelFromPlatform(
  params: { date_from?: string; date_to?: string; target?: 'balances' | 'bills' },
  onProgress: (message: string) => void,
  onBatchReady?: (batch: FuelSyncResult) => void | Promise<void>,
): Promise<FuelSyncResult> {
  const token = getAccessToken()
  const resp = await fetch(`${apiBaseUrl()}/fuel/sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
  })
  if (!resp.ok) {
    let detail = `同步请求失败（HTTP ${resp.status}）`
    try {
      const err = (await resp.json()) as { detail?: string }
      if (err.detail) detail = err.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  if (!resp.body) throw new Error('服务器未返回同步进度')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastResult: FuelSyncResult = { ok: false }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      const evt = JSON.parse(trimmed) as {
        type: string
        message?: string
        ok?: boolean
        error?: string
      }
      if (evt.type === 'progress' && evt.message) onProgress(evt.message)
      if (evt.type === 'batch' && onBatchReady) await onBatchReady(evt as FuelSyncResult)
      if (evt.type === 'done') lastResult = { ...(evt as FuelSyncResult), ok: true }
      if (evt.type === 'error') throw new Error(evt.message || '同步失败')
    }
  }

  if (!lastResult.ok) throw new Error('同步未完成')
  return lastResult
}

export async function listFuelCards(params?: { skip?: number; limit?: number }): Promise<FuelCard[]> {
  const { data } = await http.get<FuelCard[]>('/fuel/cards', { params })
  return data
}

export async function listFuelBalancesPaged(params: {
  page: number
  page_size: number
  workshop?: string
  vehicle_no?: string
  total_min?: number
  total_max?: number
  sort_by?: 'card_no' | 'workshop' | 'vehicle_no' | 'amount' | 'reserve_fund' | 'total'
  sort_dir?: 'asc' | 'desc'
}): Promise<FuelBalancePage> {
  const { data } = await http.get<FuelBalancePage>('/fuel/balances', { params })
  return data
}

export async function listFuelBalanceWorkshops(): Promise<string[]> {
  const { data } = await http.get<string[]>('/fuel/balance-workshops')
  return data
}

export type FuelEntry = {
  id: number
  vehicle_id: number
  plate_number: string
  odometer: number
  fueled_at: string
  has_photo: boolean
  created_by: number
  created_at: string
  updated_at: string
}

export async function createFuelEntry(form: FormData): Promise<FuelEntry> {
  const { data } = await http.post<FuelEntry>('/fuel/entries', form, { timeout: 180000 })
  return data
}

export async function listFuelBalanceVehicles(): Promise<string[]> {
  const { data } = await http.get<string[]>('/fuel/balance-vehicles')
  return data
}

export async function createFuelCard(payload: Record<string, unknown>): Promise<FuelCard> {
  const { data } = await http.post<FuelCard>('/fuel/cards', payload)
  return data
}

export async function updateFuelCard(id: number, payload: Record<string, unknown>): Promise<FuelCard> {
  const { data } = await http.patch<FuelCard>(`/fuel/cards/${id}`, payload)
  return data
}

export async function deleteFuelCard(id: number): Promise<void> {
  await http.delete(`/fuel/cards/${id}`)
}

export type FuelRecordPage = {
  items: FuelRecord[]
  total: number
}

export type ListFuelRecordsParams = {
  page?: number
  page_size?: number
  has_card_only?: boolean
  car_no?: string
  card_asn?: string
  workshop?: string
  date_from?: string
  date_to?: string
  sort_by?: 'occur_time' | 'workshop' | 'amount' | 'volumn' | 'car_no' | 'card_asn'
  sort_dir?: 'asc' | 'desc'
  sort_secondary_by?: 'occur_time' | 'car_no'
  sort_secondary_dir?: 'asc' | 'desc'
}

export async function listFuelRecordsPaged(params: ListFuelRecordsParams): Promise<FuelRecordPage> {
  const { data } = await http.get<FuelRecordPage>('/fuel/records', { params })
  return data
}

export async function listFuelRecordWorkshops(): Promise<string[]> {
  const { data } = await http.get<string[]>('/fuel/record-workshops')
  return data
}

export async function listFuelRecordCards(): Promise<string[]> {
  const { data } = await http.get<string[]>('/fuel/record-cards')
  return data
}

export type FuelRecordCardOption = { card_asn: string; car_no: string }

export async function listFuelRecordCardOptions(): Promise<FuelRecordCardOption[]> {
  const { data } = await http.get<FuelRecordCardOption[]>('/fuel/record-card-options')
  return data
}

export async function listFuelRecordVehicles(): Promise<string[]> {
  const { data } = await http.get<string[]>('/fuel/record-vehicles')
  return data
}

export async function exportFuelRecordsExcel(params: ListFuelRecordsParams): Promise<Blob> {
  const { data } = await http.get('/fuel/records/export.xlsx', {
    params,
    responseType: 'blob',
  })
  return data as Blob
}

export async function deleteFuelRecord(id: number): Promise<void> {
  await http.delete(`/fuel/records/${id}`)
}
