<template>
  <div v-if="open" class="mask" @click.self="emit('close')">
    <div class="panel" role="dialog" aria-modal="true">
      <div class="hd">
        <div class="ttl">{{ title }}</div>
        <button type="button" class="x" @click="emit('close')">×</button>
      </div>
      <div class="bd">
        <slot />
      </div>
      <div class="ft">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ open: boolean; title: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  background: rgba(20, 20, 19, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: max(12px, env(safe-area-inset-top, 0px)) max(14px, env(safe-area-inset-right, 0px))
    max(12px, env(safe-area-inset-bottom, 0px)) max(14px, env(safe-area-inset-left, 0px));
  z-index: 220;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.panel {
  width: min(720px, 100%);
  max-height: min(88dvh, calc(100dvh - 2 * max(12px, env(safe-area-inset-top, 0px))));
  display: flex;
  flex-direction: column;
  margin: auto;
  border-radius: 16px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  color: var(--cl-near-black);
  box-shadow: rgba(0, 0, 0, 0.08) 0px 8px 32px;
}

.hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 16px 12px 18px;
  border-bottom: 1px solid var(--cl-border-cream);
}

.ttl {
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-weight: 500;
  font-size: 1.15rem;
  line-height: 1.2;
}

.x {
  cursor: pointer;
  border: 0;
  background: transparent;
  color: var(--cl-stone);
  font-size: 22px;
  line-height: 1;
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 8px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.x:hover {
  color: var(--cl-near-black);
  background: var(--cl-warm-sand);
}

.bd {
  padding: 16px 18px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.ft {
  padding: 14px 18px max(18px, env(safe-area-inset-bottom, 0px));
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  border-top: 1px solid var(--cl-border-cream);
  flex-shrink: 0;
}

@media (max-width: 560px) {
  .mask {
    align-items: flex-end;
    padding-bottom: 0;
  }

  .panel {
    width: 100%;
    max-height: min(92dvh, 100dvh);
    border-radius: 16px 16px 0 0;
    margin: 0;
  }

  .hd {
    padding-top: max(14px, env(safe-area-inset-top, 0px));
  }
}
</style>
