<template>
  <div>
    <p class="hint">导出为 UTF-8 CSV（含 BOM），可用 Excel 直接打开。仅管理员或车管可使用。</p>
    <div v-if="!canExportReports" class="msg">当前账号无导出权限。</div>
    <div v-else class="grid">
      <button type="button" class="tile" @click="run(reportExports.vehicles)">车辆档案</button>
      <button type="button" class="tile" @click="run(reportExports.drivers)">驾驶员档案</button>
      <button type="button" class="tile" @click="run(reportExports.trips)">用车申请</button>
      <button type="button" class="tile" @click="run(reportExports.maintenance)">维修保养</button>
      <button type="button" class="tile" @click="run(reportExports.fuelCards)">油卡档案</button>
      <button type="button" class="tile" @click="run(reportExports.fuelRecords)">加油流水</button>
      <button type="button" class="tile primary" @click="run(reportExports.summary)">汇总一行表</button>
    </div>
    <div v-if="msg" class="msg">{{ msg }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { reportExports } from '@/api/reports'
import { usePermissions } from '@/composables/usePermissions'

const { canExportReports } = usePermissions()
const msg = ref('')

async function run(fn: () => Promise<void>) {
  msg.value = ''
  try {
    await fn()
  } catch {
    msg.value = '导出失败，请确认已登录且账号具备导出权限'
  }
}
</script>

<style scoped>
.hint {
  margin: 0 0 12px 0;
  color: var(--cl-olive);
  font-size: 13px;
  line-height: 1.6;
}

.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

@media (max-width: 1000px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.tile {
  position: relative;
  cursor: pointer;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  color: var(--cl-near-black);
  padding: 14px 12px;
  font-weight: 500;
  font-size: 13px;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.12s ease;
}

.tile:hover {
  border-color: rgba(201, 100, 66, 0.36);
  box-shadow: rgba(0, 0, 0, 0.08) 0px 6px 28px;
  transform: translateY(-1px);
}

.tile:focus-visible {
  outline: 2px solid rgba(201, 100, 66, 0.55);
  outline-offset: 2px;
}

.tile.primary {
  border-color: var(--cl-border-cream);
  background: var(--cl-ivory);
  color: var(--cl-near-black);
}

.tile.primary::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 3px;
  background: rgba(201, 100, 66, 0.5);
}

.msg {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.08);
  color: var(--cl-error);
  font-size: 13px;
}
</style>
