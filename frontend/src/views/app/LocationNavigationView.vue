<template>
  <div class="loc-nav">
    <header class="loc-nav__head">
      <h1 class="loc-nav__title">段内导航</h1>
      <p class="loc-nav__desc muted">
        基于高德地图 JSAPI，可扩展检索、定位与路径规划。密钥来自本地 <code>.env.local</code>，勿提交版本库。
      </p>
    </header>
    <AmapContainer class="loc-nav__map" show-driving-route use-realtime-origin />
  </div>
</template>

<script setup lang="ts">
import AmapContainer from '@/components/AmapContainer.vue'
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
