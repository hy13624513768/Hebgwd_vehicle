import type { PresetMarker } from '@/lib/amapPresets'

import { http } from './http'

export async function fetchNavPresets(): Promise<PresetMarker[]> {
  const { data } = await http.get<{ markers: PresetMarker[] }>('/nav-presets')
  return data.markers
}

export async function replaceNavPresets(markers: PresetMarker[]): Promise<PresetMarker[]> {
  const { data } = await http.put<{ markers: PresetMarker[] }>('/nav-presets', { markers })
  return data.markers
}
