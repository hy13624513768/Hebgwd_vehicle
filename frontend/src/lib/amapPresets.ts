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

export const DEFAULT_PRESET_MARKERS: PresetMarker[] = [
  { name: '哈尔滨工务段', lng: 126.57466, lat: 45.706031, locked: true },
  { name: '哈双路', lng: 126.5836, lat: 45.6891, locked: true },
  { name: '京哈高速1235公里725米作业门', lng: 126.539952, lat: 45.657708, locked: true },
]
