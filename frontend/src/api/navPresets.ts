import type { PresetMarker } from '@/lib/amapPresets'

import { http } from './http'

export async function fetchNavPresets(): Promise<PresetMarker[]> {
  const { data } = await http.get<{ markers: PresetMarker[] }>('/nav-presets')
  return data.markers
}

export async function replaceNavPresets(markers: PresetMarker[]): Promise<void> {
  await http.put('/nav-presets', { markers })
}
