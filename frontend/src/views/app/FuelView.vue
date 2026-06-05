<template>
  <div class="stack fuel-view">
    <section class="panel balance-panel">
      <div class="hd hd--split">
        <h2>油卡余额</h2>
      </div>

      <div class="balance-sync-bar">
        <div class="balance-sync-bar__main">
          <button
            type="button"
            class="primary balance-sync-btn"
            :disabled="syncingBalances || loadingBalances"
            @click="syncBalancesFromPlatform"
          >
            {{ syncingBalances ? '正在同步…' : '同步最新余额' }}
          </button>
          <div class="balance-sync-stats" aria-label="同步刷新统计">
            <div class="balance-sync-stat">
              <span class="balance-sync-stat__label">今日刷新</span>
              <span class="balance-sync-stat__value">{{ syncStats.today_count }} 次</span>
            </div>
            <div class="balance-sync-stat balance-sync-stat--time">
              <span class="balance-sync-stat__label">上次刷新</span>
              <span class="balance-sync-stat__value">{{ formatLastSynced(syncStats.last_synced_at) }}</span>
            </div>
          </div>
        </div>
        <p class="balance-sync-hint balance-panel__desktop-only">从中国石油油卡平台拉取最新余额并刷新本页</p>
      </div>
      <p class="balance-mobile-summary balance-panel__mobile-only">共 {{ balancesTotal }} 张 · 合计 {{ fmtMoney(balanceTotalAmount) }}</p>
      <div v-if="syncStatus" class="sync-status">{{ syncStatus }}</div>
      <div v-if="msg" class="msg">{{ msg }}</div>

      <section class="balance-overview balance-panel__desktop-only" aria-label="余额统计总览">
        <article class="balance-kpi">
          <div class="balance-kpi__label">当前列表卡数</div>
          <div class="balance-kpi__value">{{ balancesTotal }}</div>
          <div class="balance-kpi__hint">受车间与余额区间筛选影响</div>
        </article>
        <article class="balance-kpi balance-kpi--amount">
          <div class="balance-kpi__label">当前列表合计</div>
          <div class="balance-kpi__value">{{ fmtMoney(balanceTotalAmount) }}</div>
          <div class="balance-kpi__hint">平均单卡 {{ fmtMoney(averageBalanceAmount) }}</div>
        </article>
        <article class="balance-kpi">
          <div class="balance-kpi__label">全部油卡总览</div>
          <div class="balance-kpi__value">{{ overallCount }}</div>
          <div class="balance-kpi__hint">总余额 {{ fmtMoney(overallSum) }} · 0余额 {{ zeroBucket?.count ?? 0 }} 张</div>
        </article>
      </section>

      <div class="balance-charts balance-panel__desktop-only">
        <article class="chart chart--donut" aria-label="油卡余额区间分布图">
          <div class="ct">余额区间分布 <span class="ct-hint">· 点击筛选表格</span></div>
          <div class="balance-chart__body">
            <div class="donut" role="img" aria-label="油卡余额区间占比环形图">
              <svg viewBox="0 0 140 140" class="donut__svg">
                <g transform="rotate(-90 70 70)">
                  <circle class="donut__track" cx="70" cy="70" r="54" />
                  <circle
                    v-for="seg in donutSegments"
                    :key="`donut-${seg.key}`"
                    class="donut__seg"
                    cx="70"
                    cy="70"
                    r="54"
                    :stroke="seg.color"
                    :stroke-dasharray="seg.dasharray"
                    :stroke-dashoffset="seg.dashoffset"
                  />
                </g>
              </svg>
              <div class="donut__center">
                <span class="donut__center-num">{{ overallCount }}</span>
                <span class="donut__center-label">张油卡</span>
                <span class="donut__center-amount">{{ fmtMoney(overallSum) }}</span>
              </div>
            </div>
            <ul class="legend">
              <li v-for="seg in donutSegments" :key="`legend-${seg.key}`">
                <button
                  type="button"
                  class="legend__row"
                  :class="{ 'is-active': activeBucketKey === seg.key }"
                  @click="applyBucketFilter(seg)"
                >
                  <span class="legend__dot" :style="{ background: seg.color }" />
                  <span class="legend__label">{{ seg.label }}</span>
                  <span class="legend__count">{{ seg.count }} 张</span>
                  <span class="legend__pct">{{ seg.pct.toFixed(1) }}%</span>
                </button>
              </li>
            </ul>
          </div>
        </article>

        <article class="chart chart--bars" aria-label="全部油卡余额条形图">
          <div class="ct">全部油卡余额条形图 <span class="ct-hint">· 按合计余额区间统计</span></div>
          <div class="bars balance-bars">
            <button
              v-for="(seg, idx) in donutSegments"
              :key="`bucket-bar-${seg.key}`"
              type="button"
              class="bar-row bar-row--interactive"
              :class="{ 'bar-row--active': activeBucketKey === seg.key }"
              @click="applyBucketFilter(seg)"
            >
              <div class="bar-label">{{ seg.label }}</div>
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill" :style="chartBarFillStyle(seg.count, bucketMaxCount, idx)" />
              </div>
              <div class="bar-value">{{ seg.count }} 张 · {{ fmtMoney(seg.amount) }}</div>
            </button>
          </div>
        </article>
      </div>

      <div class="rec-toolbar balance-toolbar">
        <div class="rec-filters">
          <label class="inline-label">车间</label>
          <SearchableSelect
            v-model="balanceFilter.workshop_id"
            :options="balanceWorkshopOptions"
            allow-empty
            empty-label="全部"
            search-placeholder="输入车间关键字…"
          />
          <label class="inline-label">合计金额区间</label>
          <div class="price-range">
            <input
              v-model="balanceFilter.total_min"
              type="number"
              inputmode="decimal"
              min="0"
              step="0.01"
              class="filter-control price-input"
              placeholder="最低"
              @keyup.enter="searchBalances"
            />
            <span class="price-range__sep" aria-hidden="true">—</span>
            <input
              v-model="balanceFilter.total_max"
              type="number"
              inputmode="decimal"
              min="0"
              step="0.01"
              class="filter-control price-input"
              placeholder="最高"
              @keyup.enter="searchBalances"
            />
          </div>
        </div>
        <button type="button" class="ghost rec-query" :disabled="loadingBalances" @click="resetBalanceFilter">
          重置
        </button>
        <button type="button" class="primary rec-query" :disabled="loadingBalances" @click="searchBalances">
          {{ loadingBalances ? '查询中…' : '查询' }}
        </button>
      </div>

      <table class="tbl tbl-balances tbl--desktop">
        <thead>
          <tr>
            <th class="col-seq">序号</th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('card_no')">卡号{{ sortMark('card_no') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('workshop')">车间{{ sortMark('workshop') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('vehicle_no')">车号{{ sortMark('vehicle_no') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('amount')">金额{{ sortMark('amount') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('reserve_fund')">备用金{{ sortMark('reserve_fund') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('total')">合计{{ sortMark('total') }}</button></th>
          </tr>
        </thead>
        <tbody v-if="loadingBalances">
          <tr><td colspan="7" class="hint">余额数据加载中…</td></tr>
        </tbody>
        <tbody v-else-if="!balances.length">
          <tr><td colspan="7" class="hint">暂无油卡余额数据。</td></tr>
        </tbody>
        <tbody v-else>
          <tr v-for="(b, idx) in balances" :key="`bal-${b.id}`">
            <td class="col-seq">{{ rowSeq(idx) }}</td>
            <td>{{ b.card_no }}</td>
            <td>{{ b.workshop === '/' ? '—' : b.workshop || '—' }}</td>
            <td>{{ b.vehicle_no || '—' }}</td>
            <td>{{ fmtMoney(b.amount) }}</td>
            <td>
              <span :class="{ 'reserve-hl': hasReserve(b.reserve_fund) }">{{ fmtMoney(b.reserve_fund) }}</span>
            </td>
            <td>{{ fmtMoney(b.total) }}</td>
          </tr>
        </tbody>
      </table>

      <div class="balance-mobile" aria-live="polite">
        <p v-if="loadingBalances" class="hint balance-mobile__hint">余额数据加载中…</p>
        <p v-else-if="!balances.length" class="hint balance-mobile__hint">暂无油卡余额数据。</p>
        <ul v-else class="balance-cards" aria-label="油卡余额列表">
          <li v-for="(b, idx) in balances" :key="`bal-m-${b.id}`" class="balance-card">
            <div class="balance-card__head">
              <span class="balance-card__seq">{{ rowSeq(idx) }}</span>
              <span class="balance-card__no">{{ b.card_no }}</span>
              <strong class="balance-card__sum">{{ fmtMoney(b.total) }}</strong>
            </div>
            <p class="balance-card__sub">
              <span>{{ displayWorkshop(b.workshop) }}</span>
              <span class="balance-card__sep" aria-hidden="true">·</span>
              <span>{{ b.vehicle_no || '—' }}</span>
            </p>
            <p class="balance-card__extra">
              金额 {{ fmtMoney(b.amount) }}
              <span class="balance-card__sep" aria-hidden="true">·</span>
              <span :class="{ 'reserve-hl': hasReserve(b.reserve_fund) }">备用金 {{ fmtMoney(b.reserve_fund) }}</span>
            </p>
          </li>
        </ul>
      </div>

      <div v-if="balancesTotal > 0 && !loadingBalances" class="rec-pager">
        <span class="pager-meta">每页 15 条</span>
        <button type="button" class="ghost pager-btn" :disabled="balancePage <= 1" @click="prevBalancePage">上一页</button>
        <span class="pager-meta">第 {{ balancePage }} / {{ balanceTotalPages }} 页</span>
        <button type="button" class="ghost pager-btn" :disabled="balancePage >= balanceTotalPages" @click="nextBalancePage">
          下一页
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import * as fuelApi from '@/api/fuel'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import type { FuelBalance, FuelBalanceBucket } from '@/api/fuel'

const balances = ref<FuelBalance[]>([])
const balanceWorkshops = ref<string[]>([])
const balanceBuckets = ref<FuelBalanceBucket[]>([])
const msg = ref('')
const syncStatus = ref('')
const syncStats = ref<{ today_count: number; last_synced_at: string | null }>({
  today_count: 0,
  last_synced_at: null,
})
const syncingBalances = ref(false)
const loadingBalances = ref(false)
const balancesTotal = ref(0)
const balanceTotalAmount = ref('0')
const balancePage = ref(1)
const BALANCE_PAGE_SIZE = 15

const balanceFilter = reactive({
  workshop_id: 0,
  total_min: '' as string | number,
  total_max: '' as string | number,
})
const balanceSort = reactive({
  by: 'card_no' as 'card_no' | 'workshop' | 'vehicle_no' | 'amount' | 'reserve_fund' | 'total',
  dir: 'asc' as 'asc' | 'desc',
})

const balanceTotalPages = computed(() =>
  Math.max(1, Math.ceil(balancesTotal.value / BALANCE_PAGE_SIZE) || 1),
)
const averageBalanceAmount = computed(() =>
  balancesTotal.value ? Number(balanceTotalAmount.value || 0) / balancesTotal.value : 0,
)

const overallCount = computed(() =>
  safeBalanceBuckets.value.reduce((sum, bucket) => sum + bucket.count, 0),
)
const overallSum = computed(() =>
  safeBalanceBuckets.value.reduce((sum, bucket) => sum + Number(bucket.sum || 0), 0),
)
const safeBalanceBuckets = computed(() => (Array.isArray(balanceBuckets.value) ? balanceBuckets.value : []))
const zeroBucket = computed(() => safeBalanceBuckets.value.find((bucket) => bucket.key === 'zero'))
const bucketMaxCount = computed(() => Math.max(...safeBalanceBuckets.value.map((bucket) => bucket.count), 0))

const DONUT_C = 2 * Math.PI * 54
const BAR_FILL_GRADIENTS = [
  'linear-gradient(90deg, rgba(201, 100, 66, 0.32) 0%, #c96442 94%)',
  'linear-gradient(90deg, rgba(215, 119, 87, 0.35) 0%, #d97757 94%)',
  'linear-gradient(90deg, rgba(181, 138, 90, 0.4) 0%, #9a7340 92%)',
  'linear-gradient(90deg, rgba(201, 161, 91, 0.42) 0%, #b8883a 92%)',
  'linear-gradient(90deg, rgba(94, 93, 89, 0.28) 0%, #6b5d4b 94%)',
  'linear-gradient(90deg, rgba(167, 107, 82, 0.38) 0%, #a76b52 92%)',
  'linear-gradient(90deg, rgba(77, 76, 72, 0.32) 0%, #5c5347 92%)',
] as const
const DONUT_COLORS = ['#c96442', '#d97757', '#9a7340', '#b8883a', '#6b5d4b', '#a76b52', '#5c5347'] as const

type DonutSegment = {
  key: string
  label: string
  color: string
  count: number
  amount: number
  pct: number
  filterMin: string | number | null
  filterMax: string | number | null
  dasharray: string
  dashoffset: number
}

const donutSegments = computed<DonutSegment[]>(() => {
  const total = overallCount.value || 1
  let acc = 0
  return safeBalanceBuckets.value.map((bucket, idx) => {
    const len = (bucket.count / total) * DONUT_C
    const seg: DonutSegment = {
      key: bucket.key,
      label: bucket.label,
      color: DONUT_COLORS[idx % DONUT_COLORS.length],
      count: bucket.count,
      amount: Number(bucket.sum || 0),
      filterMin: bucket.filter_min,
      filterMax: bucket.filter_max,
      pct: overallCount.value ? (bucket.count / overallCount.value) * 100 : 0,
      dasharray: `${len} ${DONUT_C}`,
      dashoffset: -acc,
    }
    acc += len
    return seg
  })
})

function normalizePriceInput(raw: string | number | null | undefined): string {
  return String(raw ?? '').trim()
}

function parsePrice(raw: string | number | null | undefined): number | null {
  const v = normalizePriceInput(raw)
  if (!v) return null
  const n = Number(v)
  return Number.isFinite(n) && n >= 0 ? n : null
}

type LegacyFuelBalancePage = fuelApi.FuelBalancePage & {
  count_zero?: number
  count_low?: number
  count_high?: number
  sum_zero?: string
  sum_low?: string
  sum_high?: string
}

function normalizeBalanceBuckets(res: fuelApi.FuelBalancePage): FuelBalanceBucket[] {
  if (Array.isArray(res.buckets)) return res.buckets

  // 兼容旧后端：如果线上后端还没更新到 buckets 字段，页面先按旧三档展示，避免白屏。
  const legacy = res as LegacyFuelBalancePage
  if (
    legacy.count_zero !== undefined ||
    legacy.count_low !== undefined ||
    legacy.count_high !== undefined
  ) {
    return [
      { key: 'zero', label: '= 0', filter_min: 0, filter_max: 0, count: legacy.count_zero ?? 0, sum: legacy.sum_zero ?? '0' },
      { key: 'b1', label: '0 - 500', filter_min: 0.01, filter_max: 500, count: legacy.count_low ?? 0, sum: legacy.sum_low ?? '0' },
      { key: 'b2', label: '500 以上', filter_min: 500.01, filter_max: null, count: legacy.count_high ?? 0, sum: legacy.sum_high ?? '0' },
    ]
  }

  return []
}

const activeBucketKey = computed(() => {
  const minVal = normalizePriceInput(balanceFilter.total_min)
  const maxVal = normalizePriceInput(balanceFilter.total_max)
  return donutSegments.value.find((seg) => String(seg.filterMin ?? '') === minVal && String(seg.filterMax ?? '') === maxVal)?.key ?? ''
})

function barFillStyle(index: number): Record<string, string> {
  return {
    background: BAR_FILL_GRADIENTS[index % BAR_FILL_GRADIENTS.length],
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.32)',
  }
}

function chartBarFillStyle(value: number, max: number, idx: number): Record<string, string> {
  const m = max > 0 ? max : 1
  const pct = (value / m) * 100
  return { width: `${pct}%`, ...barFillStyle(idx) }
}

const balanceWorkshopOptions = computed<SearchableOption[]>(() =>
  balanceWorkshops.value.map((unit, idx) => ({
    id: idx + 1,
    label: unit,
    keywords: unit,
  })),
)

function selectedBalanceWorkshopName(): string {
  if (!balanceFilter.workshop_id) return ''
  return balanceWorkshopOptions.value.find((x) => x.id === balanceFilter.workshop_id)?.label ?? ''
}

function monthStartIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function formatLastSynced(raw: string | null) {
  if (!raw) return '暂无记录'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

async function loadSyncStats() {
  try {
    syncStats.value = await fuelApi.fetchFuelSyncStats()
  } catch {
    /* 统计加载失败不影响主流程 */
  }
}

async function syncBalancesFromPlatform() {
  balancePage.value = 1
  syncingBalances.value = true
  loadingBalances.value = true
  msg.value = ''
  syncStatus.value = '准备连接中国石油油卡平台…'
  try {
    await fuelApi.syncFuelFromPlatform(
      {
        date_from: monthStartIso(),
        date_to: todayIso(),
      },
      (message) => {
        syncStatus.value = message
      },
    )
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '同步中国石油油卡数据失败'
    syncStatus.value = ''
    loadingBalances.value = false
    syncingBalances.value = false
    return
  } finally {
    syncingBalances.value = false
  }

  syncStatus.value = '同步完成，正在刷新余额…'
  try {
    balanceWorkshops.value = await fuelApi.listFuelBalanceWorkshops()
    await fetchBalancePage()
    await loadSyncStats()
    syncStatus.value = ''
  } catch {
    msg.value = '数据已同步，但刷新余额失败，请稍后重试'
    syncStatus.value = ''
  } finally {
    loadingBalances.value = false
  }
}

async function reload() {
  msg.value = ''
  loadingBalances.value = true
  try {
    balanceWorkshops.value = await fuelApi.listFuelBalanceWorkshops()
    if (balancePage.value > balanceTotalPages.value) balancePage.value = 1
    await Promise.all([fetchBalancePage(), loadSyncStats()])
  } catch {
    msg.value = '加载油卡余额失败'
  } finally {
    loadingBalances.value = false
  }
}

async function fetchBalancePage() {
  loadingBalances.value = true
  try {
    const workshop = selectedBalanceWorkshopName()
    const minVal = parsePrice(balanceFilter.total_min)
    const maxVal = parsePrice(balanceFilter.total_max)
    const res = await fuelApi.listFuelBalancesPaged({
      page: balancePage.value,
      page_size: BALANCE_PAGE_SIZE,
      ...(workshop ? { workshop } : {}),
      ...(minVal !== null ? { total_min: minVal } : {}),
      ...(maxVal !== null ? { total_max: maxVal } : {}),
      sort_by: balanceSort.by,
      sort_dir: balanceSort.dir,
    })
    balances.value = res.items
    balancesTotal.value = res.total
    balanceTotalAmount.value = res.total_amount
    balanceBuckets.value = normalizeBalanceBuckets(res)
    const maxPage = Math.max(1, Math.ceil(res.total / BALANCE_PAGE_SIZE) || 1)
    if (balancePage.value > maxPage) balancePage.value = maxPage
  } finally {
    loadingBalances.value = false
  }
}

function toggleBalanceSort(
  by: 'card_no' | 'workshop' | 'vehicle_no' | 'amount' | 'reserve_fund' | 'total',
) {
  if (balanceSort.by === by) {
    balanceSort.dir = balanceSort.dir === 'asc' ? 'desc' : 'asc'
  } else {
    balanceSort.by = by
    balanceSort.dir = 'asc'
  }
  balancePage.value = 1
  void fetchBalancePage()
}

function sortMark(by: 'card_no' | 'workshop' | 'vehicle_no' | 'amount' | 'reserve_fund' | 'total') {
  if (balanceSort.by !== by) return ''
  return balanceSort.dir === 'asc' ? ' ↑' : ' ↓'
}

function fmtMoney(v: string | number) {
  return Number(v || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function displayWorkshop(workshop: string) {
  return workshop === '/' ? '—' : workshop || '—'
}

function rowSeq(idx: number) {
  return (balancePage.value - 1) * BALANCE_PAGE_SIZE + idx + 1
}

function hasReserve(v: string | number) {
  return Number(v || 0) > 0
}

function applyBucketFilter(bucket: DonutSegment) {
  const minValue = String(bucket.filterMin ?? '')
  const maxValue = String(bucket.filterMax ?? '')
  if (balanceFilter.total_min === minValue && balanceFilter.total_max === maxValue) {
    balanceFilter.total_min = ''
    balanceFilter.total_max = ''
  } else {
    balanceFilter.total_min = minValue
    balanceFilter.total_max = maxValue
  }
  balancePage.value = 1
  void fetchBalancePage()
}

function searchBalances() {
  balancePage.value = 1
  void fetchBalancePage()
}

function resetBalanceFilter() {
  balanceFilter.workshop_id = 0
  balanceFilter.total_min = ''
  balanceFilter.total_max = ''
  balancePage.value = 1
  void fetchBalancePage()
}

function prevBalancePage() {
  if (balancePage.value <= 1) return
  balancePage.value -= 1
  void fetchBalancePage()
}

function nextBalancePage() {
  if (balancePage.value >= balanceTotalPages.value) return
  balancePage.value += 1
  void fetchBalancePage()
}

onMounted(() => {
  void reload()
})
</script>

<style scoped>
.stack.fuel-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.panel {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  border-radius: 16px;
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.balance-toolbar {
  margin-top: 2px;
}

.hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.hd h2 {
  margin: 0;
  font-size: 1.05rem;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-weight: 500;
}

.hd--split {
  flex-wrap: wrap;
  row-gap: 8px;
}

.balance-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 8px 0 12px;
}

.balance-kpi {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 12px;
  padding: 10px 12px;
}

.balance-kpi__label {
  font-size: 12px;
  color: var(--cl-olive);
}

.balance-kpi__value {
  margin-top: 4px;
  font-size: 1.08rem;
  font-weight: 800;
  color: var(--cl-near-black);
  font-variant-numeric: tabular-nums;
}

.balance-kpi__hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--cl-charcoal);
}

.balance-kpi--amount {
  background: linear-gradient(135deg, rgba(201, 100, 66, 0.08), rgba(201, 161, 91, 0.12));
}

.chart {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 12px;
  padding: 12px 12px 10px;
  min-width: 0;
}

.balance-charts {
  display: grid;
  grid-template-columns: minmax(320px, 0.85fr) minmax(420px, 1.15fr);
  gap: 12px;
  margin-bottom: 12px;
}

.chart--donut,
.chart--bars {
  min-height: 240px;
}

.ct {
  font-size: 12px;
  color: var(--cl-olive);
  margin-bottom: 8px;
}

.ct-hint {
  font-weight: 400;
  color: var(--cl-stone);
  font-size: 11px;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.balance-bars {
  max-height: 214px;
  overflow-y: auto;
  padding-right: 4px;
}

.bar-row {
  display: grid;
  grid-template-columns: minmax(86px, 24%) minmax(0, 1fr) minmax(132px, 168px);
  gap: 8px;
  align-items: center;
}

button.bar-row {
  width: 100%;
  margin: 0;
  padding: 4px 2px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  font: inherit;
  color: inherit;
  text-align: start;
  cursor: pointer;
  -webkit-tap-highlight-color: rgba(201, 100, 66, 0.12);
}

button.bar-row:focus-visible {
  outline: 2px solid rgba(201, 100, 66, 0.45);
  outline-offset: 2px;
}

button.bar-row:hover,
button.bar-row.bar-row--active {
  background: rgba(201, 100, 66, 0.08);
}

.bar-label {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 9px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ebe7dc, var(--cl-warm-sand));
  border: 1px solid rgba(232, 230, 220, 0.85);
  box-shadow: inset 0 1px 2px rgba(20, 20, 19, 0.06);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  min-width: 6px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(201, 100, 66, 0.55), #c96442);
  transition:
    filter 0.16s ease,
    box-shadow 0.16s ease;
}

.bar-row--interactive:hover:not(:disabled) .bar-fill {
  filter: brightness(1.07) saturate(1.05);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    0 0 0 1px rgba(201, 100, 66, 0.12);
}

.bar-value {
  font-size: 12px;
  text-align: right;
  color: var(--cl-charcoal);
  font-variant-numeric: tabular-nums;
}

.balance-chart__body {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
}

.donut {
  position: relative;
  width: 138px;
  height: 138px;
  flex: 0 0 auto;
}

.donut__svg {
  width: 100%;
  height: 100%;
  display: block;
}

.donut__track {
  fill: none;
  stroke: #ebe7dc;
  stroke-width: 15;
}

.donut__seg {
  fill: none;
  stroke-width: 15;
  stroke-linecap: butt;
  transition: stroke-dasharray 0.4s ease;
}

.donut__center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  pointer-events: none;
}

.donut__center-num {
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--cl-near-black);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.donut__center-label {
  font-size: 12px;
  color: var(--cl-olive);
}

.donut__center-amount {
  margin-top: 3px;
  max-width: 92px;
  font-size: 11px;
  font-weight: 700;
  color: var(--cl-brand, #c96442);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.legend {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1 1 180px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.legend__row {
  width: 100%;
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
  display: grid;
  grid-template-columns: 12px minmax(72px, 1fr) 54px 48px;
  align-items: center;
  gap: 8px;
  padding: 5px 6px;
  border-radius: 8px;
  text-align: left;
  transition: background-color 0.14s ease, box-shadow 0.14s ease;
}

.legend__row:hover,
.legend__row.is-active {
  background: rgba(201, 100, 66, 0.08);
}

.legend__row.is-active {
  box-shadow: inset 0 0 0 1px rgba(201, 100, 66, 0.18);
}

.legend__dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}

.legend__label {
  font-size: 12px;
  color: var(--cl-charcoal);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.legend__count,
.legend__pct {
  font-size: 11px;
  color: var(--cl-charcoal);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.legend__pct {
  color: var(--cl-olive);
}

.price-range {
  display: flex;
  align-items: center;
  gap: 6px;
}

.price-input {
  width: 110px;
}

.rec-filters .price-input {
  padding: 10px 10px;
  border-radius: 12px;
  min-height: 42px;
  font-size: 13px;
  box-sizing: border-box;
}

.price-range__sep {
  color: var(--cl-olive);
}

.primary {
  cursor: pointer;
  border: 0;
  border-radius: 10px;
  padding: 8px 12px;
  background: var(--cl-brand);
  color: var(--cl-ivory);
  font-weight: 500;
  font-size: 12px;
}

.balance-sync-bar {
  margin: 4px 0 12px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(201, 100, 66, 0.22);
  background: linear-gradient(135deg, rgba(255, 252, 247, 0.98), rgba(250, 244, 235, 0.92));
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.balance-sync-bar__main {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  min-width: 0;
}

.balance-sync-btn {
  width: 100%;
  flex: none;
  min-width: 0;
  min-height: 44px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow:
    rgba(201, 100, 66, 0.28) 0 6px 18px -6px,
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
  box-sizing: border-box;
}

.balance-sync-stats {
  width: 100%;
  flex: none;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 8px;
  min-width: 0;
}

.balance-sync-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(201, 100, 66, 0.12);
  box-sizing: border-box;
}

.balance-sync-stat__label {
  font-size: 11px;
  color: var(--cl-olive);
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.balance-sync-stat__value {
  font-size: 14px;
  font-weight: 800;
  color: var(--cl-near-black);
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.balance-sync-stat--time .balance-sync-stat__value {
  font-size: 12px;
  font-weight: 700;
}

.balance-sync-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.balance-sync-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--cl-olive);
  line-height: 1.45;
}

.sync-status {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(201, 100, 66, 0.35);
  background: rgba(201, 100, 66, 0.1);
  color: #8a4b22;
  font-size: 13px;
}

.msg {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.08);
  color: var(--cl-error);
  font-size: 13px;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--cl-border-cream);
  text-align: left;
}

th {
  color: var(--cl-olive);
  font-weight: 800;
  background: var(--cl-warm-sand);
}

.th-sort-btn {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: inherit;
  padding: 0;
  cursor: pointer;
}

.w {
  width: 140px;
  white-space: nowrap;
}

.link {
  cursor: pointer;
  border: 0;
  background: transparent;
  color: var(--cl-coral);
  margin-right: 10px;
  padding: 0;
  font-size: 13px;
}

.link.danger {
  color: var(--cl-error);
}

.rec-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 12px;
  background: var(--cl-warm-sand);
  border: 1px solid var(--cl-border-cream);
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.rec-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  flex: 1;
  min-width: 0;
  max-width: 100%;
}

/* 桌面：不参与布局；移动端：包住 date，避免 WebKit 固有宽度撑破父级 */
.filter-field--date {
  display: contents;
}

.inline-label {
  font-size: 12px;
  color: var(--cl-olive);
  white-space: nowrap;
}

.filter-control {
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  font-size: 12px;
  min-width: 0;
}

/* 与 SearchableSelect 触发器统一：圆角、高度、字号 */
.rec-filters .filter-control {
  padding: 10px 10px;
  border-radius: 12px;
  min-height: 42px;
  font-size: 13px;
  box-sizing: border-box;
}

.filter-date {
  width: 132px;
  max-width: 100%;
}

.filter-station {
  width: min(200px, 100%);
}

.rec-query {
  flex-shrink: 0;
}

.hint {
  padding: 16px 10px;
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
}

.tbl-balances {
  table-layout: fixed;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  overflow: hidden;
  background: var(--cl-white);
}

.tbl-balances th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: linear-gradient(180deg, #f4efe5 0%, #efe8dc 100%);
  color: #5d5548;
  font-size: 13px;
  letter-spacing: 0.01em;
}

.tbl-balances td {
  background: #fff;
  border-bottom: 1px solid rgba(232, 224, 212, 0.85);
  transition: background-color 0.12s ease;
}

.tbl-balances td {
  word-break: break-word;
}

.reserve-hl {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 6px;
  background: rgba(196, 133, 34, 0.16);
  border: 1px solid rgba(196, 133, 34, 0.32);
  color: #8a5a16;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.tbl-balances tbody tr:nth-child(even) td {
  background: #fcfaf6;
}

.tbl-balances tbody tr:hover td {
  background: #f6f0e5;
}

.tbl-balances th:nth-child(1),
.tbl-balances td:nth-child(1) {
  width: 7%;
  text-align: center;
  color: var(--cl-olive);
  font-variant-numeric: tabular-nums;
}

.tbl-balances th:nth-child(2),
.tbl-balances td:nth-child(2) {
  width: 16%;
}

.tbl-balances th:nth-child(3),
.tbl-balances td:nth-child(3) {
  width: 13%;
}

.tbl-balances th:nth-child(4),
.tbl-balances td:nth-child(4) {
  width: 16%;
}

.tbl-balances th:nth-child(5),
.tbl-balances td:nth-child(5),
.tbl-balances th:nth-child(6),
.tbl-balances td:nth-child(6),
.tbl-balances th:nth-child(7),
.tbl-balances td:nth-child(7) {
  width: 16%;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.balance-mobile {
  display: none;
}

.balance-panel__mobile-only {
  display: none;
}

.balance-mobile-summary {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--cl-olive);
  font-variant-numeric: tabular-nums;
}

.balance-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.balance-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  background: var(--cl-ivory);
  padding: 12px;
  box-shadow: rgba(0, 0, 0, 0.04) 0 3px 12px;
}

.balance-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.balance-card__seq {
  flex-shrink: 0;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  border: 1px solid var(--cl-border-cream);
  color: var(--cl-olive);
  font-size: 12px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.balance-card__no {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--cl-near-black);
  word-break: break-all;
  line-height: 1.35;
  font-variant-numeric: tabular-nums;
}

.balance-card__sum {
  flex-shrink: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--cl-brand, #c96442);
  font-variant-numeric: tabular-nums;
}

.balance-card__sub,
.balance-card__extra {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--cl-charcoal);
}

.balance-card__sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
}

.balance-card__extra {
  font-size: 12px;
  color: var(--cl-olive);
  font-variant-numeric: tabular-nums;
}

.balance-card__sep {
  color: var(--cl-olive);
  opacity: 0.65;
}

.tbl--desktop {
  display: table;
}

.rec-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
}

.pager-meta {
  font-size: 13px;
  color: var(--cl-charcoal);
}

.pager-size {
  width: 72px;
}

.pager-btn {
  font-size: 12px;
  padding: 6px 12px;
}

.ghost {
  cursor: pointer;
  border: 1px solid var(--cl-border-warm);
  background: transparent;
  color: var(--cl-charcoal);
  border-radius: 10px;
  padding: 10px 12px;
}

/* 宽屏：按钮与统计并排，统计区固定宽度避免被 flex 拉宽 */
@media (min-width: 960px) {
  .balance-sync-bar__main {
    flex-direction: row;
    align-items: center;
    gap: 14px;
  }

  .balance-sync-btn {
    width: auto;
    flex: 0 0 auto;
    min-width: 168px;
    max-width: 220px;
  }

  .balance-sync-stats {
    width: auto;
    flex: 0 0 auto;
    grid-template-columns: 108px 148px;
    gap: 10px;
  }
}

/* 窄屏与平板：统计改为两行紧凑条，避免两列网格被拉成宽空框 */
@media (max-width: 1180px) {
  .balance-charts {
    grid-template-columns: 1fr;
  }

  .chart--donut,
  .chart--bars {
    min-height: 0;
  }
}

@media (max-width: 959px) {
  .balance-sync-stats {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .balance-sync-stat {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 9px 12px;
  }

  .balance-sync-stat__value {
    flex-shrink: 0;
    text-align: right;
  }

  .balance-sync-stat--time .balance-sync-stat__value {
    font-size: 12px;
  }
}

@media (max-width: 768px) {
  .panel {
    padding: 12px;
    border-radius: 14px;
  }

  .balance-panel__desktop-only {
    display: none !important;
  }

  .balance-panel__mobile-only {
    display: block;
  }

  .tbl--desktop {
    display: none;
  }

  .hd {
    margin-bottom: 8px;
  }

  .balance-sync-bar {
    padding: 12px;
    margin-bottom: 10px;
  }

  .balance-sync-btn {
    min-height: 48px;
    font-size: 16px;
  }

  .balance-sync-hint {
    display: none;
  }

  .rec-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    margin-bottom: 10px;
    padding: 10px;
  }

  .rec-filters {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }

  .inline-label {
    margin-top: 6px;
  }

  .rec-filters .inline-label:first-child {
    margin-top: 0;
  }

  .rec-filters :deep(.searchable-select) {
    max-width: 100% !important;
    width: 100%;
    flex: none;
    align-self: stretch;
    min-width: 0;
  }

  .rec-filters :deep(.searchable-select__trigger) {
    font-size: 16px;
    max-width: 100%;
  }

  .rec-filters :deep(.searchable-select__search) {
    font-size: 16px;
  }

  /* 日期外层：限制 WebKit 溢出；圆角与 input 一致，避免 overflow:hidden 把右侧圆角裁成直角 */
  .rec-filters .filter-field--date {
    display: block;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    border-radius: 12px;
    overflow: hidden;
    box-sizing: border-box;
    /* 部分 WebKit 下圆角裁剪更稳定 */
    transform: translateZ(0);
    -webkit-transform: translateZ(0);
  }

  .rec-filters .filter-field--date .filter-control.filter-date {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    display: block;
    box-sizing: border-box;
    border-radius: 12px;
  }

  .rec-filters .filter-control {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    display: block;
    font-size: 16px;
    box-sizing: border-box;
  }

  .price-range {
    width: 100%;
  }

  .price-range .price-input {
    flex: 1 1 0;
    width: auto;
    min-width: 0;
  }

  .rec-query {
    min-height: 44px;
    font-size: 15px;
    font-weight: 600;
    width: 100%;
  }

  .balance-mobile {
    display: block;
  }

  .balance-cards {
    gap: 0;
    border: 1px solid var(--cl-border-cream);
    border-radius: 12px;
    overflow: hidden;
    background: var(--cl-white);
  }

  .balance-card {
    border: 0;
    border-radius: 0;
    box-shadow: none;
    padding: 12px 14px;
    background: var(--cl-white);
    border-bottom: 1px solid rgba(232, 224, 212, 0.9);
  }

  .balance-card:last-child {
    border-bottom: 0;
  }

  .balance-card:nth-child(even) {
    background: #fcfaf6;
  }

  .balance-mobile__hint {
    margin: 0 0 8px;
  }

  .rec-pager {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .pager-size {
    width: 100%;
    min-height: 44px;
    font-size: 16px;
  }

  .pager-btn {
    width: 100%;
    min-height: 44px;
    font-size: 15px;
  }

  .pager-meta {
    text-align: center;
  }
}
</style>
