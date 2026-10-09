<template>
  <div v-if="message" class="fuel-query-status" :class="{ 'is-active': active }" role="status" aria-live="polite" aria-atomic="true">
    <template v-if="active">
      <div class="status-heading"><span class="status-spinner" aria-hidden="true" /><strong>{{ title }}</strong><span class="status-time">已用时 {{ elapsed }} 秒</span></div>
      <p class="status-message">{{ message }}</p>
      <p class="status-hint">{{ waitingForCode ? '验证码由系统自动读取，请等待短信转发至邮箱。' : '查询正在进行，请稍候。' }}</p>
    </template>
    <span v-else>{{ message }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{ message: string; active: boolean; title: string }>()
const elapsed = ref(0)
const waitingForCode = computed(() => /等待验证码|验证码送达|验证码邮件|短信转发/.test(props.message))
let timer: ReturnType<typeof setInterval> | undefined
watch(() => props.active, (active) => {
  clearInterval(timer)
  if (!active) return
  elapsed.value = 0
  const started = Date.now()
  timer = setInterval(() => { elapsed.value = Math.floor((Date.now() - started) / 1000) }, 1000)
}, { immediate: true })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.fuel-query-status { margin-bottom: 10px; padding: 8px 12px; border: 1px solid var(--cl-border-cream); border-radius: 8px; background: var(--cl-warm-sand); color: var(--cl-charcoal); font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
.fuel-query-status.is-active { padding: 14px; border-color: var(--cl-brand); border-left-width: 4px; background: var(--cl-white); }
.status-heading { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; color: var(--cl-brand); }
.status-heading strong { font-size: 14px; }
.status-time { margin-left: auto; color: var(--cl-olive); font-size: 12px; }
.status-message { margin: 10px 0 4px; font-size: 14px; font-weight: 600; }
.status-hint { margin: 0; color: var(--cl-olive); font-size: 12px; }
.status-spinner { width: 15px; height: 15px; border: 2px solid var(--cl-border-cream); border-top-color: var(--cl-brand); border-radius: 50%; animation: status-spin .8s linear infinite; }
@keyframes status-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .status-spinner { animation: none; } }
</style>
