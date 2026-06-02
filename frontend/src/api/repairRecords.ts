import { http } from '@/api/http'

export type RepairSettlementLine = {
  id: number
  line_no: number
  item_name: string
  part_name: string
  quantity: string
  unit: string
  labor_fee: string
  part_fee: string
  amount: string
  raw_text: string
  term_id: number | null
  term_name: string
  category_l1: string
  category_l2: string
  match_score: number
  match_method: string
}

export type RepairSettlement = {
  id: number
  repair_record_id: number
  order_no: string
  plate_number: string
  vehicle_model: string
  owner: string
  shop_name: string
  service_date: string | null
  mileage_in: number
  total_amount: string
  recognition_status: string
  recognition_error: string | null
  lines: RepairSettlementLine[]
  created_at: string
  updated_at: string
}

export type RepairRecord = {
  id: number
  vehicle_id: number
  driver_id: number | null
  repair_order_no: string
  photo_duo_path: string | null
  photo_item_path: string | null
  photo_item_video_path: string | null
  photo_settlement_path: string | null
  status: string
  created_by: number
  created_at: string
  updated_at: string
  plate_number: string
  driver_name: string
  settlement: RepairSettlement | null
}

export type SettlementSummary = {
  id: number
  repair_record_id: number
  vehicle_id: number
  plate_number: string
  order_no: string
  service_date: string | null
  total_amount: string
  mileage_in: number
  shop_name: string
  recognition_status: string
  line_count: number
  category_summary: Record<string, number>
  created_at: string
}

function apiBaseUrl(): string {
  const apiRoot = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
  return apiRoot ? `${apiRoot}/api/v1` : '/api/v1'
}

export function repairFileUrl(recordId: number, storedPath: string | null | undefined): string | null {
  if (!storedPath) return null
  const name = storedPath.split('/').pop() || storedPath.split('\\').pop()
  if (!name) return null
  return `${apiBaseUrl()}/repair-records/files/${recordId}/${encodeURIComponent(name)}`
}

export async function listRepairRecords(params?: {
  skip?: number
  limit?: number
  vehicle_id?: number
}): Promise<{ items: RepairRecord[]; total: number }> {
  const { data } = await http.get<{ items: RepairRecord[]; total: number }>('/repair-records', { params })
  return data
}

export async function createRepairRecord(form: FormData): Promise<RepairRecord> {
  const { data } = await http.post<RepairRecord>('/repair-records', form, {
    timeout: 180000,
  })
  return data
}

export async function recognizeRepairSettlement(recordId: number): Promise<{ ok: boolean; message: string }> {
  const { data } = await http.post<{ ok: boolean; message: string }>(
    `/repair-records/${recordId}/recognize-settlement`,
  )
  return data
}

export async function listSettlementSummaries(params?: {
  skip?: number
  limit?: number
  vehicle_id?: number
  recognition_status?: string
}): Promise<{ items: SettlementSummary[]; total: number; category_totals: Record<string, number> }> {
  const { data } = await http.get<{
    items: SettlementSummary[]
    total: number
    category_totals: Record<string, number>
  }>('/repair-records/settlements/summary', { params })
  return data
}

export async function getSettlementDetail(settlementId: number): Promise<RepairSettlement> {
  const { data } = await http.get<RepairSettlement>(`/repair-records/settlements/${settlementId}`)
  return data
}

export async function uploadSettlementTest(
  file: File,
  vehicleId?: number,
): Promise<RepairRecord> {
  const fd = new FormData()
  fd.append('photo_settlement', file)
  if (vehicleId) fd.append('vehicle_id', String(vehicleId))
  const { data } = await http.post<RepairRecord>('/repair-records/upload-settlement-test', fd, {
    timeout: 180000,
  })
  return data
}
