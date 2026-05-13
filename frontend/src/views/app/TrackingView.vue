<template>
  <div class="tracking">
    <header class="tracking__head">
      <h1 class="tracking__title">定位管理</h1>
      <p class="tracking__desc muted">
        演示地图容器；后续可接入车辆实时位置、历史轨迹与电子围栏。与导航模块共用高德环境变量。
      </p>
    </header>
    <AmapContainer v-model:preset-markers="trackingPresets" :zoom="11" class="tracking__map" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import AmapContainer from '@/components/AmapContainer.vue'
import type { PresetMarker } from '@/lib/amapPresets'

const trackingPresets = ref<PresetMarker[]>([])
</script>

<style scoped>
.tracking {
  width: 100%;
  max-width: min(1200px, 100%);
  margin: 0 auto;
}

.tracking__head {
  margin-bottom: 1rem;
}

.tracking__title {
  margin: 0 0 0.35rem;
  font-size: clamp(1.1rem, 2.5vw, 1.35rem);
  font-weight: 600;
}

.tracking__desc {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
}

.muted {
  color: var(--cl-olive);
}
</style>
