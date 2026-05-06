<template>
  <div class="slider" ref="root">
    <div class="slider-bg" :style="{ width: `${fillWidth}px` }" />
    <div
      class="slider-handle"
      :style="{ left: `${handleLeft}px` }"
      @pointerdown="onPointerDown"
    >
      &gt;&gt;
    </div>
    <div class="slider-tip">{{ tip }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import * as authApi from '@/api/auth'

/** 与样式一致；略大于 44px 便于手机点击 */
const HANDLE_W = 52

const props = defineProps<{ sessionId: string }>()
const emit = defineEmits<{ (e: 'ready'): void }>()

const root = ref<HTMLElement | null>(null)
const dragging = ref(false)
const handleLeft = ref(0)
const verified = ref(false)
const tip = ref('拖动滑块验证')
const activePointerId = ref<number | null>(null)

let removeDocListeners: (() => void) | null = null

const maxTravel = computed(() => {
  const el = root.value
  if (!el) return 0
  return Math.max(0, el.clientWidth - HANDLE_W)
})

const fillWidth = computed(() => Math.min(handleLeft.value + HANDLE_W, root.value?.clientWidth ?? 0))

function reset() {
  if (removeDocListeners) {
    removeDocListeners()
    removeDocListeners = null
  }
  dragging.value = false
  activePointerId.value = null
  handleLeft.value = 0
  verified.value = false
  tip.value = '拖动滑块验证'
}

watch(
  () => props.sessionId,
  () => {
    reset()
  },
)

function onPointerDown(ev: PointerEvent) {
  if (verified.value || dragging.value) return
  if (ev.button !== 0) return

  const handleEl = ev.currentTarget as HTMLElement
  const el = root.value
  if (!el) return

  ev.preventDefault()

  try {
    handleEl.setPointerCapture(ev.pointerId)
  } catch {
    /* 个别环境下可能失败，仍尝试用 document 跟踪 */
  }

  dragging.value = true
  activePointerId.value = ev.pointerId

  const onMove = (e: PointerEvent) => {
    if (e.pointerId !== activePointerId.value || !dragging.value) return
    e.preventDefault()
    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left - HANDLE_W / 2
    handleLeft.value = Math.max(0, Math.min(x, maxTravel.value))
  }

  const finishDrag = async (e: PointerEvent) => {
    if (e.pointerId !== activePointerId.value) return

    dragging.value = false
    activePointerId.value = null

    try {
      handleEl.releasePointerCapture(e.pointerId)
    } catch {
      /* 已释放或无效 */
    }

    if (removeDocListeners) {
      removeDocListeners()
      removeDocListeners = null
    }

    if (handleLeft.value >= maxTravel.value * 0.98) {
      try {
        await authApi.completeSliderSession(props.sessionId)
        verified.value = true
        tip.value = '验证成功'
        emit('ready')
      } catch {
        tip.value = '验证失败，请重试'
        handleLeft.value = 0
      }
    } else {
      handleLeft.value = 0
      tip.value = '拖动滑块验证'
    }
  }

  const opts = { capture: true, passive: false } as const
  document.addEventListener('pointermove', onMove, opts)
  document.addEventListener('pointerup', finishDrag, opts)
  document.addEventListener('pointercancel', finishDrag, opts)

  removeDocListeners = () => {
    document.removeEventListener('pointermove', onMove, opts)
    document.removeEventListener('pointerup', finishDrag, opts)
    document.removeEventListener('pointercancel', finishDrag, opts)
  }
}

onBeforeUnmount(() => {
  reset()
})
</script>

<style scoped>
.slider {
  position: relative;
  width: 100%;
  height: 50px;
  border-radius: 12px;
  background: var(--cl-warm-sand);
  overflow: hidden;
  user-select: none;
  -webkit-user-select: none;
  margin-top: 20px;
  box-shadow: inset 0 0 0 1px var(--cl-border-cream);
  touch-action: none;
  -webkit-tap-highlight-color: transparent;
}

.slider-bg {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: rgba(201, 100, 66, 0.22);
  z-index: 1;
}

.slider-handle {
  /* 宽度与脚本中 HANDLE_W 保持一致 */
  width: 52px;
  position: absolute;
  left: 0;
  top: 0;
  height: 46px;
  line-height: 46px;
  border: 1px solid var(--cl-border-warm);
  background: var(--cl-white);
  z-index: 3;
  cursor: grab;
  touch-action: none;
  color: var(--cl-terracotta);
  font-size: 14px;
  font-weight: 600;
  border-radius: 10px;
  margin: 2px;
  box-shadow: var(--cl-white) 0px 0px 0px 0px, var(--cl-ring-warm) 0px 0px 0px 1px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slider-handle:active {
  cursor: grabbing;
}

.slider-tip {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--cl-stone);
  z-index: 2;
  pointer-events: none;
}
</style>
