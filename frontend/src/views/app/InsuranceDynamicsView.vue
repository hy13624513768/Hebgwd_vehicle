<template>
  <div class="placeholder-view">
    <p class="muted">
      保险动态：可展示保单到期提醒、理赔与续保状态等。当前为占位页面，对接保险数据后可在此扩展。
    </p>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.placeholder-view {
  max-width: 42rem;
  line-height: 1.6;
}

.muted {
  color: var(--cl-olive);
  font-size: 13px;
}
</style>
