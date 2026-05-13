<template>
  <div class="amap-wrap">
    <div v-if="!canLoadMap" class="amap-missing" role="alert">
      <p class="amap-missing__title">高德地图未配置，无法显示页面</p>
      <p class="amap-missing__text">
        在 <code>frontend</code> 目录新建 <code>.env.development.local</code>（或 <code>.env.local</code>），参考
        <code>.env.example</code> 填写：
      </p>
      <pre class="amap-missing__pre">VITE_AMAP_KEY=你的Web端Key
VITE_AMAP_SECURITY_JSCODE=对应安全密钥</pre>
      <p class="amap-missing__text">
        控制台：<a href="https://console.amap.com/" target="_blank" rel="noopener noreferrer">高德开放平台</a>
        → 应用 → Key 与安全密钥（JS API 2.0）。
      </p>
      <p class="amap-missing__text">
        <strong>域名白名单</strong>须包含当前访问地址（例如 Sealos 公网
        <code>https://fhlkzwzoizzu.sealosbja.site</code> 及本地 <code>http://127.0.0.1:8080</code>）。
      </p>
      <p class="amap-missing__text muted">修改环境变量后请<strong>重启</strong> Vite（停止再执行 <code>npm run dev</code>）。</p>
    </div>
    <div v-else-if="warnSecurityOnly" class="amap-missing amap-missing--warn" role="status">
      <p class="amap-missing__title">未配置安全密钥</p>
      <p class="amap-missing__text">
        已检测到 <code>VITE_AMAP_KEY</code>，但未设置 <code>VITE_AMAP_SECURITY_JSCODE</code>。高德 2.x 通常会拦截请求，地图可能空白。
        请在同一文件中补充安全密钥并重启 Vite。
      </p>
    </div>

    <template v-if="canLoadMap">
    <div v-if="initError" class="amap-missing amap-missing--error" role="alert">
      <p class="amap-missing__title">地图加载失败</p>
      <p class="amap-missing__text">{{ initError }}</p>
      <p class="amap-missing__text muted">
        常见原因：安全密钥未配置、Key 类型错误、当前域名未加入高德控制台「域名白名单」。修改后请重启 Vite。
      </p>
    </div>
    <div
      v-if="showDestinationPicker"
      class="amap-search-panel"
      :class="{ 'amap-search-panel--editor-open': allowMarkerEdit && showMarkerEditor }"
    >
      <div class="amap-search-row">
        <label for="amap-preset-select-trigger" class="amap-search-label">选择目的地</label>
        <div class="amap-preset-combobox-wrap">
          <div
            id="amap-preset-select"
            ref="presetComboRoot"
            class="amap-preset-combobox"
            :class="{ 'amap-preset-combobox--open': presetComboOpen }"
          >
            <button
              id="amap-preset-select-trigger"
              type="button"
              class="amap-search-input amap-preset-combobox__trigger"
              :disabled="presetMarkers.length === 0"
              aria-haspopup="listbox"
              :aria-expanded="presetComboOpen"
              aria-controls="amap-preset-combobox-list"
              aria-label="从预设地点选择目的地"
              @click="togglePresetCombo"
            >
              <span class="amap-preset-combobox__trigger-text">{{ currentPresetLabel }}</span>
              <span class="amap-preset-combobox__chevron" aria-hidden="true">▼</span>
            </button>
            <div
              v-show="presetComboOpen"
              class="amap-preset-combobox__panel"
              role="presentation"
              @click.stop
            >
              <input
                ref="presetComboInputRef"
                v-model="presetComboFilter"
                type="search"
                class="amap-search-input amap-preset-combobox__filter"
                placeholder="输入关键字筛选…"
                aria-label="在预设目的地中搜索关键字"
                autocomplete="off"
                @keydown.escape.prevent="closePresetCombo"
              />
              <ul
                id="amap-preset-combobox-list"
                class="amap-preset-combobox__list"
                role="listbox"
                aria-label="预设目的地"
              >
                <li v-if="filteredPresetComboIndices.length === 0" class="amap-preset-combobox__empty" role="presentation">
                  无匹配项，请修改关键字
                </li>
                <li
                  v-for="i in filteredPresetComboIndices"
                  :key="i"
                  role="option"
                  :aria-selected="i === selectedPresetIndex"
                  class="amap-preset-combobox__option"
                  :class="{ 'amap-preset-combobox__option--active': i === selectedPresetIndex }"
                  @click="selectPresetFromCombo(i)"
                >
                  {{ presetComboOptionLabel(i) }}
                </li>
              </ul>
            </div>
          </div>
        </div>
        <button type="button" class="amap-search-btn" @click="openNavForCurrent">打开导航</button>
      </div>
      <div class="amap-search-row amap-search-row--secondary">
        <label for="amap-street-search" class="amap-search-label">搜索街道</label>
        <div class="amap-search-field-wrap">
          <input
            id="amap-street-search"
            v-model="streetSearchKeyword"
            type="text"
            class="amap-search-input"
            placeholder="输入街道名称搜索..."
            aria-label="搜索街道名称"
            @keyup.enter="searchStreet"
          />
          <button type="button" class="amap-search-btn amap-search-btn--secondary" @click="searchStreet">搜索</button>
        </div>
      </div>
      <div v-if="streetSearchResults.length > 0" class="amap-search-results">
        <div
          v-for="(item, index) in streetSearchResults"
          :key="index"
          class="amap-search-result-item"
          @click="selectStreetResult(item)"
        >
          <div class="amap-result-name">{{ item.name }}</div>
          <div class="amap-result-address">{{ item.address }}</div>
        </div>
      </div>
      <p v-if="!allowMarkerEdit" class="amap-perm-hint">
        当前账号无地图标点编辑权限；预设点位置仅各级管理员可拖动或修改坐标。
      </p>
      <div v-if="allowMarkerEdit" class="amap-marker-editor">
        <div class="amap-editor-toggle" @click="showMarkerEditor = !showMarkerEditor">
          <span>{{ showMarkerEditor ? '收起' : '编辑标记位置' }}</span>
          <span class="amap-toggle-icon">{{ showMarkerEditor ? '▼' : '▶' }}</span>
        </div>
        <div v-if="showMarkerEditor" class="amap-editor-panel">
          <div class="amap-editor-row">
            <label class="amap-editor-label">名称</label>
            <input
              v-model="editName"
              type="text"
              class="amap-editor-input"
              placeholder="地图上显示的名称"
              aria-label="标记名称"
            />
          </div>
          <div class="amap-editor-row amap-editor-row--coords">
            <div class="amap-editor-coord-cell">
              <label class="amap-editor-label" for="amap-edit-lng">经度</label>
              <input
                id="amap-edit-lng"
                v-model="editLng"
                type="text"
                class="amap-editor-input"
                placeholder="126.57466"
                inputmode="decimal"
              />
            </div>
            <div class="amap-editor-coord-cell">
              <label class="amap-editor-label" for="amap-edit-lat">纬度</label>
              <input
                id="amap-edit-lat"
                v-model="editLat"
                type="text"
                class="amap-editor-input"
                placeholder="45.706031"
                inputmode="decimal"
              />
            </div>
          </div>
          <div class="amap-editor-lock-row">
            <button
              type="button"
              class="amap-editor-btn amap-editor-btn--lock"
              :class="{ 'amap-editor-btn--lock-on': currentPresetLocked }"
              @click="toggleMarkerPositionLock"
            >
              {{ currentPresetLocked ? '解锁拖动' : '锁定拖动' }}
            </button>
            <span v-if="isCoarsePointer" class="amap-lock-hint">锁定后不可拖点/选点；可改上方坐标后保存。</span>
            <span v-else class="amap-lock-hint">锁定后无法在地图上拖动或选点，避免误触；仍可在上方改坐标后保存。</span>
          </div>
          <div class="amap-editor-actions amap-editor-actions--split">
            <button type="button" class="amap-editor-btn" @click="addPresetMarkerPoint">新增标记</button>
            <button
              type="button"
              class="amap-editor-btn"
              :disabled="presetMarkers.length <= 1"
              @click="onClickDeletePresetMarker"
            >
              删除当前
            </button>
          </div>
          <div class="amap-editor-actions">
            <button type="button" class="amap-editor-btn amap-editor-btn--primary" @click="applyMarkerEdit">
              保存当前标记
            </button>
            <button
              type="button"
              class="amap-editor-btn"
              :disabled="deviceLocateLoading"
              @click="onFetchDeviceLocation"
            >
              {{ deviceLocateLoading ? '定位中…' : '获取当前位置' }}
            </button>
          </div>
          <button
            type="button"
            class="amap-editor-btn amap-editor-btn--block"
            :class="{ 'amap-editor-btn--pick-on': mapPickActive }"
            :disabled="!mapReady || currentPresetLocked"
            @click="toggleMapPick"
          >
            {{ mapPickActive ? '取消地图选点' : '地图选点' }}
          </button>
          <p v-if="mapPickActive" class="amap-editor-tip amap-editor-tip--pick">
            {{ mapPickHintText }}
          </p>
          <p class="amap-editor-tip">{{ dragHintText }}</p>
        </div>
      </div>
    </div>

    <!-- 移动端展开编辑时：地图易吞掉单指滑动；中间条 + 临时关地图拖移，便于整页上下滚动 -->
    <div
      v-if="showMobileMapEditorChrome"
      class="amap-mobile-page-scroll-bridge"
      role="note"
      aria-label="上下滑动此处可带动整页滚动"
    >
      <span class="amap-mobile-page-scroll-bridge__line" aria-hidden="true" />
      <span class="amap-mobile-page-scroll-bridge__text">上下滑动 · 翻页</span>
      <span class="amap-mobile-page-scroll-bridge__line" aria-hidden="true" />
    </div>

    <!-- 仅地图区域为定位上下文，避免「图层 / 视角」悬浮控件相对整页（含搜索条）偏移 -->
    <div class="amap-map-stage" :class="{ 'amap-map-stage--picking': mapPickActive }">
      <div
        v-if="mapPickActive && mapReady"
        class="amap-pick-banner"
        role="status"
        aria-live="polite"
      >
        地图选点中 · 轻触目标位置
      </div>
      <div
        ref="hostRef"
        class="amap-host"
        :class="{ 'amap-host--can-edit': allowMarkerEdit && mapReady }"
        role="application"
        aria-label="地图"
      />
      <div
        v-if="mapReady"
        class="amap-layer-tools"
        role="region"
        aria-label="图层切换"
      >
        <button
          type="button"
          class="amap-layer-toggle"
          :aria-expanded="layerPanelExpanded"
          aria-controls="amap-layer-panel"
          @click="layerPanelExpanded = !layerPanelExpanded"
        >
          图层
          <span class="amap-layer-chevron" aria-hidden="true">{{ layerPanelExpanded ? '▼' : '▶' }}</span>
        </button>
        <div
          id="amap-layer-panel"
          v-show="layerPanelExpanded"
          class="amap-layer-panel"
        >
          <div class="amap-layer-section">
            <div class="amap-layer-section-title">底图</div>
            <label class="amap-layer-option">
              <input v-model="baseLayerType" type="radio" value="normal" />
              <span>标准图层</span>
            </label>
            <label class="amap-layer-option">
              <input v-model="baseLayerType" type="radio" value="satellite" />
              <span>卫星图</span>
            </label>
          </div>
          <div class="amap-layer-section">
            <div class="amap-layer-section-title">叠加</div>
            <label class="amap-layer-option">
              <input v-model="showRoadNet" type="checkbox" />
              <span>路网</span>
            </label>
            <label class="amap-layer-option">
              <input v-model="showTraffic" type="checkbox" />
              <span>路况</span>
            </label>
          </div>
        </div>
      </div>
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

    <Teleport to="body">
      <div
        v-if="deletePwdOpen"
        class="amap-delete-pwd-backdrop"
        role="presentation"
        @click.self="closeDeletePwdModal"
      >
        <div
          class="amap-delete-pwd-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="amap-delete-pwd-title"
          @keydown.escape.prevent="closeDeletePwdModal"
        >
          <p id="amap-delete-pwd-title" class="amap-delete-pwd-title">删除当前标记</p>
          <p class="amap-delete-pwd-desc">请输入<strong>当前登录账号</strong>的登录密码，确认后再删除。</p>
          <input
            ref="deletePwdInputRef"
            v-model="deletePwdField"
            type="password"
            class="amap-delete-pwd-input"
            autocomplete="current-password"
            aria-label="当前账号登录密码"
            @keydown.escape.prevent="closeDeletePwdModal"
            @keyup.enter="submitDeletePwdModal"
          />
          <div class="amap-delete-pwd-actions">
            <button type="button" class="amap-delete-pwd-btn" :disabled="deletePwdVerifying" @click="closeDeletePwdModal">
              取消
            </button>
            <button
              type="button"
              class="amap-delete-pwd-btn amap-delete-pwd-btn--danger"
              :disabled="deletePwdVerifying"
              @click="submitDeletePwdModal"
            >
              {{ deletePwdVerifying ? '验证中…' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import * as authApi from '@/api/auth'
import { isAmapKeyConfigured, isAmapSecurityConfigured, loadAmap, openAmapNavigationTo } from '@/lib/amap'
import { DEFAULT_PRESET_MARKERS, isPresetPositionLocked, type PresetMarker } from '@/lib/amapPresets'

const canLoadMap = computed(() => isAmapKeyConfigured())
const warnSecurityOnly = computed(() => canLoadMap.value && !isAmapSecurityConfigured())

/** 默认点标记 [经度, 纬度]；未传 center 时地图中心与此一致 */
const DEFAULT_MARKER_LNG_LAT: [number, number] = [126.57466, 45.706031]

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
    /**
     * 是否允许拖动地图标记、使用「编辑标记位置」面板修改坐标。
     * 业务页应按角色传入：仅段级/车间级等管理员为 true，驾驶员等应为 false。
     */
    allowMarkerEdit?: boolean
  }>(),
  {
    zoom: 14,
    markerTitle: '哈尔滨工务段',
    showMarker: true,
    markerNavigateOnClick: false,
    showDestinationPicker: true,
    allowMarkerEdit: false,
  },
)

/** 预设/可管理标记点列表，支持 v-model:preset-markers 在父级持久化 */
const presetMarkers = defineModel<PresetMarker[]>('presetMarkers', {
  default: () => DEFAULT_PRESET_MARKERS.map((p) => ({ ...p })),
})

function findInitialPresetIndex(): number {
  const list = presetMarkers.value
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
const initError = ref<string | null>(null)
const mapReady = ref(false)
const viewFlat = ref(true)
const pitch = ref(0)

/** 自定义图层面板（替代高德 MapType 控件，默认折叠减少遮挡） */
const layerPanelExpanded = ref(false)
const baseLayerType = ref<'normal' | 'satellite'>('normal')
const showRoadNet = ref(false)
const showTraffic = ref(false)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let defaultLayerInst: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let satelliteLayerInst: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let roadNetLayerInst: any = null
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let trafficLayerInst: any = null

function applyMapLayers() {
  if (!mapRaw || !amapNS) return
  const base = baseLayerType.value === 'satellite' ? satelliteLayerInst : defaultLayerInst
  if (!base) return
  const layers: any[] = [base]
  if (showRoadNet.value && roadNetLayerInst) layers.push(roadNetLayerInst)
  if (showTraffic.value && trafficLayerInst) layers.push(trafficLayerInst)
  try {
    mapRaw.setLayers(layers)
  } catch (e) {
    console.warn('[amap] setLayers 失败', e)
  }
}

watch([baseLayerType, showRoadNet, showTraffic], () => {
  applyMapLayers()
})

const selectedPresetIndex = ref(findInitialPresetIndex())

const currentPresetLocked = computed(() =>
  isPresetPositionLocked(presetMarkers.value[selectedPresetIndex.value]),
)

/** 预设目的地：展开后在内置框中按名称关键字筛选 */
const presetComboOpen = ref(false)
const presetComboFilter = ref('')
const presetComboRoot = ref<HTMLElement | null>(null)
const presetComboInputRef = ref<HTMLInputElement | null>(null)

const filteredPresetComboIndices = computed(() => {
  const list = presetMarkers.value
  const kw = presetComboFilter.value.trim().toLowerCase()
  if (!kw) return list.map((_, i) => i)
  const out: number[] = []
  for (let i = 0; i < list.length; i++) {
    if ((list[i]?.name ?? '').toLowerCase().includes(kw)) out.push(i)
  }
  return out
})

const currentPresetLabel = computed(() => {
  const m = presetMarkers.value[selectedPresetIndex.value]
  if (!m) return presetMarkers.value.length === 0 ? '暂无预设点' : '请选择'
  return `${m.name}${isPresetPositionLocked(m) ? '（已锁定）' : ''}`
})

function presetComboOptionLabel(i: number): string {
  const m = presetMarkers.value[i]
  if (!m) return ''
  return `${m.name}${isPresetPositionLocked(m) ? '（已锁定）' : ''}`
}

function closePresetCombo() {
  presetComboOpen.value = false
  presetComboFilter.value = ''
}

function togglePresetCombo() {
  if (presetMarkers.value.length === 0) return
  presetComboOpen.value = !presetComboOpen.value
  if (presetComboOpen.value) {
    presetComboFilter.value = ''
    void nextTick(() => presetComboInputRef.value?.focus())
  }
}

function onPresetComboDocPointerDown(e: PointerEvent) {
  const root = presetComboRoot.value
  if (!presetComboOpen.value || !root) return
  if (!root.contains(e.target as Node)) closePresetCombo()
}

function syncMarkerDraggability() {
  const d = props.allowMarkerEdit
  try {
    mainMarker?.setDraggable?.(d)
    for (let i = 0; i < presetOverlayMarkers.length; i++) {
      const locked = isPresetPositionLocked(presetMarkers.value[i])
      presetOverlayMarkers[i]?.setDraggable?.(d && !locked)
    }
  } catch {
    /* ignore */
  }
}

watch(
  () => props.allowMarkerEdit,
  (v) => {
    if (!v) showMarkerEditor.value = false
    syncMarkerDraggability()
    if (!mapRaw || !amapNS) return
    if (presetMarkers.value.length > 0) {
      installPresetOverlays(amapNS)
    } else if (mainMarker) {
      try {
        mainMarker.setLabel(buildMarkerLabelOptions(amapNS, props.markerTitle, v))
      } catch {
        /* ignore */
      }
    }
  },
)

// 街道搜索相关状态
const streetSearchKeyword = ref('')
const streetSearchResults = ref<Array<{ name: string; address: string; lng: number; lat: number }>>([])
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let placeSearchRaw: any = null

// 标记编辑相关状态
const editableMarker = ref<{ lng: number; lat: number; name: string } | null>(null)
const editName = ref('')
const editLng = ref('')
const editLat = ref('')
const showMarkerEditor = ref(false)
const deletePwdOpen = ref(false)
const deletePwdField = ref('')
const deletePwdVerifying = ref(false)
const deletePwdInputRef = ref<HTMLInputElement | null>(null)
const deviceLocateLoading = ref(false)
const mapPickActive = ref(false)
/** 触摸/笔等粗指针设备（典型为手机），用于提示文案与交互提示 */
const isCoarsePointer = ref(false)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let mapPickHandler: any = null
/** 避免移动端一次轻触触发两次 map click */
let lastMapPickAt = 0

const mapPickHintText = computed(() =>
  isCoarsePointer.value
    ? '在地图上轻触路面等空白处选点；点到标记只会选中该点，可点在标记旁边。选到后自动关闭。'
    : '在地图上单击以拾取该点经纬度（拾取一次后自动关闭）。',
)

const showMobileMapEditorChrome = computed(
  () =>
    props.showDestinationPicker &&
    props.allowMarkerEdit &&
    showMarkerEditor.value &&
    isCoarsePointer.value,
)

const dragHintText = computed(() => {
  const coarseEditorNoPick =
    isCoarsePointer.value &&
    props.allowMarkerEdit &&
    showMarkerEditor.value &&
    !mapPickActive.value
  const scrollHint = coarseEditorNoPick
    ? ' 单指拖地图平移已暂时关闭，可先上下滑动页面；收起「编辑标记位置」后再拖地图。'
    : ''
  if (currentPresetLocked.value) {
    return (
      '当前点已锁定：不可拖动或地图选点；需要移动时请点「解锁拖动」，或直接在上方改经纬度后点「保存当前标记」。' +
      scrollHint
    )
  }
  const base = isCoarsePointer.value
    ? '按住标记拖动可改位置（拖动时地图暂时不能平移，松手后恢复）；改完请点击「保存当前标记」。'
    : '提示：可拖动标记修改位置；改完请点「保存当前标记」写入列表。'
  return base + scrollHint
})

/** 粗指针 + 展开编辑时暂时关闭地图单指平移，避免整块地图抢走纵向滑动、整页无法滚动 */
function syncMapPanForCoarseEditor() {
  if (!mapRaw) return
  const suppressMapPan =
    isCoarsePointer.value &&
    props.allowMarkerEdit &&
    showMarkerEditor.value &&
    !mapPickActive.value
  try {
    mapRaw.setStatus?.({ dragEnable: !suppressMapPan })
  } catch {
    /* ignore */
  }
}

watch(
  [isCoarsePointer, showMarkerEditor, mapPickActive, () => props.allowMarkerEdit, mapReady],
  () => {
    if (!mapReady.value) return
    syncMapPanForCoarseEditor()
  },
)

watch(
  presetMarkers,
  (list) => {
    if (list.length === 0) closePresetCombo()
    if (selectedPresetIndex.value >= list.length) {
      selectedPresetIndex.value = Math.max(0, list.length - 1)
    }
    if (mapRaw && amapNS) {
      if (list.length > 0) {
        installPresetOverlays(amapNS)
      } else {
        destroyPresetOverlays()
      }
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
/** 预设点对应的多个标记（与 mainMarker 二选一：有预设列表时只用这批） */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let presetOverlayMarkers: any[] = []
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let geolocationRaw: any = null

function escapeLabelHtml(s: string) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function buildMarkerLabelHtml(text: string) {
  const t = escapeLabelHtml(text)
  return `<span style="display:inline-block;padding:4px 10px;background:rgba(253,252,247,.96);border:none;border-radius:8px;font-size:12px;font-weight:600;color:#2c2825;white-space:nowrap;box-shadow:0 2px 10px rgba(20,20,19,.1);">${t}</span>`
}

/** 可拖动时开启 raiseOnDrag，标签需额外上移，否则拖动抬起时常与图标重叠 */
const MARKER_LABEL_OFFSET_Y_LOCKED = -8
const MARKER_LABEL_OFFSET_Y_DRAGGABLE = -44

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildMarkerLabelOptions(AMap: any, name: string, canDrag: boolean) {
  return {
    content: buildMarkerLabelHtml(name),
    direction: 'top' as const,
    offset: new AMap.Pixel(0, canDrag ? MARKER_LABEL_OFFSET_Y_DRAGGABLE : MARKER_LABEL_OFFSET_Y_LOCKED),
  }
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

// 标记位置编辑功能
function applyMarkerEdit() {
  if (!props.allowMarkerEdit) return
  const lng = parseFloat(editLng.value)
  const lat = parseFloat(editLat.value)
  if (Number.isNaN(lng) || Number.isNaN(lat)) {
    alert('请输入有效的经纬度数值')
    return
  }
  const name = editName.value.trim()
  if (!name) {
    alert('请填写标记名称')
    return
  }
  const idx = selectedPresetIndex.value
  if (idx < 0 || idx >= presetMarkers.value.length) return
  const next = presetMarkers.value.map((p, i) => (i === idx ? { ...p, name, lng, lat } : p))
  presetMarkers.value = next
  navTarget.value = { lng, lat, name }
  editableMarker.value = { lng, lat, name }
  updateEditableMarker(lng, lat)
}

function syncEditorFromSelectedPreset() {
  const p = presetMarkers.value[selectedPresetIndex.value]
  if (!p) return
  editName.value = p.name
  editLng.value = p.lng.toFixed(6)
  editLat.value = p.lat.toFixed(6)
  navTarget.value = { lng: p.lng, lat: p.lat, name: p.name }
}

function addPresetMarkerPoint() {
  if (!props.allowMarkerEdit) return
  let lng = DEFAULT_MARKER_LNG_LAT[0]
  let lat = DEFAULT_MARKER_LNG_LAT[1]
  const c = mapRaw?.getCenter?.()
  if (c && typeof c.getLng === 'function' && typeof c.getLat === 'function') {
    lng = c.getLng()
    lat = c.getLat()
  }
  const name = `新标记${presetMarkers.value.length + 1}`
  const newMarker: PresetMarker = { name, lng, lat, locked: true }
  const newIndex = presetMarkers.value.length
  presetMarkers.value = [...presetMarkers.value, newMarker]
  selectedPresetIndex.value = newIndex
  // 与列表项同源写入表单，避免「更新列表 → 重建标记 → 误触其它点 click」抢在 sync 之前导致名称框与新建点不一致
  editName.value = name
  editLng.value = lng.toFixed(6)
  editLat.value = lat.toFixed(6)
  navTarget.value = { lng, lat, name }
  void nextTick(() => {
    const p = presetMarkers.value[newIndex]
    if (!p || p.name !== name) return
    selectedPresetIndex.value = newIndex
    syncEditorFromSelectedPreset()
  })
}

function performRemoveSelectedPresetMarker() {
  if (!props.allowMarkerEdit) return
  if (presetMarkers.value.length <= 1) return
  const idx = selectedPresetIndex.value
  presetMarkers.value = presetMarkers.value.filter((_, i) => i !== idx)
  selectedPresetIndex.value = Math.min(idx, presetMarkers.value.length - 1)
  const p = presetMarkers.value[selectedPresetIndex.value]
  if (p) applyPresetMarker(p)
}

function closeDeletePwdModal() {
  if (deletePwdVerifying.value) return
  deletePwdOpen.value = false
  deletePwdField.value = ''
}

async function submitDeletePwdModal() {
  if (deletePwdVerifying.value) return
  const pwd = deletePwdField.value
  if (!pwd) {
    alert('请输入登录密码')
    return
  }
  deletePwdVerifying.value = true
  try {
    await authApi.verifyCurrentPassword({ password: pwd })
    deletePwdVerifying.value = false
    deletePwdOpen.value = false
    deletePwdField.value = ''
    performRemoveSelectedPresetMarker()
  } catch (e) {
    deletePwdVerifying.value = false
    const msg = axios.isAxiosError(e)
      ? String(e.response?.data?.detail ?? '验证失败，请重试')
      : '验证失败，请重试'
    alert(msg)
  }
}

function onClickDeletePresetMarker() {
  if (!props.allowMarkerEdit) return
  if (presetMarkers.value.length <= 1) {
    alert('至少保留一个标记点')
    return
  }
  deletePwdField.value = ''
  deletePwdOpen.value = true
  void nextTick(() => deletePwdInputRef.value?.focus())
}

function toggleMarkerPositionLock() {
  if (!props.allowMarkerEdit) return
  const idx = selectedPresetIndex.value
  if (idx < 0 || idx >= presetMarkers.value.length) return
  const cur = presetMarkers.value[idx]
  if (!cur) return
  const wasLocked = isPresetPositionLocked(cur)
  presetMarkers.value = presetMarkers.value.map((p, i) =>
    i === idx ? { ...p, locked: !wasLocked } : p,
  )
  if (mapPickActive.value && isPresetPositionLocked(presetMarkers.value[idx])) detachMapPick()
}

function detachMapPick() {
  if (mapPickHandler && mapRaw) {
    try {
      mapRaw.off('click', mapPickHandler)
    } catch {
      /* ignore */
    }
  }
  mapPickHandler = null
  mapPickActive.value = false
  syncMapPanForCoarseEditor()
}

function toggleMapPick() {
  if (!props.allowMarkerEdit || !mapRaw) return
  if (mapPickActive.value) {
    detachMapPick()
    return
  }
  const pickIdx = selectedPresetIndex.value
  const pickCur = presetMarkers.value[pickIdx]
  if (isPresetPositionLocked(pickCur)) {
    alert('当前标记已锁定位置，请先点「解锁拖动」再使用地图选点。')
    return
  }
  lastMapPickAt = 0
  mapPickActive.value = true
  mapPickHandler = (e: any) => {
    const now = Date.now()
    if (now - lastMapPickAt < 320) return
    lastMapPickAt = now
    const idx = selectedPresetIndex.value
    if (isPresetPositionLocked(presetMarkers.value[idx])) {
      alert('当前标记已锁定，无法通过地图选点修改位置。')
      detachMapPick()
      return
    }
    const ll = e?.lnglat
    if (!ll) return
    const lng = typeof ll.getLng === 'function' ? ll.getLng() : Number(ll.lng)
    const lat = typeof ll.getLat === 'function' ? ll.getLat() : Number(ll.lat)
    if (Number.isNaN(lng) || Number.isNaN(lat)) return
    editLng.value = lng.toFixed(6)
    editLat.value = lat.toFixed(6)
    const name = editName.value.trim() || navTarget.value.name
    navTarget.value = { lng, lat, name }
    updateEditableMarker(lng, lat)
    detachMapPick()
  }
  mapRaw.on('click', mapPickHandler)
}

/** 使用高德定位获取设备当前位置（GCJ-02），填入上方经纬度框 */
function onFetchDeviceLocation() {
  if (!props.allowMarkerEdit) return
  if (!geolocationRaw) {
    alert('定位未就绪，请刷新页面后重试')
    return
  }
  deviceLocateLoading.value = true
  geolocationRaw.getCurrentPosition((status: string, result: any) => {
    deviceLocateLoading.value = false
    if (status === 'complete' && result?.position) {
      const lng = Number(result.position.lng)
      const lat = Number(result.position.lat)
      if (!Number.isNaN(lng) && !Number.isNaN(lat)) {
        editLng.value = lng.toFixed(6)
        editLat.value = lat.toFixed(6)
        return
      }
    }
    const msg =
      typeof result?.info === 'string'
        ? result.info
        : typeof result?.message === 'string'
          ? result.message
          : ''
    alert(
      msg
        ? `定位失败：${msg}`
        : '定位失败：请确认已允许浏览器定位权限，并尽量使用 HTTPS 访问（非安全上下文下浏览器可能禁止定位）',
    )
    console.warn('[amap] 获取当前位置失败', status, result)
  })
}

function updateEditableMarker(lng: number, lat: number) {
  if (mainMarker) {
    mainMarker.setPosition([lng, lat])
  }
  if (presetOverlayMarkers.length > 0) {
    const idx = Math.min(Math.max(0, selectedPresetIndex.value), presetOverlayMarkers.length - 1)
    presetOverlayMarkers[idx]?.setPosition?.([lng, lat])
  }
}

// 处理标记拖动结束事件（单标记模式 / mainMarker）
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function onMarkerDragEnd(e: any) {
  const position = e.target?.getPosition?.()
  if (position) {
    const lng = position.getLng?.() ?? position.lng ?? position[0]
    const lat = position.getLat?.() ?? position.lat ?? position[1]
    navTarget.value = { lng: Number(lng), lat: Number(lat), name: navTarget.value.name }
    editLng.value = Number(lng).toFixed(6)
    editLat.value = Number(lat).toFixed(6)
  }
}

/** 预设点标记拖拽结束：同步当前选中项、导航目标与路线 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function onPresetMarkerDragEnd(e: any, presetIndex: number) {
  if (isPresetPositionLocked(presetMarkers.value[presetIndex])) return
  syncMapPanForCoarseEditor()
  const position = e.target?.getPosition?.()
  if (!position) return
  const lng = Number(position.getLng?.() ?? position.lng ?? position[0])
  const lat = Number(position.getLat?.() ?? position.lat ?? position[1])
  if (Number.isNaN(lng) || Number.isNaN(lat)) return
  const cur = presetMarkers.value[presetIndex]
  const name = cur?.name ?? navTarget.value.name
  const next = presetMarkers.value.map((p, i) => (i === presetIndex ? { ...p, lng, lat } : p))
  presetMarkers.value = next
  selectedPresetIndex.value = presetIndex
  navTarget.value = { lng, lat, name }
  if (props.allowMarkerEdit) {
    editLng.value = lng.toFixed(6)
    editLat.value = lat.toFixed(6)
  }
}

function applyPresetMarker(p: PresetMarker) {
  navTarget.value = { lng: p.lng, lat: p.lat, name: p.name }
  if (props.allowMarkerEdit) {
    editName.value = p.name
    editLng.value = p.lng.toFixed(6)
    editLat.value = p.lat.toFixed(6)
  }
}

function destroyPresetOverlays() {
  for (const mk of presetOverlayMarkers) {
    try {
      mk.setMap(null)
    } catch {
      /* ignore */
    }
  }
  presetOverlayMarkers = []
}

function resetPresetMarkerZIndices() {
  presetOverlayMarkers.forEach((mk, i) => {
    try {
      mk.setzIndex?.(120 + i)
    } catch {
      /* ignore */
    }
  })
}

/** 在地图上一次展示全部预设点，并自适应视野 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function installPresetOverlays(AMap: any) {
  destroyPresetOverlays()
  if (!mapRaw || !presetMarkers.value.length) return
  for (let i = 0; i < presetMarkers.value.length; i++) {
    const p = presetMarkers.value[i]
    const locked = isPresetPositionLocked(p)
    const canDrag = props.allowMarkerEdit && !locked
    const mk = new AMap.Marker({
      position: [p.lng, p.lat],
      title: p.name,
      anchor: 'bottom-center',
      draggable: canDrag,
      raiseOnDrag: canDrag,
      zIndex: 120 + i,
      label: buildMarkerLabelOptions(AMap, p.name, canDrag),
    })
    if (canDrag) {
      mk.on('dragstart', () => {
        mapRaw?.setStatus({ dragEnable: false })
        try {
          mk.setzIndex?.(580)
        } catch {
          /* ignore */
        }
      })
      mk.on('dragend', (e: any) => {
        resetPresetMarkerZIndices()
        onPresetMarkerDragEnd(e, i)
      })
    }
    mk.on('click', () => {
      const cur = presetMarkers.value[i]
      if (!cur) return
      selectedPresetIndex.value = i
      applyPresetMarker(cur)
      if (props.markerNavigateOnClick) {
        openAmapNavigationTo(cur.lng, cur.lat, cur.name)
      }
    })
    mk.setMap(mapRaw)
    presetOverlayMarkers.push(mk)
  }
  syncMarkerDraggability()
}

function onPresetSelected() {
  const m = presetMarkers.value[selectedPresetIndex.value]
  if (m) applyPresetMarker(m)
}

function selectPresetFromCombo(i: number) {
  selectedPresetIndex.value = i
  onPresetSelected()
  closePresetCombo()
}

function openNavForCurrent() {
  const t = navTarget.value
  openAmapNavigationTo(t.lng, t.lat, t.name)
}

// 街道搜索功能
function searchStreet() {
  if (!placeSearchRaw || !streetSearchKeyword.value.trim()) {
    streetSearchResults.value = []
    return
  }
  placeSearchRaw.search(streetSearchKeyword.value.trim(), (status: string, result: any) => {
    if (status === 'complete' && result?.info === 'OK' && result?.poiList?.pois) {
      streetSearchResults.value = result.poiList.pois.map((poi: any) => ({
        name: poi.name,
        address: poi.address || '暂无地址信息',
        lng: Number(poi.location?.lng ?? 0),
        lat: Number(poi.location?.lat ?? 0),
      })).filter((p: { lng: number; lat: number }) => p.lng && p.lat)
    } else {
      streetSearchResults.value = []
      console.warn('[amap] 搜索未返回结果', status, result)
    }
  })
}

function selectStreetResult(item: { name: string; address: string; lng: number; lat: number }) {
  // 设置为目标点
  navTarget.value = { lng: item.lng, lat: item.lat, name: item.name }
  // 移动地图中心到该位置
  mapRaw?.setCenter?.([item.lng, item.lat])
  mapRaw?.setZoom?.(16)
  // 清除搜索结果
  streetSearchResults.value = []
  streetSearchKeyword.value = item.name
}

onMounted(async () => {
  document.addEventListener('pointerdown', onPresetComboDocPointerDown, true)
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    isCoarsePointer.value = window.matchMedia('(pointer: coarse)').matches
  }
  if (!canLoadMap.value) return
  initError.value = null
  try {
    const plugins = ['AMap.Scale', 'AMap.PlaceSearch']
    const loadGeolocation = props.allowMarkerEdit
    if (loadGeolocation) plugins.push('AMap.Geolocation')
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
      mapStyle: 'amap://styles/normal', // 使用标准样式，显示更多道路细节
      showBuildingBlock: true, // 显示3D建筑物
      features: ['bg', 'point', 'road', 'building'], // 启用所有地图要素
    })
    m.addControl(new AMap.Scale())

    defaultLayerInst =
      typeof AMap.createDefaultLayer === 'function' ? AMap.createDefaultLayer() : m.getLayers?.()?.[0] ?? null
    satelliteLayerInst = new AMap.TileLayer.Satellite()
    roadNetLayerInst = new AMap.TileLayer.RoadNet()
    trafficLayerInst = new AMap.TileLayer.Traffic({ zIndex: 110 })
    applyMapLayers()

    if (loadGeolocation) {
      geolocationRaw = new AMap.Geolocation({
        enableHighAccuracy: true,
        timeout: 15000,
        showMarker: false,
        showCircle: false,
      })
    }

    // 初始化地点搜索插件
    placeSearchRaw = new AMap.PlaceSearch({
      pageSize: 10,
      pageIndex: 1,
      extensions: 'all',
    })

    mapRaw = m

    if (presetMarkers.value.length > 0) {
      installPresetOverlays(AMap)
    } else if (props.showMarker) {
      mainMarker = new AMap.Marker({
        position: lngLat,
        title: props.markerTitle,
        anchor: 'bottom-center',
        draggable: props.allowMarkerEdit,
        raiseOnDrag: props.allowMarkerEdit,
        zIndex: 120,
        label: buildMarkerLabelOptions(AMap, props.markerTitle, props.allowMarkerEdit),
      })
      mainMarker.setMap(m)
      if (props.allowMarkerEdit) {
        mainMarker.on('dragstart', () => {
          m.setStatus({ dragEnable: false })
          try {
            mainMarker.setzIndex?.(580)
          } catch {
            /* ignore */
          }
        })
        mainMarker.on('dragend', (e: any) => {
          syncMapPanForCoarseEditor()
          try {
            mainMarker.setzIndex?.(120)
          } catch {
            /* ignore */
          }
          onMarkerDragEnd(e)
        })
      }
      // 点击导航
      if (props.markerNavigateOnClick) {
        mainMarker.on('click', () => {
          const t = navTarget.value
          openAmapNavigationTo(t.lng, t.lat, t.name)
        })
      }
    }
    mapReady.value = true
    syncMapPanForCoarseEditor()
    syncPitchFromMap()
    selectedPresetIndex.value = findInitialPresetIndex()
    const initialPreset = presetMarkers.value[selectedPresetIndex.value]
    if (initialPreset) {
      navTarget.value = { lng: initialPreset.lng, lat: initialPreset.lat, name: initialPreset.name }
    }
    if (props.allowMarkerEdit) syncEditorFromSelectedPreset()
  } catch (e) {
    console.error('[amap] 初始化失败', e)
    initError.value =
      e instanceof Error ? e.message : '地图脚本加载失败，请检查 Key / 安全密钥与域名白名单后重启 Vite'
  }
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onPresetComboDocPointerDown, true)
  detachMapPick()
  geolocationRaw = null
  placeSearchRaw = null
  destroyPresetOverlays()
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

/** 移动端：编辑与地图之间的「可滑动条」，单指上下滑交给整页滚动，避免只能挤在细缝里滑 */
.amap-mobile-page-scroll-bridge {
  display: none;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin: 0.35rem 0 0.55rem;
  padding: 0.45rem 0.65rem;
  border-radius: 10px;
  border: 1px dashed rgba(142, 132, 109, 0.38);
  background: rgba(253, 245, 238, 0.55);
  touch-action: pan-y;
  -webkit-user-select: none;
  user-select: none;
}

.amap-mobile-page-scroll-bridge__line {
  flex: 1 1 2rem;
  max-width: 4rem;
  height: 1px;
  background: rgba(142, 132, 109, 0.35);
}

.amap-mobile-page-scroll-bridge__text {
  flex: 0 0 auto;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: rgba(80, 72, 58, 0.82);
  white-space: nowrap;
}

.amap-delete-pwd-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(20, 20, 19, 0.45);
  box-sizing: border-box;
}

.amap-delete-pwd-dialog {
  width: 100%;
  max-width: 360px;
  padding: 1.1rem 1.15rem;
  border-radius: 12px;
  background: rgba(253, 252, 247, 0.99);
  border: 1px solid rgba(142, 132, 109, 0.35);
  box-shadow: 0 12px 40px rgba(20, 20, 19, 0.18);
  box-sizing: border-box;
}

.amap-delete-pwd-title {
  margin: 0 0 0.35rem;
  font-size: 1rem;
  font-weight: 700;
  color: var(--cl-charcoal, #2c2b28);
}

.amap-delete-pwd-desc {
  margin: 0 0 0.75rem;
  font-size: 0.82rem;
  line-height: 1.45;
  color: rgba(44, 43, 40, 0.72);
}

.amap-delete-pwd-input {
  width: 100%;
  box-sizing: border-box;
  min-height: 44px;
  margin-bottom: 0.85rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  border: 1px solid rgba(142, 132, 109, 0.4);
  font: inherit;
  font-size: 0.95rem;
  background: #fff;
}

.amap-delete-pwd-input:focus {
  outline: none;
  border-color: rgba(201, 100, 66, 0.55);
}

.amap-delete-pwd-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.amap-delete-pwd-btn {
  min-height: 40px;
  padding: 0.4rem 0.85rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid rgba(142, 132, 109, 0.4);
  background: rgba(255, 255, 255, 0.95);
  color: var(--cl-charcoal, #2c2b28);
  touch-action: manipulation;
}

.amap-delete-pwd-btn--danger {
  border-color: rgba(180, 60, 50, 0.45);
  background: rgba(180, 60, 50, 0.92);
  color: #fff;
}

.amap-delete-pwd-btn--danger:hover {
  background: rgba(160, 50, 45, 0.95);
}

/** 地图画布 + 叠在其上的控件；与上方搜索面板分离，保证 absolute 的 top/right 相对地图区域 */
.amap-map-stage {
  position: relative;
  width: 100%;
}

.amap-map-stage--picking .amap-host {
  box-shadow: inset 0 0 0 3px rgba(201, 100, 66, 0.38);
}

.amap-pick-banner {
  position: absolute;
  left: 50%;
  top: max(10px, env(safe-area-inset-top, 0px));
  transform: translateX(-50%);
  z-index: 520;
  padding: 0.45rem 0.95rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
  background: rgba(253, 252, 247, 0.97);
  border: 1px solid rgba(201, 100, 66, 0.5);
  box-shadow: 0 4px 18px rgba(20, 20, 19, 0.12);
  pointer-events: none;
  max-width: min(340px, calc(100% - 20px));
  text-align: center;
  line-height: 1.4;
}

/** 减少触摸拖动标记时与地图平移手势冲突（依赖高德内部仍接收触摸） */
.amap-host--can-edit :deep(.amap-marker) {
  touch-action: none;
}

.amap-missing {
  margin-bottom: 0.75rem;
  padding: 1rem 1.1rem;
  border-radius: 12px;
  border: 1px solid rgba(201, 100, 66, 0.35);
  background: rgba(253, 245, 238, 0.98);
  color: var(--cl-charcoal, #2c2b28);
  font-size: 0.875rem;
  line-height: 1.55;
}

.amap-missing--warn {
  border-color: rgba(184, 134, 11, 0.45);
  background: rgba(255, 251, 235, 0.98);
}

.amap-missing--error {
  border-color: rgba(180, 60, 50, 0.4);
  background: rgba(255, 242, 240, 0.98);
}

.amap-missing__title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 700;
}

.amap-missing__text {
  margin: 0 0 0.45rem;
}

.amap-missing__text:last-child {
  margin-bottom: 0;
}

.amap-missing__pre {
  margin: 0.35rem 0 0.65rem;
  padding: 0.65rem 0.85rem;
  overflow: auto;
  font-size: 0.8rem;
  line-height: 1.45;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(142, 132, 109, 0.22);
}

.amap-missing .muted {
  opacity: 0.88;
  font-size: 0.82rem;
}

.amap-missing code {
  font-size: 0.85em;
  padding: 0.12em 0.35em;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.75);
}

.amap-search-panel {
  margin-bottom: 0.65rem;
}

.amap-perm-hint {
  margin: 0.55rem 0 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--cl-olive, rgba(80, 72, 58, 0.85));
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

.amap-preset-combobox-wrap {
  flex: 1 1 180px;
  min-width: 0;
  position: relative;
}

.amap-preset-combobox {
  position: relative;
  width: 100%;
}

.amap-preset-combobox__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font: inherit;
  appearance: none;
  -webkit-appearance: none;
}

.amap-preset-combobox__trigger:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.amap-preset-combobox__trigger-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.amap-preset-combobox__chevron {
  flex-shrink: 0;
  font-size: 0.65rem;
  line-height: 1;
  opacity: 0.65;
}

.amap-preset-combobox--open .amap-preset-combobox__chevron {
  opacity: 0.9;
}

.amap-preset-combobox__panel {
  position: absolute;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  z-index: 640;
  padding: 0.45rem;
  border-radius: 10px;
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  background: rgba(255, 255, 255, 0.99);
  box-shadow: 0 8px 28px rgba(40, 35, 30, 0.12);
  box-sizing: border-box;
}

.amap-preset-combobox__filter {
  width: 100%;
  min-height: 40px;
  margin-bottom: 0.35rem;
  flex: none;
  box-sizing: border-box;
}

.amap-preset-combobox__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: min(40vh, 280px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.amap-preset-combobox__option {
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  line-height: 1.35;
}

.amap-preset-combobox__option:hover {
  background: rgba(201, 100, 66, 0.1);
}

.amap-preset-combobox__option--active {
  font-weight: 600;
}

.amap-preset-combobox__empty {
  padding: 0.5rem 0.55rem;
  font-size: 0.82rem;
  line-height: 1.4;
  color: var(--cl-olive, rgba(80, 72, 58, 0.85));
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

.amap-search-btn--secondary {
  background: rgba(201, 100, 66, 0.85);
  border-color: rgba(201, 100, 66, 0.55);
}

.amap-search-row--secondary {
  margin-top: 0.5rem;
}

.amap-search-field-wrap {
  flex: 1 1 180px;
  display: flex;
  gap: 0.5rem;
}

.amap-search-results {
  margin-top: 0.5rem;
  max-height: 240px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  border-radius: 10px;
  box-shadow: 0 4px 18px rgba(20, 20, 19, 0.08);
}

.amap-search-result-item {
  padding: 0.65rem 0.9rem;
  cursor: pointer;
  border-bottom: 1px solid rgba(142, 132, 109, 0.12);
  transition: background 0.15s ease;
}

.amap-search-result-item:last-child {
  border-bottom: none;
}

.amap-search-result-item:hover {
  background: rgba(253, 245, 238, 0.85);
}

.amap-result-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--cl-charcoal, #2c2b28);
  margin-bottom: 0.25rem;
}

.amap-result-address {
  font-size: 0.8rem;
  color: rgba(44, 43, 40, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.amap-marker-editor {
  margin-top: 0.5rem;
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  overflow: hidden;
}

.amap-editor-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem 0.9rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
  background: rgba(253, 245, 238, 0.6);
  transition: background 0.15s ease;
}

.amap-editor-toggle:hover {
  background: rgba(253, 245, 238, 0.9);
}

.amap-toggle-icon {
  font-size: 0.75rem;
  color: rgba(44, 43, 40, 0.6);
}

.amap-editor-panel {
  padding: 0.75rem 0.9rem;
  border-top: 1px solid rgba(142, 132, 109, 0.2);
}

.amap-editor-lock-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.5rem;
}

.amap-editor-btn--lock {
  flex: 0 0 auto;
  font-size: 0.78rem;
  padding: 0.35rem 0.65rem;
}

.amap-editor-btn--lock-on {
  background: rgba(142, 132, 109, 0.18);
  border-color: rgba(142, 132, 109, 0.42);
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
}

.amap-lock-hint {
  flex: 1 1 10rem;
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.4;
  color: rgba(44, 43, 40, 0.62);
}

.amap-editor-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
}

.amap-editor-row--coords {
  align-items: flex-end;
  gap: 0.55rem;
}

.amap-editor-coord-cell {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 0.28rem;
}

.amap-editor-coord-cell .amap-editor-label {
  align-self: flex-start;
}

.amap-editor-label {
  flex: 0 0 auto;
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(44, 43, 40, 0.85);
  min-width: 2.5rem;
}

.amap-editor-input {
  flex: 1 1 auto;
  min-width: 0;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  border: 1px solid rgba(142, 132, 109, 0.35);
  font-size: 0.85rem;
  background: rgba(255, 255, 255, 0.98);
}

.amap-editor-input:focus {
  outline: none;
  border-color: rgba(201, 100, 66, 0.55);
}

.amap-editor-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.amap-editor-actions--split {
  flex-wrap: wrap;
}

.amap-editor-btn--block {
  width: 100%;
  margin-top: 0.5rem;
  flex: none;
}

.amap-editor-btn--pick-on {
  border-color: rgba(201, 100, 66, 0.65);
  background: rgba(201, 100, 66, 0.12);
  color: var(--cl-terracotta, #c96442);
  font-weight: 600;
}

.amap-editor-tip--pick {
  font-style: normal;
  color: rgba(201, 100, 66, 0.95);
  font-weight: 500;
}

.amap-editor-btn {
  flex: 1 1 auto;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  border: 1px solid rgba(142, 132, 109, 0.35);
  background: rgba(255, 255, 255, 0.95);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.amap-editor-btn:hover:not(:disabled) {
  background: rgba(253, 245, 238, 0.85);
  border-color: rgba(201, 100, 66, 0.45);
}

.amap-editor-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.amap-editor-btn--primary {
  background: var(--cl-terracotta, #c96442);
  border-color: rgba(201, 100, 66, 0.55);
  color: #fff;
}

.amap-editor-btn--primary:hover:not(:disabled) {
  background: rgba(201, 100, 66, 0.9);
}

.amap-editor-tip {
  margin: 0.6rem 0 0;
  font-size: 0.75rem;
  color: rgba(44, 43, 40, 0.6);
  font-style: italic;
}

.amap-layer-tools {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 500;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  max-width: min(220px, calc(100% - 24px));
}

.amap-layer-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  border: 1px solid rgba(142, 132, 109, 0.35);
  background: rgba(253, 252, 247, 0.95);
  color: var(--cl-charcoal, #2c2b28);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.4rem 0.65rem;
  border-radius: 8px;
  box-shadow: 0 4px 18px rgba(20, 20, 19, 0.08);
  line-height: 1.2;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.amap-layer-toggle:hover {
  background: rgba(245, 229, 218, 0.45);
  border-color: rgba(201, 100, 66, 0.35);
}

.amap-layer-chevron {
  font-size: 0.65rem;
  opacity: 0.75;
}

.amap-layer-panel {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(253, 252, 247, 0.96);
  border: 1px solid rgba(142, 132, 109, 0.22);
  box-shadow: 0 4px 18px rgba(20, 20, 19, 0.08);
  min-width: 9.5rem;
}

.amap-layer-section {
  margin-bottom: 10px;
}

.amap-layer-section:last-child {
  margin-bottom: 0;
}

.amap-layer-section-title {
  font-size: 0.72rem;
  font-weight: 700;
  color: rgba(44, 43, 40, 0.55);
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}

.amap-layer-option {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  margin-bottom: 6px;
  cursor: pointer;
  color: var(--cl-charcoal, #2c2b28);
}

.amap-layer-option:last-child {
  margin-bottom: 0;
}

.amap-layer-option input {
  flex-shrink: 0;
}

.amap-host {
  width: 100%;
  height: clamp(300px, 62vh, 620px);
  min-height: 280px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
}

/* 高德默认给 label 外包一层带蓝框的 .amap-marker-label，此处去掉 */
.amap-host :deep(.amap-marker-label) {
  border: none !important;
  background: transparent !important;
  padding: 0 !important;
  box-shadow: none !important;
  outline: none !important;
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

  /** 展开编辑时：整块控制区与地图之间分层更明显 */
  .amap-search-panel--editor-open {
    margin-bottom: 0.85rem;
    padding-bottom: 0.35rem;
    border-bottom: 2px solid rgba(201, 100, 66, 0.32);
    box-shadow: 0 10px 22px rgba(20, 20, 19, 0.1);
  }

  .amap-wrap:has(.amap-search-panel--editor-open) .amap-map-stage {
    margin-top: 2px;
    padding-top: 1px;
    border-top: 1px solid rgba(142, 132, 109, 0.38);
    box-shadow: inset 0 3px 0 rgba(253, 252, 247, 0.95);
  }

  .amap-marker-editor {
    margin-top: 0.35rem;
    border-radius: 8px;
    box-shadow: 0 2px 0 rgba(44, 43, 40, 0.06);
    touch-action: pan-y;
  }

  /** 展开编辑时不再用内层滚动「锁住」整页：在表单、空白处上下滑交给外层页面 */
  .amap-search-panel--editor-open .amap-editor-panel {
    max-height: none;
    overflow-y: visible;
    -webkit-overflow-scrolling: auto;
  }

  .amap-editor-panel {
    max-height: min(38vh, 300px);
    overflow-y: auto;
    padding: 0.42rem 0.55rem 0.48rem;
    -webkit-overflow-scrolling: touch;
  }

  .amap-mobile-page-scroll-bridge {
    display: flex;
  }

  .amap-editor-row {
    margin-bottom: 0.32rem;
    gap: 0.3rem;
  }

  .amap-editor-row--coords {
    gap: 0.4rem;
    margin-bottom: 0.35rem;
  }

  .amap-editor-coord-cell {
    gap: 0.2rem;
  }

  .amap-editor-toggle {
    min-height: 38px;
    padding: 0.42rem 0.65rem;
    font-size: 0.8rem;
  }

  .amap-editor-btn {
    min-height: 36px;
    padding: 0.32rem 0.48rem;
    font-size: 0.76rem;
  }

  .amap-editor-btn--lock {
    min-height: 34px;
    padding: 0.28rem 0.48rem;
    font-size: 0.72rem;
  }

  .amap-editor-actions {
    margin-top: 0.35rem;
    gap: 0.3rem;
  }

  .amap-editor-btn--block {
    margin-top: 0.35rem;
  }

  .amap-editor-input {
    min-height: 40px;
    padding: 0.3rem 0.45rem;
    font-size: 16px;
  }

  .amap-editor-label {
    align-self: flex-start;
    min-width: 0;
    font-size: 0.72rem;
  }

  .amap-editor-row:not(.amap-editor-row--coords) .amap-editor-label {
    align-self: center;
  }

  .amap-editor-tip {
    margin: 0.35rem 0 0;
    font-size: 0.64rem;
    line-height: 1.4;
  }

  .amap-editor-lock-row {
    margin-bottom: 0.32rem;
    gap: 0.3rem;
  }

  .amap-lock-hint {
    flex: 1 1 100%;
    font-size: 0.62rem;
    line-height: 1.35;
  }

  .amap-host {
    height: clamp(360px, 78vh, 88svh);
    min-height: 360px;
    border-radius: 8px;
  }

  /** 展开编辑时略压低地图高度，留出更多整页滚动空间，并与临时关闭单指拖图配合 */
  .amap-wrap:has(.amap-search-panel--editor-open) .amap-host {
    height: clamp(220px, 46svh, 52vh);
    min-height: 200px;
    max-height: min(52vh, 420px);
  }

  .amap-driving-panel {
    margin-top: 0.45rem;
    max-height: min(20vh, 180px);
    border-radius: 8px;
  }

  .amap-layer-tools {
    top: 8px;
    right: 8px;
    max-width: min(200px, calc(100% - 56px));
  }

  .amap-layer-panel {
    min-width: 0;
    width: 100%;
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
