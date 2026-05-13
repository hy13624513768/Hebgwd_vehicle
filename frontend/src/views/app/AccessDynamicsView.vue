<template>
  <div class="access-page">
    <header class="access-page__head">
      <h1 class="access-page__title">通行动态</h1>
      <p class="access-page__desc muted">
        可展示 ETC、园区/门禁通行、路桥费用等与通行相关的汇总与流水。下方提供发票类凭证的 AI 识别入口（演示），便于后续与通行费用对账。
      </p>
    </header>

    <InvoiceRecognitionPanel />
  </div>
</template>

<script setup lang="ts">
import InvoiceRecognitionPanel from '@/components/InvoiceRecognitionPanel.vue'
</script>

<style scoped>
.access-page {
  width: 100%;
  max-width: min(1200px, 100%);
  margin: 0 auto;
}

.access-page__head {
  margin-bottom: 0.25rem;
}

.access-page__title {
  margin: 0 0 0.35rem;
  font-size: clamp(1.1rem, 2.5vw, 1.35rem);
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
}

.access-page__desc {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.55;
  max-width: 48rem;
}

.muted {
  color: var(--cl-olive, #6b6558);
}
</style>
