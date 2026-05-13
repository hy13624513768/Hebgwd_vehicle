<template>
  <div class="loc-nav">
    <header class="loc-nav__head">
      <h1 class="loc-nav__title">段内导航</h1>
      <p class="loc-nav__desc muted">
        基于高德地图 JSAPI，支持检索与高德导航跳转。
      </p>
      <p v-if="presetsLoadError" class="loc-nav__warn" role="alert">{{ presetsLoadError }}</p>
    </header>
    <AmapContainer
      v-model:preset-markers="navPresetMarkers"
      class="loc-nav__map"
      :marker-navigate-on-click="false"
      :allow-marker-edit="canEditMapLocations"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { fetchNavPresets, replaceNavPresets } from '@/api/navPresets'
import AmapContainer from '@/components/AmapContainer.vue'
import { DEFAULT_PRESET_MARKERS, type PresetMarker } from '@/lib/amapPresets'
import { usePermissions } from '@/composables/usePermissions'

function cloneDefaults(): PresetMarker[] {
  return DEFAULT_PRESET_MARKERS.map((p) => ({ ...p }))
}

const navPresetMarkers = ref<PresetMarker[]>(cloneDefaults())
const presetsLoadError = ref<string | null>(null)
const presetsHydrated = ref(false)
const { canEditMapLocations } = usePermissions()

onMounted(async () => {
  try {
    const markers = await fetchNavPresets()
    navPresetMarkers.value = markers.length > 0 ? markers : cloneDefaults()
  } catch {
    presetsLoadError.value = '无法从服务器加载预设点，已暂时使用默认位置。请检查网络或重新登录。'
    navPresetMarkers.value = cloneDefaults()
  } finally {
    presetsHydrated.value = true
  }
})

let saveTimer: ReturnType<typeof setTimeout> | null = null
watch(
  navPresetMarkers,
  (v) => {
    if (!presetsHydrated.value || !canEditMapLocations.value) return
    if (v.length === 0) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      void replaceNavPresets(v).catch(() => {
        alert('保存预设点到服务器失败，请检查网络或权限后重试')
      })
    }, 650)
  },
  { deep: true },
)
</script>

<style scoped>
.loc-nav {
  width: 100%;
  max-width: min(1200px, 100%);
  margin: 0 auto;
}

.loc-nav__head {
  margin-bottom: 1rem;
}

.loc-nav__title {
  margin: 0 0 0.35rem;
  font-size: clamp(1.1rem, 2.5vw, 1.35rem);
  font-weight: 600;
}

.loc-nav__desc {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
}

.loc-nav__warn {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  color: #a63d2d;
}

.loc-nav__desc code {
  font-size: 0.8em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(142, 132, 109, 0.12);
}

.muted {
  color: var(--cl-olive);
}
</style>
