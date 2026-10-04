import type { PresetMarker } from '@/lib/amapPresets'

import { http } from './http'
let revision: string | null = null

export async function fetchNavPresets(): Promise<PresetMarker[]> {
  const { data } = await http.get<{ markers: PresetMarker[]; revision: string }>('/nav-presets')
  revision = data.revision
  return data.markers
}

export async function replaceNavPresets(markers: PresetMarker[]): Promise<PresetMarker[]> {
  const { data } = await http.put<{ markers: PresetMarker[]; revision: string }>('/nav-presets', { markers, revision })
  revision = data.revision
  return data.markers
}
