import { http } from '@/api/http'

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
  amount: string
  workshop: string
  org_name: string
  balance: string
  gift_name: string
  created_at: string
  updated_at: string
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

export type FuelBalancePage = {
  items: FuelBalance[]
  total: number
  total_amount: string
  count_zero: number
  count_low: number
  count_high: number
  sum_zero: string
  sum_low: string
  sum_high: string
}

export async function listFuelCards(params?: { skip?: number; limit?: number }): Promise<FuelCard[]> {
  const { data } = await http.get<FuelCard[]>('/fuel/cards', { params })
  return data
}

export async function listFuelBalancesPaged(params: {
  page: number
  page_size: number
  workshop?: string
  amount_bucket?: 'zero' | 'low' | 'high'
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
  card_asn?: string
  workshop?: string
  date_from?: string
  date_to?: string
  sort_by?: 'occur_time' | 'workshop' | 'amount' | 'volumn' | 'car_no' | 'card_asn'
  sort_dir?: 'asc' | 'desc'
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
