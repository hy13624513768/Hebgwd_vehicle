import { http } from './http'

export type NavPresetOpAction = 'create' | 'delete' | 'unlock_drag' | 'lock_drag' | 'save'

export type NavPresetOpLogPayload = {
  action: NavPresetOpAction
  marker_name: string
  marker_lng?: number | null
  marker_lat?: number | null
  detail?: string
}

/** 写入段内导航标记点操作日志（失败时静默，不阻断用户操作） */
export async function postNavPresetOpLog(payload: NavPresetOpLogPayload): Promise<void> {
  await http.post('/nav-presets/operation-logs', payload)
}
