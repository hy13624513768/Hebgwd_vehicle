<template>
  <div class="maintenance-view">
    <header class="page-head">
      <div>
        <h1 class="page-title">维修保养</h1>
        <p class="page-desc muted">
          展示驾驶员在「维修记录」页上传并经 AI 识别的结算单，明细已按<strong>维修词条</strong>自动归类。管理员可「上传样例测试」从本机逐张选图试识别。
        </p>
      </div>
      <div v-if="categoryTotals && Object.keys(categoryTotals).length" class="cat-totals">
        <span v-for="(amt, cat) in categoryTotals" :key="cat" class="cat-pill">
          {{ cat }}：￥{{ fmtMoney(amt) }}
        </span>
      </div>
    </header>

    <div class="toolbar">
      <select v-model.number="vehicleFilter" class="sel" @change="reload">
        <option :value="0">全部车辆</option>
        <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}</option>
      </select>
      <select v-model="statusFilter" class="sel" @change="reload">
        <option value="">全部状态</option>
        <option value="done">已识别</option>
        <option value="failed">识别失败</option>
        <option value="pending">待识别</option>
      </select>
      <button type="button" class="ghost" :disabled="loading" @click="reload">刷新</button>
      <template v-if="canManageFleet">
        <input
          ref="sampleFileInput"
          type="file"
          accept="image/jpeg,image/jpg,image/png,image/webp"
          class="sample-file-input"
          @change="onSampleFilePicked"
        />
        <button type="button" class="primary" :disabled="uploadingSample" @click="pickSampleFile">
          {{ uploadingSample ? '识别中…' : '上传样例测试' }}
        </button>
      </template>
    </div>

    <div v-if="msg" class="msg" :class="msgKind === 'ok' ? 'msg--ok' : 'msg--err'">{{ msg }}</div>
    <div v-if="loading" class="hint">加载中…</div>
    <div v-else-if="!rows.length" class="hint">
      暂无结算单数据。请让驾驶员在「维修记录」页上传结算单，或点击「上传样例测试」从本机选一张图片试识别。
    </div>

    <table v-else class="tbl tbl--desktop">
      <thead>
        <tr>
          <th>车牌</th>
          <th>单号</th>
          <th>日期</th>
          <th>金额</th>
          <th>里程</th>
          <th>大类汇总</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td class="strong">{{ r.plate_number }}</td>
          <td>{{ r.order_no || '—' }}</td>
          <td>{{ r.service_date ? fmtDate(r.service_date) : '—' }}</td>
          <td>￥{{ r.total_amount }}</td>
          <td>{{ r.mileage_in ? `${r.mileage_in} km` : '—' }}</td>
          <td class="cat-cell">
            <span v-for="(amt, cat) in r.category_summary" :key="`${r.id}-${cat}`" class="cat-tag">
              {{ cat }} {{ fmtMoney(amt) }}
            </span>
          </td>
          <td><span class="status" :class="`status--${r.recognition_status}`">{{ statusLabel(r.recognition_status) }}</span></td>
          <td><button type="button" class="link" @click="openDetail(r.id)">明细</button></td>
        </tr>
      </tbody>
    </table>

    <ul v-if="!loading && rows.length" class="settle-cards">
      <li v-for="r in rows" :key="`m-${r.id}`" class="settle-card">
        <div class="settle-card__top">
          <strong>{{ r.plate_number }}</strong>
          <span>￥{{ r.total_amount }}</span>
        </div>
        <p class="muted">{{ r.order_no }} · {{ r.service_date ? fmtDate(r.service_date) : '日期未知' }}</p>
        <div class="cat-tags">
          <span v-for="(amt, cat) in r.category_summary" :key="`${r.id}-m-${cat}`" class="cat-tag">{{ cat }} {{ fmtMoney(amt) }}</span>
        </div>
        <button type="button" class="link" @click="openDetail(r.id)">查看明细与归类</button>
      </li>
    </ul>

    <AppModal :open="detailOpen" title="结算单明细与词条归类" @close="detailOpen = false">
      <div v-if="detailLoading" class="hint">加载明细…</div>
      <template v-else-if="detail">
        <div class="detail-meta">
          <p><strong>车牌</strong> {{ detail.plate_number }} · <strong>单号</strong> {{ detail.order_no }}</p>
          <p><strong>车型</strong> {{ detail.vehicle_model || '—' }} · <strong>里程</strong> {{ detail.mileage_in }} km</p>
          <p><strong>合计</strong> ￥{{ detail.total_amount }}</p>
        </div>
        <table class="tbl tbl-detail">
          <thead>
            <tr>
              <th>项目</th>
              <th>金额</th>
              <th>一级大类</th>
              <th>二级子类</th>
              <th>匹配词条</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in detail.lines" :key="line.id">
              <td>{{ line.item_name }}{{ line.part_name ? ` / ${line.part_name}` : '' }}</td>
              <td>￥{{ line.amount }}</td>
              <td>{{ line.category_l1 || '—' }}</td>
              <td>{{ line.category_l2 || '—' }}</td>
              <td>
                {{ line.term_name || '—' }}
                <span v-if="line.match_score" class="match-score">({{ line.match_score }}%)</span>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
      <template #footer>
        <button type="button" class="primary" @click="detailOpen = false">关闭</button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import * as repairApi from '@/api/repairRecords'
import type { RepairSettlement, SettlementSummary } from '@/api/repairRecords'
import * as vapi from '@/api/vehicles'
import AppModal from '@/components/AppModal.vue'
import { usePermissions } from '@/composables/usePermissions'
import type { Vehicle } from '@/api/types'
import { fmtDate } from '@/utils/format'

const { canManageFleet } = usePermissions()

const loading = ref(true)
const uploadingSample = ref(false)
const sampleFileInput = ref<HTMLInputElement | null>(null)
const rows = ref<SettlementSummary[]>([])
const categoryTotals = ref<Record<string, number>>({})
const vehicles = ref<Vehicle[]>([])
const vehicleFilter = ref(0)
const statusFilter = ref('')
const msg = ref('')
const msgKind = ref<'ok' | 'err'>('err')

const detailOpen = ref(false)
const detailLoading = ref(false)
const detail = ref<RepairSettlement | null>(null)

function fmtMoney(v: number | string) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function statusLabel(s: string) {
  const m: Record<string, string> = {
    done: '已识别',
    failed: '失败',
    pending: '待识别',
    processing: '识别中',
  }
  return m[s] || s
}

async function reload() {
  loading.value = true
  if (!uploadingSample.value) msg.value = ''
  try {
    const [vs, res] = await Promise.all([
      vapi.listVehicles({ limit: 200 }),
      repairApi.listSettlementSummaries({
        vehicle_id: vehicleFilter.value || undefined,
        recognition_status: statusFilter.value || undefined,
        limit: 100,
      }),
    ])
    vehicles.value = vs
    rows.value = res.items
    categoryTotals.value = res.category_totals
  } catch {
    msgKind.value = 'err'
    msg.value = '加载结算单失败'
  } finally {
    loading.value = false
  }
}

async function openDetail(settlementId: number) {
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await repairApi.getSettlementDetail(settlementId)
  } catch {
    msg.value = '加载结算明细失败'
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

function pickSampleFile() {
  if (!vehicles.value.length) {
    msgKind.value = 'err'
    msg.value = '请先在「车辆管理」中登记至少一辆车'
    return
  }
  sampleFileInput.value?.click()
}

async function onSampleFilePicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  uploadingSample.value = true
  msg.value = '正在上传并识别，大约需要 30～60 秒…'
  msgKind.value = 'ok'
  try {
    const record = await repairApi.uploadSettlementTest(file, vehicleFilter.value || undefined)
    const st = record.settlement
    const lines = st?.lines?.length ?? 0
    if (st?.recognition_status === 'done') {
      msgKind.value = 'ok'
      msg.value = `识别完成：${st.plate_number || record.plate_number} · ${lines} 项明细 · 合计 ￥${st.total_amount}`
      await reload()
      if (st.id) await openDetail(st.id)
    } else {
      msgKind.value = 'err'
      msg.value = st?.recognition_error || '识别未完成，请换一张更清晰的图片重试'
      await reload()
    }
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; data?: { detail?: string } }; code?: string }
    msgKind.value = 'err'
    if (e.response?.status === 401) {
      msg.value = '登录已过期或未登录，请退出后重新登录，再试上传'
    } else if (e.code === 'ECONNABORTED') {
      msg.value = '识别超时（超过 3 分钟），请换一张更小的图片或稍后重试'
    } else {
      msg.value = e.response?.data?.detail || '上传或识别失败'
    }
  } finally {
    uploadingSample.value = false
  }
}

onMounted(reload)
</script>

<style scoped>
.maintenance-view {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.page-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 1.15rem;
  font-family: Georgia, 'Times New Roman', 'Songti SC', serif;
}

.page-desc {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.cat-totals {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-start;
}

.cat-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  border: 1px solid var(--cl-border-cream);
  font-size: 12px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.sel {
  min-width: 160px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
}

.primary {
  cursor: pointer;
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  background: var(--cl-brand);
  color: var(--cl-ivory);
  font-weight: 700;
  font-size: 13px;
}

.ghost {
  cursor: pointer;
  border: 1px solid var(--cl-border-warm);
  background: transparent;
  border-radius: 10px;
  padding: 10px 12px;
}

.msg {
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
}

.msg--err {
  border: 1px solid rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.08);
  color: var(--cl-error);
}

.msg--ok {
  border: 1px solid rgba(39, 143, 80, 0.35);
  background: rgba(39, 143, 80, 0.08);
  color: #1d5e36;
}

.sample-file-input {
  display: none;
}

.hint {
  padding: 20px;
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
}

.muted {
  color: var(--cl-olive);
  font-size: 13px;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  overflow: hidden;
}

th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--cl-border-cream);
  text-align: left;
  vertical-align: top;
}

th {
  background: var(--cl-warm-sand);
  color: var(--cl-olive);
  font-weight: 800;
}

.strong {
  font-weight: 900;
}

.cat-cell {
  max-width: 280px;
}

.cat-tag {
  display: inline-block;
  margin: 2px 4px 2px 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(201, 100, 66, 0.1);
  font-size: 11px;
}

.status--done {
  color: #1d5e36;
  font-weight: 700;
}

.status--failed {
  color: var(--cl-error);
  font-weight: 700;
}

.link {
  border: 0;
  background: transparent;
  color: var(--cl-coral);
  cursor: pointer;
  font-size: 13px;
}

.settle-cards {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 12px;
  flex-direction: column;
}

.settle-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  padding: 14px;
  background: var(--cl-ivory);
}

.settle-card__top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.cat-tags {
  margin: 8px 0;
}

.detail-meta {
  margin-bottom: 12px;
  font-size: 13px;
  line-height: 1.6;
}

.tbl-detail {
  font-size: 12px;
}

.match-score {
  color: var(--cl-olive);
  font-size: 11px;
}

@media (max-width: 768px) {
  .tbl--desktop {
    display: none;
  }

  .settle-cards {
    display: flex;
  }

  .sel,
  .primary,
  .ghost {
    width: 100%;
    min-height: 44px;
  }
}
</style>
