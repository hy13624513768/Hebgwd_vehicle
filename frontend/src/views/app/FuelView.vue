<template>
  <div class="stack fuel-view">
    <section class="panel balance-panel">
      <div class="hd hd--split">
        <h2>油卡余额（卡内剩余金额）</h2>
        <div class="balance-meta">
          <span>共 {{ balancesTotal }} 张</span>
          <span>合计 {{ Number(balanceTotalAmount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
          <button
            type="button"
            class="balance-pill balance-pill--zero"
            :class="{ 'is-active': balanceFilter.amount_bucket === 'zero' }"
            @click="toggleBalanceBucket('zero')"
          >
            合计=0：{{ balanceCountZero }}
          </button>
          <button
            type="button"
            class="balance-pill balance-pill--low"
            :class="{ 'is-active': balanceFilter.amount_bucket === 'low' }"
            @click="toggleBalanceBucket('low')"
          >
            合计0.1-500：{{ balanceCountLow }}
          </button>
          <button
            type="button"
            class="balance-pill balance-pill--high"
            :class="{ 'is-active': balanceFilter.amount_bucket === 'high' }"
            @click="toggleBalanceBucket('high')"
          >
            合计500以上：{{ balanceCountHigh }}
          </button>
        </div>
      </div>

      <div class="balance-sync-row">
        <button
          type="button"
          class="primary balance-sync-btn"
          :disabled="syncingBalances || loadingBalances"
          @click="syncBalancesFromPlatform"
        >
          {{ syncingBalances ? '正在同步…' : '同步最新余额' }}
        </button>
        <p class="balance-sync-hint">从中国石油油卡平台拉取最新余额并刷新本页</p>
      </div>
      <div v-if="syncStatus" class="sync-status">{{ syncStatus }}</div>
      <div v-if="msg" class="msg">{{ msg }}</div>

      <section class="balance-overview" aria-label="余额统计总览">
        <article class="balance-kpi">
          <div class="balance-kpi__label">总卡数</div>
          <div class="balance-kpi__value">{{ balancesTotal }}</div>
        </article>
        <article class="balance-kpi balance-kpi--amount">
          <div class="balance-kpi__label">合计金额</div>
          <div class="balance-kpi__value">{{ fmtMoney(balanceTotalAmount) }}</div>
          <div class="balance-kpi__hint">平均单卡 {{ fmtMoney(averageBalanceAmount) }}</div>
        </article>
        <article class="balance-kpi">
          <div class="balance-kpi__label">金额 0 档</div>
          <div class="balance-kpi__value">{{ balanceCountZero }}</div>
          <div class="balance-kpi__hint">占比 {{ fmtPercent(balanceCountZero, balancesTotal) }}</div>
        </article>
      </section>

      <section class="balance-breakdown" aria-label="金额区间分析">
        <button
          type="button"
          class="break-row"
          :class="{ 'is-active': balanceFilter.amount_bucket === 'zero' }"
          @click="toggleBalanceBucket('zero')"
        >
          <div class="break-row__label">合计=0</div>
          <div class="break-row__bar"><i :style="{ width: bucketBarWidth('zero') }" /></div>
          <div class="break-row__meta">{{ balanceCountZero }} 张 · {{ fmtMoney(balanceSumZero) }}</div>
        </button>
        <button
          type="button"
          class="break-row"
          :class="{ 'is-active': balanceFilter.amount_bucket === 'low' }"
          @click="toggleBalanceBucket('low')"
        >
          <div class="break-row__label">合计0.1-500</div>
          <div class="break-row__bar"><i :style="{ width: bucketBarWidth('low') }" /></div>
          <div class="break-row__meta">{{ balanceCountLow }} 张 · {{ fmtMoney(balanceSumLow) }}</div>
        </button>
        <button
          type="button"
          class="break-row"
          :class="{ 'is-active': balanceFilter.amount_bucket === 'high' }"
          @click="toggleBalanceBucket('high')"
        >
          <div class="break-row__label">合计500以上</div>
          <div class="break-row__bar"><i :style="{ width: bucketBarWidth('high') }" /></div>
          <div class="break-row__meta">{{ balanceCountHigh }} 张 · {{ fmtMoney(balanceSumHigh) }}</div>
        </button>
      </section>

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
        </div>
        <button type="button" class="primary rec-query" :disabled="loadingBalances" @click="searchBalances">
          {{ loadingBalances ? '查询中…' : '查询' }}
        </button>
      </div>

      <table class="tbl tbl-balances tbl--desktop">
        <thead>
          <tr>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('card_no')">卡号{{ sortMark('card_no') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('workshop')">车间{{ sortMark('workshop') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('vehicle_no')">车号{{ sortMark('vehicle_no') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('amount')">金额{{ sortMark('amount') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('reserve_fund')">备用金{{ sortMark('reserve_fund') }}</button></th>
            <th><button type="button" class="th-sort-btn" @click="toggleBalanceSort('total')">合计{{ sortMark('total') }}</button></th>
          </tr>
        </thead>
        <tbody v-if="loadingBalances">
          <tr><td colspan="6" class="hint">余额数据加载中…</td></tr>
        </tbody>
        <tbody v-else-if="!balances.length">
          <tr><td colspan="6" class="hint">暂无油卡余额数据。</td></tr>
        </tbody>
        <tbody v-else>
          <tr v-for="b in balances" :key="`bal-${b.id}`">
            <td>{{ b.card_no }}</td>
            <td>{{ b.workshop === '/' ? '—' : b.workshop || '—' }}</td>
            <td>{{ b.vehicle_no || '—' }}</td>
            <td>{{ b.amount }}</td>
            <td>{{ b.reserve_fund }}</td>
            <td>{{ b.total }}</td>
          </tr>
        </tbody>
      </table>

      <div class="balance-mobile" aria-live="polite">
        <p v-if="loadingBalances" class="hint balance-mobile__hint">余额数据加载中…</p>
        <p v-else-if="!balances.length" class="hint balance-mobile__hint">暂无油卡余额数据。</p>
        <ul v-else class="balance-cards" aria-label="油卡余额列表">
          <li v-for="b in balances" :key="`bal-m-${b.id}`" class="balance-card">
            <div class="balance-card__top">
              <span class="balance-card__card-no">{{ b.card_no }}</span>
              <span class="balance-card__total">合计 {{ b.total }}</span>
            </div>
            <div class="balance-card__line">
              <span class="balance-card__k">车间</span>
              <span class="balance-card__v">{{ b.workshop === '/' ? '—' : b.workshop || '—' }}</span>
            </div>
            <div class="balance-card__line">
              <span class="balance-card__k">车号</span>
              <span class="balance-card__v">{{ b.vehicle_no || '—' }}</span>
            </div>
            <div class="balance-card__grid">
              <div class="balance-card__stat">
                <span class="balance-card__sk">金额</span>
                <span class="balance-card__sv">{{ b.amount }}</span>
              </div>
              <div class="balance-card__stat">
                <span class="balance-card__sk">备用金</span>
                <span class="balance-card__sv">{{ b.reserve_fund }}</span>
              </div>
            </div>
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
import type { FuelBalance } from '@/api/fuel'

const balances = ref<FuelBalance[]>([])
const balanceWorkshops = ref<string[]>([])
const msg = ref('')
const syncStatus = ref('')
const syncingBalances = ref(false)
const loadingBalances = ref(false)
const balancesTotal = ref(0)
const balanceTotalAmount = ref('0')
const balanceCountZero = ref(0)
const balanceCountLow = ref(0)
const balanceCountHigh = ref(0)
const balanceSumZero = ref('0')
const balanceSumLow = ref('0')
const balanceSumHigh = ref('0')
const balancePage = ref(1)
const BALANCE_PAGE_SIZE = 15

const balanceFilter = reactive({
  workshop_id: 0,
  amount_bucket: '' as '' | 'zero' | 'low' | 'high',
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
    await fetchBalancePage()
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
    const res = await fuelApi.listFuelBalancesPaged({
      page: balancePage.value,
      page_size: BALANCE_PAGE_SIZE,
      ...(workshop ? { workshop } : {}),
      ...(balanceFilter.amount_bucket ? { amount_bucket: balanceFilter.amount_bucket } : {}),
      sort_by: balanceSort.by,
      sort_dir: balanceSort.dir,
    })
    balances.value = res.items
    balancesTotal.value = res.total
    balanceTotalAmount.value = res.total_amount
    balanceCountZero.value = res.count_zero
    balanceCountLow.value = res.count_low
    balanceCountHigh.value = res.count_high
    balanceSumZero.value = res.sum_zero
    balanceSumLow.value = res.sum_low
    balanceSumHigh.value = res.sum_high
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

function fmtPercent(part: number, total: number) {
  if (!total) return '0.0%'
  return `${((part / total) * 100).toFixed(1)}%`
}

function bucketBarWidth(bucket: 'zero' | 'low' | 'high') {
  const total = Number(balanceTotalAmount.value || 0)
  if (!total) return '0%'
  const mapping = {
    zero: Number(balanceSumZero.value || 0),
    low: Number(balanceSumLow.value || 0),
    high: Number(balanceSumHigh.value || 0),
  }
  return `${Math.max((mapping[bucket] / total) * 100, 2)}%`
}

function toggleBalanceBucket(bucket: 'zero' | 'low' | 'high') {
  balanceFilter.amount_bucket = balanceFilter.amount_bucket === bucket ? '' : bucket
  balancePage.value = 1
  void fetchBalancePage()
}

function searchBalances() {
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

.balance-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: var(--cl-olive);
  font-size: 12px;
}

.balance-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  cursor: pointer;
  font-family: inherit;
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease,
    filter 0.12s ease;
}

.balance-pill--zero {
  color: #7a1f1f;
  background: rgba(181, 51, 51, 0.12);
  border-color: rgba(181, 51, 51, 0.22);
}

.balance-pill--low {
  color: #6f4a18;
  background: rgba(196, 133, 34, 0.14);
  border-color: rgba(196, 133, 34, 0.24);
}

.balance-pill--high {
  color: #1d5e36;
  background: rgba(39, 143, 80, 0.14);
  border-color: rgba(39, 143, 80, 0.24);
}

.balance-pill:hover {
  filter: brightness(0.98);
}

.balance-pill.is-active {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(20, 20, 19, 0.15);
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

.balance-breakdown {
  border: 1px dashed rgba(201, 100, 66, 0.3);
  border-radius: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.66);
  margin-bottom: 12px;
  display: grid;
  gap: 8px;
}

.break-row {
  border: 0;
  width: 100%;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 170px;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  border-radius: 10px;
  transition: background-color 0.14s ease, box-shadow 0.14s ease;
}

.break-row:hover {
  background: rgba(201, 100, 66, 0.08);
}

.break-row.is-active {
  background: rgba(201, 100, 66, 0.13);
  box-shadow: inset 0 0 0 1px rgba(201, 100, 66, 0.22);
}

.break-row__label {
  font-size: 12px;
  color: var(--cl-charcoal);
  font-weight: 700;
}

.break-row__bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(77, 76, 72, 0.12);
  overflow: hidden;
}

.break-row__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(201, 100, 66, 0.82), rgba(181, 138, 90, 0.92));
}

.break-row.is-active .break-row__bar i {
  background: linear-gradient(90deg, rgba(201, 100, 66, 0.94), rgba(166, 116, 57, 0.98));
}

.break-row__meta {
  font-size: 12px;
  color: var(--cl-charcoal);
  text-align: right;
  font-variant-numeric: tabular-nums;
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

.balance-sync-row {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  margin: 4px 0 12px;
}

.balance-sync-btn {
  width: 100%;
  min-height: 44px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow:
    rgba(201, 100, 66, 0.28) 0 6px 18px -6px,
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.balance-sync-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.balance-sync-hint {
  margin: 0;
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

.tbl-balances tbody tr:nth-child(even) td {
  background: #fcfaf6;
}

.tbl-balances tbody tr:hover td {
  background: #f6f0e5;
}

.tbl-balances th:nth-child(1),
.tbl-balances td:nth-child(1) {
  width: 16%;
}

.tbl-balances th:nth-child(2),
.tbl-balances td:nth-child(2) {
  width: 14%;
}

.tbl-balances th:nth-child(3),
.tbl-balances td:nth-child(3) {
  width: 18%;
}

.tbl-balances th:nth-child(4),
.tbl-balances td:nth-child(4),
.tbl-balances th:nth-child(5),
.tbl-balances td:nth-child(5),
.tbl-balances th:nth-child(6),
.tbl-balances td:nth-child(6) {
  width: 17%;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.balance-mobile {
  display: none;
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

.balance-card__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.balance-card__card-no {
  font-size: 14px;
  font-weight: 800;
  color: var(--cl-near-black);
  word-break: break-all;
}

.balance-card__total {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 700;
}

.balance-card__line {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 8px;
  margin-top: 6px;
}

.balance-card__k {
  font-size: 11px;
  color: var(--cl-olive);
  font-weight: 700;
}

.balance-card__v {
  font-size: 13px;
  color: var(--cl-charcoal);
  word-break: break-word;
}

.balance-card__grid {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.balance-card__stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.balance-card__sk {
  font-size: 11px;
  color: var(--cl-olive);
  font-weight: 700;
}

.balance-card__sv {
  font-size: 14px;
  font-weight: 700;
  color: var(--cl-near-black);
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

@media (max-width: 768px) {
  .panel {
    padding: 12px;
    border-radius: 14px;
  }

  .rec-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .balance-overview {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .balance-breakdown {
    padding: 10px;
  }

  .break-row {
    grid-template-columns: 70px minmax(0, 1fr);
    gap: 8px;
  }

  .break-row__meta {
    grid-column: 1 / -1;
    text-align: left;
    margin-left: 78px;
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

  .rec-query {
    min-height: 44px;
    font-size: 15px;
    font-weight: 600;
    width: 100%;
  }

  .balance-sync-btn {
    min-height: 48px;
    font-size: 16px;
  }

  .balance-mobile {
    display: block;
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
