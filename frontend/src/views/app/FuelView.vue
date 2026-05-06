<template>
  <div class="stack fuel-view">
    <section class="panel rec-panel">
      <div class="hd">
        <h2>加油流水</h2>
      </div>
      <div v-if="msg" class="msg">{{ msg }}</div>
      <div class="rec-toolbar">
        <div class="rec-filters">
          <label class="inline-label">卡号</label>
          <SearchableSelect
            v-model="recFilter.card_asn_id"
            :options="recordCardOptions"
            allow-empty
            empty-label="全部"
            search-placeholder="输入卡号关键字…"
          />
          <label class="inline-label">车间</label>
          <SearchableSelect
            v-model="recFilter.workshop_id"
            :options="recordWorkshopOptions"
            allow-empty
            empty-label="全部"
            search-placeholder="输入车间关键字…"
          />
          <label class="inline-label">日期起</label>
          <div class="filter-field filter-field--date">
            <input v-model="recFilter.date_from" type="date" class="filter-control filter-date" />
          </div>
          <label class="inline-label">日期止</label>
          <div class="filter-field filter-field--date">
            <input v-model="recFilter.date_to" type="date" class="filter-control filter-date" />
          </div>
        </div>
        <div class="rec-actions">
          <button type="button" class="primary rec-query" :disabled="loadingRecords" @click="searchRecords">
            {{ loadingRecords ? '查询中…' : '查询' }}
          </button>
          <button type="button" class="ghost rec-query" :disabled="exportingRecords" @click="exportRecords">
            {{ exportingRecords ? '导出中…' : '导出Excel' }}
          </button>
        </div>
      </div>
      <table class="tbl tbl-records tbl--desktop">
        <thead>
          <tr>
            <th>序号</th>
            <th>油卡</th>
            <th>车辆</th>
            <th>
              <button type="button" class="th-sort-btn" @click="toggleRecordSort('workshop')">
                车间{{ recordSortMark('workshop') }}
              </button>
            </th>
            <th>
              <button type="button" class="th-sort-btn" @click="toggleRecordSort('occur_time')">
                日期{{ recordSortMark('occur_time') }}
              </button>
            </th>
            <th>升数</th>
            <th>单价</th>
            <th>金额</th>
            <th class="col-station">站点</th>
          </tr>
        </thead>
        <tbody v-if="!recordsSearched">
          <tr>
            <td colspan="9" class="hint">请设置筛选条件（可选）后点击「查询」加载流水，默认按时间倒序分页展示。</td>
          </tr>
        </tbody>
        <tbody v-else-if="loadingRecords">
          <tr>
            <td colspan="9" class="hint">加载中…</td>
          </tr>
        </tbody>
        <tbody v-else-if="!records.length">
          <tr>
            <td colspan="9" class="hint">当前条件下没有记录。</td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr v-for="(r, idx) in records" :key="r.id">
            <td>{{ displayRecordSeq(idx) }}</td>
            <td>{{ r.card_asn }}</td>
            <td>{{ r.car_no || '—' }}</td>
            <td>{{ r.workshop || '—' }}</td>
            <td>{{ formatOccurTime(r.occur_time) }}</td>
            <td>{{ r.volumn }}</td>
            <td>{{ unitPriceOf(r) }}</td>
            <td>{{ r.amount }}</td>
            <td class="col-station">{{ r.org_name || '—' }}</td>
          </tr>
        </tbody>
      </table>

      <div class="rec-mobile" aria-live="polite">
        <p v-if="!recordsSearched && !loadingRecords" class="hint rec-mobile__hint">
          请设置筛选条件（可选）后点击「查询」加载流水，默认按时间倒序分页展示。
        </p>
        <p v-else-if="loadingRecords" class="hint rec-mobile__hint">加载中…</p>
        <p v-else-if="!records.length" class="hint rec-mobile__hint">当前条件下没有记录。</p>
        <ul v-else class="fuel-rec-cards" aria-label="加油流水列表">
          <li v-for="(r, idx) in records" :key="`mob-${r.id}`" class="fuel-rec-card">
            <div class="fuel-rec-card__top">
              <span class="fuel-rec-card__id">序号 {{ displayRecordSeq(idx) }}</span>
              <span class="fuel-rec-card__date">{{ formatOccurTime(r.occur_time) }}</span>
            </div>
            <div class="fuel-rec-card__line">
              <span class="fuel-rec-card__k">油卡</span>
              <span class="fuel-rec-card__v">{{ r.card_asn }}</span>
            </div>
            <div class="fuel-rec-card__line">
              <span class="fuel-rec-card__k">车辆</span>
              <span class="fuel-rec-card__v">{{ r.car_no || '—' }}</span>
            </div>
            <div class="fuel-rec-card__line">
              <span class="fuel-rec-card__k">车间</span>
              <span class="fuel-rec-card__v">{{ r.workshop || '—' }}</span>
            </div>
            <div class="fuel-rec-card__grid">
              <div class="fuel-rec-card__stat">
                <span class="fuel-rec-card__sk">升数</span>
                <span class="fuel-rec-card__sv">{{ r.volumn }}</span>
              </div>
              <div class="fuel-rec-card__stat">
                <span class="fuel-rec-card__sk">单价</span>
                <span class="fuel-rec-card__sv">{{ unitPriceOf(r) }}</span>
              </div>
              <div class="fuel-rec-card__stat fuel-rec-card__stat--wide">
                <span class="fuel-rec-card__sk">金额</span>
                <span class="fuel-rec-card__sv">{{ r.amount }}</span>
              </div>
            </div>
            <div class="fuel-rec-card__station">
              <span class="fuel-rec-card__sk">站点</span>
              <p class="fuel-rec-card__station-text">{{ r.org_name || '—' }}</p>
            </div>
          </li>
        </ul>
      </div>

      <div v-if="recordsSearched && !loadingRecords" class="rec-pager">
        <span class="pager-meta">共 {{ recordsTotal }} 条</span>
        <label class="inline-label">每页</label>
        <select v-model.number="recFilter.page_size" class="filter-control pager-size" @change="onRecordPageSizeChange">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
        <span class="pager-meta">条</span>
        <button type="button" class="ghost pager-btn" :disabled="recFilter.page <= 1" @click="prevRecordPage">上一页</button>
        <span class="pager-meta">第 {{ recFilter.page }} / {{ totalRecordPages }} 页</span>
        <button type="button" class="ghost pager-btn" :disabled="recFilter.page >= totalRecordPages" @click="nextRecordPage">
          下一页
        </button>
      </div>
    </section>

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
          <button type="button" class="ghost" :disabled="loadingBalances" @click="reload">
            {{ loadingBalances ? '刷新中…' : '刷新余额' }}
          </button>
        </div>
      </div>

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
import type { FuelBalance, FuelRecord } from '@/api/fuel'

const records = ref<FuelRecord[]>([])
const balances = ref<FuelBalance[]>([])
const balanceWorkshops = ref<string[]>([])
const recordWorkshops = ref<string[]>([])
const recordCards = ref<string[]>([])
const msg = ref('')
const loadingRecords = ref(false)
const exportingRecords = ref(false)
const loadingBalances = ref(false)
const recordsSearched = ref(false)
const recordsTotal = ref(0)
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

const recFilter = reactive({
  card_asn_id: 0,
  workshop_id: 0,
  date_from: '',
  date_to: '',
  page: 1,
  page_size: 20,
})
const recSort = reactive({
  by: 'occur_time' as 'occur_time' | 'workshop' | 'amount' | 'volumn' | 'car_no' | 'card_asn',
  dir: 'desc' as 'asc' | 'desc',
})
const balanceFilter = reactive({
  workshop_id: 0,
  amount_bucket: '' as '' | 'zero' | 'low' | 'high',
})
const balanceSort = reactive({
  by: 'workshop' as 'card_no' | 'workshop' | 'vehicle_no' | 'amount' | 'reserve_fund' | 'total',
  dir: 'asc' as 'asc' | 'desc',
})

const totalRecordPages = computed(() =>
  Math.max(1, Math.ceil(recordsTotal.value / recFilter.page_size) || 1),
)
const balanceTotalPages = computed(() =>
  Math.max(1, Math.ceil(balancesTotal.value / BALANCE_PAGE_SIZE) || 1),
)
const averageBalanceAmount = computed(() =>
  balancesTotal.value ? Number(balanceTotalAmount.value || 0) / balancesTotal.value : 0,
)

const recordWorkshopOptions = computed<SearchableOption[]>(() =>
  recordWorkshops.value.map((unit, idx) => ({
    id: idx + 1,
    label: unit,
    keywords: unit,
  })),
)

const recordCardOptions = computed<SearchableOption[]>(() =>
  recordCards.value.map((card, idx) => ({
    id: idx + 1,
    label: card,
    keywords: card,
  })),
)

const balanceWorkshopOptions = computed<SearchableOption[]>(() =>
  balanceWorkshops.value.map((unit, idx) => ({
    id: idx + 1,
    label: unit,
    keywords: unit,
  })),
)

function selectedRecordWorkshopName(): string {
  if (!recFilter.workshop_id) return ''
  return recordWorkshopOptions.value.find((x) => x.id === recFilter.workshop_id)?.label ?? ''
}

function selectedRecordCardNo(): string {
  if (!recFilter.card_asn_id) return ''
  return recordCardOptions.value.find((x) => x.id === recFilter.card_asn_id)?.label ?? ''
}

function selectedBalanceWorkshopName(): string {
  if (!balanceFilter.workshop_id) return ''
  return balanceWorkshopOptions.value.find((x) => x.id === balanceFilter.workshop_id)?.label ?? ''
}

function formatOccurTime(raw: string) {
  if (!raw) return '—'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleString('zh-CN', { hour12: false })
}

function unitPriceOf(r: FuelRecord) {
  const vol = Number(r.volumn || 0)
  const amount = Number(r.amount || 0)
  if (vol <= 0) return '0.00'
  return (amount / vol).toFixed(2)
}

function displayRecordSeq(index: number) {
  return (recFilter.page - 1) * recFilter.page_size + index + 1
}

function toggleRecordSort(by: 'occur_time' | 'workshop' | 'amount' | 'volumn' | 'car_no' | 'card_asn') {
  if (recSort.by === by) {
    recSort.dir = recSort.dir === 'asc' ? 'desc' : 'asc'
  } else {
    recSort.by = by
    recSort.dir = 'asc'
  }
  recFilter.page = 1
  void fetchRecordsPage()
}

function recordSortMark(by: 'occur_time' | 'workshop' | 'amount' | 'volumn' | 'car_no' | 'card_asn') {
  if (recSort.by !== by) return ''
  return recSort.dir === 'asc' ? ' ↑' : ' ↓'
}

async function reload() {
  msg.value = ''
  loadingBalances.value = true
  try {
    const [bws, rws, cards] = await Promise.all([
      fuelApi.listFuelBalanceWorkshops(),
      fuelApi.listFuelRecordWorkshops(),
      fuelApi.listFuelRecordCards(),
    ])
    balanceWorkshops.value = bws
    recordWorkshops.value = rws
    recordCards.value = cards
    if (balancePage.value > balanceTotalPages.value) balancePage.value = 1
    await fetchBalancePage()
  } catch {
    msg.value = '加载油卡、车辆与余额数据失败'
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

function buildRecordQueryParams(): fuelApi.ListFuelRecordsParams {
  const params: fuelApi.ListFuelRecordsParams = {
    page: recFilter.page,
    page_size: recFilter.page_size,
    sort_by: recSort.by,
    sort_dir: recSort.dir,
  }
  const cardAsn = selectedRecordCardNo()
  if (cardAsn) params.card_asn = cardAsn
  const workshop = selectedRecordWorkshopName()
  if (workshop) params.workshop = workshop
  if (recFilter.date_from) params.date_from = recFilter.date_from
  if (recFilter.date_to) params.date_to = recFilter.date_to
  return params
}

async function fetchRecordsPage() {
  loadingRecords.value = true
  msg.value = ''
  try {
    const res = await fuelApi.listFuelRecordsPaged(buildRecordQueryParams())
    const maxPage = Math.max(1, Math.ceil(res.total / recFilter.page_size) || 1)
    if (res.total > 0 && recFilter.page > maxPage) {
      recFilter.page = maxPage
      const res2 = await fuelApi.listFuelRecordsPaged(buildRecordQueryParams())
      records.value = res2.items
      recordsTotal.value = res2.total
    } else {
      records.value = res.items
      recordsTotal.value = res.total
    }
    recordsSearched.value = true
  } catch {
    msg.value = '加载加油流水失败'
  } finally {
    loadingRecords.value = false
  }
}

function searchRecords() {
  recFilter.page = 1
  void fetchRecordsPage()
}

async function exportRecords() {
  exportingRecords.value = true
  try {
    const blob = await fuelApi.exportFuelRecordsExcel(buildRecordQueryParams())
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `fuel_records_${new Date().toISOString().slice(0, 10)}.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch {
    msg.value = '导出加油流水失败'
  } finally {
    exportingRecords.value = false
  }
}

function onRecordPageSizeChange() {
  recFilter.page = 1
  if (recordsSearched.value) void fetchRecordsPage()
}

function prevRecordPage() {
  if (recFilter.page <= 1) return
  recFilter.page -= 1
  void fetchRecordsPage()
}

function nextRecordPage() {
  if (recFilter.page >= totalRecordPages.value) return
  recFilter.page += 1
  void fetchRecordsPage()
}

onMounted(reload)
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

.balance-panel {
  order: 1;
}

.rec-panel {
  order: 2;
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

.rec-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.hint {
  padding: 16px 10px;
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
}

.tbl-records .col-station {
  max-width: 300px;
  white-space: normal;
  word-break: break-word;
  line-height: 1.4;
  vertical-align: top;
}

.tbl-records {
  table-layout: fixed;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  overflow: hidden;
  background: var(--cl-white);
}

.tbl-records th:nth-child(1),
.tbl-records td:nth-child(1) {
  width: 7%;
  text-align: center;
}

.tbl-records th:nth-child(2),
.tbl-records td:nth-child(2) {
  width: 16%;
}

.tbl-records th:nth-child(3),
.tbl-records td:nth-child(3) {
  width: 12%;
}

.tbl-records th:nth-child(4),
.tbl-records td:nth-child(4) {
  width: 11%;
}

.tbl-records th:nth-child(5),
.tbl-records td:nth-child(5),
.tbl-records th:nth-child(6),
.tbl-records td:nth-child(6),
.tbl-records th:nth-child(7),
.tbl-records td:nth-child(7) {
  width: 10%;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.tbl-records th:nth-child(8),
.tbl-records td:nth-child(8) {
  width: 9%;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.tbl-records th:nth-child(9),
.tbl-records td:nth-child(9) {
  width: 26%;
}

.tbl-records tbody tr:nth-child(even) td {
  background: #fcfaf6;
}

.tbl-records tbody tr:hover td {
  background: #f6f0e5;
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

.rec-mobile {
  display: none;
}

.fuel-rec-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fuel-rec-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  background: var(--cl-ivory);
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.04) 0 4px 16px;
}

.fuel-rec-card__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.fuel-rec-card__id {
  font-size: 12px;
  font-weight: 700;
  color: var(--cl-olive);
}

.fuel-rec-card__date {
  font-size: 13px;
  color: var(--cl-charcoal);
  font-weight: 600;
}

.fuel-rec-card__line {
  display: grid;
  grid-template-columns: 44px 1fr;
  gap: 8px 10px;
  align-items: baseline;
  font-size: 13px;
  margin-bottom: 6px;
}

.fuel-rec-card__k {
  color: var(--cl-olive);
  font-size: 12px;
  font-weight: 700;
}

.fuel-rec-card__v {
  color: var(--cl-near-black);
  font-weight: 800;
  word-break: break-all;
}

.fuel-rec-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
  margin: 12px 0;
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
}

.fuel-rec-card__stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fuel-rec-card__stat--wide {
  grid-column: 1 / -1;
}

.fuel-rec-card__sk {
  font-size: 11px;
  font-weight: 700;
  color: var(--cl-olive);
  text-transform: none;
}

.fuel-rec-card__sv {
  font-size: 14px;
  font-weight: 700;
  color: var(--cl-near-black);
}

.fuel-rec-card__station {
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
}

.fuel-rec-card__station .fuel-rec-card__sk {
  display: block;
  margin-bottom: 6px;
}

.fuel-rec-card__station-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--cl-charcoal);
  word-break: break-word;
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
  }

  .rec-actions {
    width: 100%;
    margin-left: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .rec-actions .rec-query {
    width: 100%;
  }

  .tbl--desktop {
    display: none;
  }

  .rec-mobile {
    display: block;
  }

  .balance-mobile {
    display: block;
  }

  .balance-mobile__hint {
    margin: 0 0 8px;
  }

  .rec-mobile__hint {
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
