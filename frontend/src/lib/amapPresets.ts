/** 段内导航等页面共用的地图预设点（名称 + GCJ-02 经纬度） */
export type PresetMarker = {
  name: string
  lng: number
  lat: number
  /**
   * 位置默认锁定（防误触）；仅当显式为 false 时可在地图上拖动或使用地图选点。
   * 仍可在表单中改坐标后保存。
   */
  locked?: boolean
}

/** 地图上是否禁止拖动 / 地图选点（未传 locked 视为锁定） */
export function isPresetPositionLocked(p: PresetMarker | undefined): boolean {
  if (!p) return true
  return p.locked !== false
}

/** 写入服务器前统一为锁定，避免历史数据或误保存导致「未点解锁却可拖」 */
export function normalizePresetMarkersForStorage(markers: PresetMarker[]): PresetMarker[] {
  return markers.map((m) => ({ ...m, locked: true }))
}

/** 去掉首尾空格，用于名称比较与保存 */
export function normalizePresetMarkerName(name: string): string {
  return name.trim()
}

/**
 * 检查名称是否与列表中其他标记重复（排除当前正在编辑的下标）。
 * @returns 重复项的下标；无重复返回 -1
 */
export function findDuplicatePresetNameIndex(
  markers: PresetMarker[],
  name: string,
  excludeIndex: number,
): number {
  const key = normalizePresetMarkerName(name)
  if (!key) return -1
  return markers.findIndex((m, i) => i !== excludeIndex && normalizePresetMarkerName(m.name) === key)
}

/** 校验整表名称均唯一；失败时返回提示文案 */
export function validateUniquePresetMarkerNames(markers: PresetMarker[]): string | null {
  const seen = new Set<string>()
  for (const m of markers) {
    const key = normalizePresetMarkerName(m.name)
    if (!key) return '标记名称不能为空，请填写后再保存。'
    if (seen.has(key)) {
      return `标记名称「${key}」与已有标记重复，请修改为不重名的名称后再保存。`
    }
    seen.add(key)
  }
  return null
}

export const DEFAULT_PRESET_MARKERS: PresetMarker[] = [
  { name: '哈尔滨工务段', lng: 126.57466, lat: 45.706031, locked: true },
  { name: '哈双路', lng: 126.5836, lat: 45.6891, locked: true },
  { name: '京哈高速1235公里725米作业门', lng: 126.539952, lat: 45.657708, locked: true },
]
