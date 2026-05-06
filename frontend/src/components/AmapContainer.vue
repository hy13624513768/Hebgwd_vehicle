<template>
  <div class="amap-wrap">
    <div v-if="showDestinationPicker" class="amap-search-panel">
      <div class="amap-search-row">
        <label for="amap-preset-select" class="amap-search-label">选择目的地</label>
        <select
          id="amap-preset-select"
          v-model.number="selectedPresetIndex"
          class="amap-search-input amap-search-select"
          aria-label="从预设地点选择目的地"
          @change="onPresetSelected"
        >
          <option v-for="(m, i) in presetMarkers" :key="i" :value="i">{{ m.name }}</option>
        </select>
        <button type="button" class="amap-search-btn" @click="openNavForCurrent">打开导航</button>
      </div>
    </div>

    <div ref="hostRef" class="amap-host" role="application" aria-label="地图" />
    <div
      v-if="showDrivingRoute"
      :id="drivingPanelId"
      class="amap-driving-panel"
      aria-label="驾车路线详情"
    />
    <div v-if="mapReady" class="amap-view-tools" role="toolbar" aria-label="地图视角">
      <button type="button" class="amap-tool-btn" :class="{ 'amap-tool-btn--active': viewFlat }" @click="apply2D">
        平面
      </button>
      <button type="button" class="amap-tool-btn" :class="{ 'amap-tool-btn--active': !viewFlat }" @click="apply3D">
        3D 倾斜
      </button>
      <span class="amap-tool-sep" aria-hidden="true" />
      <button type="button" class="amap-tool-btn amap-tool-btn--icon" title="俯仰增大" :disabled="pitch >= PITCH_MAX" @click="pitchDelta(8)">
        俯+
      </button>
      <button type="button" class="amap-tool-btn amap-tool-btn--icon" title="俯仰减小" :disabled="pitch <= 0" @click="pitchDelta(-8)">
        俯−
      </button>
      <button type="button" class="amap-tool-btn amap-tool-btn--ghost" title="重置旋转" @click="resetRotation">正北</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, useId, watch } from 'vue'

import { loadAmap, openAmapNavigationTo } from '@/lib/amap'

/** 默认点标记 [经度, 纬度]；未传 center 时地图中心与此一致 */
const DEFAULT_MARKER_LNG_LAT: [number, number] = [126.57466, 45.706031]

export type PresetMarker = {
  name: string
  lng: number
  lat: number
}

/** JSAPI 2.0 WebGL 下俯仰约 0～83，取保守上限避免异常 */
const PITCH_MAX = 70
const PITCH_3D_DEFAULT = 52

const COORD_EPS = 1e-5

const props = withDefaults(
  defineProps<{
    zoom?: number
    center?: [number, number]
    markerPosition?: [number, number]
    markerTitle?: string
    showMarker?: boolean
    markerNavigateOnClick?: boolean
    /** 地图上方从预设点选择目的地 */
    showDestinationPicker?: boolean
    /** 预设可选目的地（名称 + 经纬度） */
    presetMarkers?: PresetMarker[]
    /** 是否在地图上使用驾车插件默认 UI 做路径规划（选目的地后自动规划） */
    showDrivingRoute?: boolean
    /** 驾车规划起点 [经度, 纬度]，默认与默认标记点一致 */
    routeOrigin?: [number, number]
    /** 是否使用实时定位作为驾车规划起点（失败时回退 routeOrigin/default） */
    useRealtimeOrigin?: boolean
  }>(),
  {
    zoom: 14,
    markerTitle: '哈尔滨工务段',
    showMarker: true,
    markerNavigateOnClick: true,
    showDestinationPicker: true,
    presetMarkers: () => [
      { name: '哈尔滨工务段', lng: 126.57466, lat: 45.706031 },
      { name: '哈双路', lng: 126.5836, lat: 45.6891 },
    ],
    showDrivingRoute: false,
    useRealtimeOrigin: false,
  },
)

const drivingPanelId = useId().replace(/:/g, '_')

function findInitialPresetIndex(): number {
  const list = props.presetMarkers
  if (!list.length) return 0
  const mp = props.markerPosition ?? DEFAULT_MARKER_LNG_LAT
  const [lng, lat] = mp
  const title = props.markerTitle
  for (let i = 0; i < list.length; i++) {
    const p = list[i]
    if (Math.abs(p.lng - lng) < COORD_EPS && Math.abs(p.lat - lat) < COORD_EPS) return i
  }
  for (let i = 0; i < list.length; i++) {
    if (list[i].name === title) return i
  }
  return 0
}

const hostRef = ref<HTMLElement | null>(null)
const mapReady = ref(false)
const viewFlat = ref(true)
const pitch = ref(0)

const selectedPresetIndex = ref(findInitialPresetIndex())

watch(
  () => props.presetMarkers,
  (list) => {
    if (selectedPresetIndex.value >= list.length) {
      selectedPresetIndex.value = Math.max(0, list.length - 1)
    }
  },
  { deep: true },
)

/** 当前「点击标记导航」的目标（与标记位置同步） */
const navTarget = ref({
  lng: (props.markerPosition ?? DEFAULT_MARKER_LNG_LAT)[0],
  lat: (props.markerPosition ?? DEFAULT_MARKER_LNG_LAT)[1],
  name: props.markerTitle,
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let amapNS: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mapRaw: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mainMarker: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let drivingRaw: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let geolocationRaw: any = null

function routeOriginLngLat(): [number, number] {
  return props.routeOrigin ?? DEFAULT_MARKER_LNG_LAT
}

function resolveRealtimeOrigin(): Promise<[number, number] | null> {
  if (!props.useRealtimeOrigin || !geolocationRaw) return Promise.resolve(null)
  return new Promise((resolve) => {
    geolocationRaw.getCurrentPosition((status: string, result: any) => {
      if (status === 'complete' && result?.position) {
        const lng = Number(result.position.lng)
        const lat = Number(result.position.lat)
        if (!Number.isNaN(lng) && !Number.isNaN(lat)) {
          resolve([lng, lat])
          return
        }
      }
      console.warn('[amap] 实时定位失败，使用默认起点', status, result)
      resolve(null)
    })
  })
}

async function runDrivingSearchTo(dest: PresetMarker) {
  if (!props.showDrivingRoute || !drivingRaw || !amapNS) return
  const origin = (await resolveRealtimeOrigin()) ?? routeOriginLngLat()
  const [olng, olat] = origin
  if (Math.abs(olng - dest.lng) < COORD_EPS && Math.abs(olat - dest.lat) < COORD_EPS) {
    drivingRaw.clear?.()
    return
  }
  const start = new amapNS.LngLat(olng, olat)
  const end = new amapNS.LngLat(dest.lng, dest.lat)
  drivingRaw.search(start, end, (status: string, result: unknown) => {
    if (status !== 'complete') {
      console.warn('[amap] 驾车路线规划未完成', status, result)
    }
  })
}

function escapeLabelHtml(s: string) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function buildMarkerLabelHtml(text: string) {
  const t = escapeLabelHtml(text)
  return `<span style="display:inline-block;padding:4px 10px;background:rgba(253,252,247,.96);border:1px solid rgba(201,100,66,.38);border-radius:8px;font-size:12px;font-weight:600;color:#2c2825;white-space:nowrap;box-shadow:0 2px 10px rgba(20,20,19,.1);">${t}</span>`
}

function syncPitchFromMap() {
  const p = mapRaw?.getPitch?.()
  if (typeof p === 'number' && !Number.isNaN(p)) {
    pitch.value = Math.round(p)
    viewFlat.value = pitch.value < 8
  }
}

function apply2D() {
  mapRaw?.setPitch?.(0)
  mapRaw?.setRotation?.(0)
  pitch.value = 0
  viewFlat.value = true
}

function apply3D() {
  const target = Math.min(PITCH_3D_DEFAULT, PITCH_MAX)
  mapRaw?.setPitch?.(target)
  pitch.value = target
  viewFlat.value = false
}

function pitchDelta(delta: number) {
  const next = Math.min(PITCH_MAX, Math.max(0, pitch.value + delta))
  mapRaw?.setPitch?.(next)
  pitch.value = next
  viewFlat.value = next < 8
}

function resetRotation() {
  mapRaw?.setRotation?.(0)
}

function applyPresetMarker(p: PresetMarker) {
  navTarget.value = { lng: p.lng, lat: p.lat, name: p.name }
  mapRaw?.setCenter?.([p.lng, p.lat])
  mapRaw?.setZoom?.(16)
  if (mainMarker) {
    mainMarker.setPosition([p.lng, p.lat])
    mainMarker.setTitle(p.name)
    mainMarker.setLabel({
      content: buildMarkerLabelHtml(p.name),
      direction: 'top',
      offset: new amapNS.Pixel(0, -6),
    })
  }
  void runDrivingSearchTo(p)
}

function onPresetSelected() {
  const m = props.presetMarkers[selectedPresetIndex.value]
  if (m) applyPresetMarker(m)
}

function openNavForCurrent() {
  const t = navTarget.value
  openAmapNavigationTo(t.lng, t.lat, t.name)
}

onMounted(async () => {
  try {
    const plugins = ['AMap.Scale', 'AMap.ToolBar']
    if (props.showDrivingRoute) plugins.push('AMap.Driving')
    if (props.useRealtimeOrigin) plugins.push('AMap.Geolocation')
    const AMap = await loadAmap(plugins)
    amapNS = AMap
    if (!hostRef.value) return
    const lngLat = props.markerPosition ?? DEFAULT_MARKER_LNG_LAT
    const center = props.center ?? lngLat
    const [lng0, lat0] = lngLat
    navTarget.value = { lng: lng0, lat: lat0, name: props.markerTitle }

    const m = new AMap.Map(hostRef.value, {
      viewMode: '3D',
      zoom: props.zoom,
      center,
      pitch: 0,
      rotation: 0,
      mapStyle: 'amap://styles/macaron',
    })
    m.addControl(new AMap.Scale())
    m.addControl(new AMap.ToolBar({ position: 'RT' }))

    if (props.showDrivingRoute) {
      const policy = AMap.DrivingPolicy?.LEAST_TIME ?? 0
      drivingRaw = new AMap.Driving({
        map: m,
        panel: drivingPanelId,
        policy,
        autoFitView: true,
      })
    }
    if (props.useRealtimeOrigin) {
      geolocationRaw = new AMap.Geolocation({
        enableHighAccuracy: true,
        timeout: 8000,
      })
    }

    if (props.showMarker) {
      mainMarker = new AMap.Marker({
        position: lngLat,
        title: props.markerTitle,
        anchor: 'bottom-center',
        cursor: 'pointer',
        label: {
          content: buildMarkerLabelHtml(props.markerTitle),
          direction: 'top',
          offset: new AMap.Pixel(0, -6),
        },
      })
      if (props.markerNavigateOnClick) {
        mainMarker.on('click', () => {
          const t = navTarget.value
          openAmapNavigationTo(t.lng, t.lat, t.name)
        })
      }
      m.add(mainMarker)
    }

    mapRaw = m
    mapReady.value = true
    syncPitchFromMap()
    selectedPresetIndex.value = findInitialPresetIndex()
    const initialPreset = props.presetMarkers[selectedPresetIndex.value]
    if (initialPreset) void runDrivingSearchTo(initialPreset)
  } catch (e) {
    console.error('[amap] 初始化失败', e)
  }
})

onUnmounted(() => {
  drivingRaw?.clear?.()
  drivingRaw = null
  geolocationRaw = null
  mapRaw?.destroy()
  mapRaw = null
  mainMarker = null
  amapNS = null
  mapReady.value = false
})
</script>

<style scoped>
.amap-wrap {
  position: relative;
  width: 100%;
}

.amap-search-panel {
  margin-bottom: 0.65rem;
}

.amap-search-row {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
  flex-wrap: wrap;
}

.amap-search-label {
  flex: 0 0 auto;
  align-self: center;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
}

.amap-search-input {
  flex: 1 1 180px;
  min-width: 0;
  min-height: 44px;
  padding: 0.5rem 0.75rem;
  border-radius: 10px;
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  font: inherit;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.95);
}

.amap-search-select {
  cursor: pointer;
  appearance: auto;
}

.amap-search-btn {
  cursor: pointer;
  min-height: 44px;
  padding: 0.5rem 1rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid rgba(201, 100, 66, 0.45);
  background: var(--cl-terracotta, #c96442);
  color: #fff;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  flex: 0 0 auto;
}

.amap-search-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.amap-host {
  width: 100%;
  height: clamp(300px, 62vh, 620px);
  min-height: 280px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
}

.amap-driving-panel {
  margin-top: 0.65rem;
  max-height: min(32vh, 280px);
  overflow: auto;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
  background: rgba(253, 252, 247, 0.96);
  box-sizing: border-box;
  font-size: 13px;
  line-height: 1.45;
}

.amap-driving-panel :deep(.amap-lib-driving) {
  border-radius: 12px;
}

.amap-view-tools {
  position: absolute;
  left: 10px;
  bottom: 24px;
  z-index: 500;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(253, 252, 247, 0.92);
  border: 1px solid rgba(142, 132, 109, 0.22);
  box-shadow: 0 4px 18px rgba(20, 20, 19, 0.08);
  max-width: calc(100% - 20px);
}

@media (max-width: 900px) {
  .amap-host {
    height: clamp(280px, 56vh, 500px);
  }

  .amap-driving-panel {
    max-height: min(28vh, 240px);
  }
}

@media (max-width: 640px) {
  .amap-search-row {
    gap: 0.45rem;
  }

  .amap-search-input,
  .amap-search-btn {
    min-height: 42px;
  }

  .amap-host {
    height: clamp(360px, 78vh, 88svh);
    min-height: 360px;
    border-radius: 8px;
  }

  .amap-driving-panel {
    margin-top: 0.45rem;
    max-height: min(20vh, 180px);
    border-radius: 8px;
  }

  .amap-view-tools {
    left: 8px;
    right: 8px;
    bottom: 10px;
    max-width: none;
    padding: 7px 8px;
    gap: 4px;
  }

  .amap-tool-btn {
    font-size: 0.72rem;
    padding: 0.3rem 0.48rem;
  }
}

.amap-tool-sep {
  width: 1px;
  height: 1.1rem;
  background: rgba(142, 132, 109, 0.28);
  margin: 0 2px;
}

.amap-tool-btn {
  cursor: pointer;
  border: 1px solid rgba(142, 132, 109, 0.35);
  background: rgba(255, 255, 255, 0.9);
  color: var(--cl-charcoal, #2c2b28);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.35rem 0.55rem;
  border-radius: 8px;
  line-height: 1.2;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.amap-tool-btn:hover:not(:disabled) {
  background: rgba(245, 229, 218, 0.45);
  border-color: rgba(201, 100, 66, 0.35);
}

.amap-tool-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.amap-tool-btn--active {
  background: rgba(201, 100, 66, 0.18);
  border-color: rgba(201, 100, 66, 0.45);
  color: var(--cl-terracotta, #c96442);
}

.amap-tool-btn--icon {
  min-width: 2.5rem;
  padding-inline: 0.35rem;
}

.amap-tool-btn--ghost {
  background: transparent;
}
</style>
