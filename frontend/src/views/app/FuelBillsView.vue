<template>
  <div class="stack fuel-bills-view">
    <section class="panel rec-panel">
      <div class="hd">
        <h2>账单明细</h2>
        <span class="record-count">{{ recordsTotal }} <span>条记录</span></span>
        <div class="rec-actions">
          <button type="button" class="primary rec-query" :disabled="syncingRecords" @click="searchRecords()">
            {{ syncingRecords ? '查询中…' : '查询账单' }}
          </button>
          <button type="button" class="ghost rec-query" :disabled="syncingRecords" @click="searchRecords(true)">
            更新昆仑账单
          </button>
          <button type="button" class="ghost rec-query" :disabled="exportingRecords || syncingRecords" @click="exportRecords">
            {{ exportingRecords ? '导出中…' : '导出 Excel' }}
          </button>
        </div>
      </div>
      <div class="rec-toolbar">
        <div class="rec-filters">
          <div class="filter-group">
            <span class="filter-label">油卡</span>
            <SearchableSelect
              v-model="recFilter.card_asn_id"
              :options="recordCardOptions"
              :disabled="syncingRecords"
              allow-empty
              empty-label="全部油卡"
              search-placeholder="输入车号或卡号关键字…"
              aria-label="油卡筛选"
            />
          </div>
          <div class="filter-group">
            <span class="filter-label">车间</span>
            <SearchableSelect
              v-model="recFilter.workshop_id"
              :options="recordWorkshopOptions"
              :disabled="syncingRecords"
              allow-empty
              empty-label="全部车间"
              search-placeholder="输入车间关键字…"
              aria-label="车间筛选"
            />
          </div>
          <div class="filter-group">
            <span class="filter-label">车牌号</span>
            <SearchableSelect
              v-model="recFilter.vehicle_id"
              :options="recordVehicleOptions"
              :disabled="syncingRecords"
              allow-empty
              empty-label="全部车辆"
              search-placeholder="输入车牌号关键字…"
              aria-label="车牌号筛选"
            />
          </div>
          <div class="filter-group filter-group--date">
            <label class="filter-label" for="bill-date-from">开始日期</label>
            <input id="bill-date-from" v-model="recFilter.date_from" type="date" :disabled="syncingRecords" class="filter-control filter-date" />
          </div>
          <div class="filter-group filter-group--date">
            <label class="filter-label" for="bill-date-to">结束日期</label>
            <input id="bill-date-to" v-model="recFilter.date_to" type="date" :disabled="syncingRecords" class="filter-control filter-date" />
          </div>
        </div>
      </div>
      <FuelQueryStatus :message="syncStatus" :active="syncingRecords" title="正在查询账单" />
      <div v-if="msg" class="msg" role="alert">{{ msg }}</div>
      <div class="list-toolbar">
        <span class="list-caption">查询优先读取已保存账单，筛选后自动更新列表；新增账单可点击“更新昆仑账单”</span>
        <div class="sort-actions" aria-label="账单排序">
          <span class="sort-label">排序</span>
          <button type="button" class="active" :disabled="syncingRecords" @click="toggleRecordSort('occur_time')">
            <span class="sort-priority">{{ recSort.by === 'occur_time' ? 1 : 2 }}</span> 日期{{ recordSortMark('occur_time') }}
          </button>
          <button type="button" class="active" :disabled="syncingRecords" @click="toggleRecordSort('car_no')">
            <span class="sort-priority">{{ recSort.by === 'car_no' ? 1 : 2 }}</span> 车号{{ recordSortMark('car_no') }}
          </button>
          <button type="button" :disabled="syncingRecords" aria-label="交换日期与车号的排序优先级" @click="swapRecordSort">交换优先级</button>
        </div>
      </div>
      <div v-if="!isMobileRecords" class="rec-table-wrap">
        <table class="tbl-records" aria-label="油卡账单列表">
          <thead>
            <tr>
              <th class="col-date">日期</th>
              <th class="col-vehicle">车号</th>
              <th class="col-card desktop-only">油卡</th>
              <th class="col-workshop desktop-only">车间</th>
              <th class="col-volume desktop-only">升数 / L</th>
              <th class="col-price desktop-only">单价 / 元</th>
              <th class="col-amount">金额 / 元</th>
              <th class="col-station desktop-only">站点</th>
              <th class="col-actions desktop-only">操作</th>
            </tr>
          </thead>
          <tbody v-if="loadingRecords || !recordsSearched || !records.length">
            <tr><td colspan="9" class="hint">{{ loadingRecords || !recordsSearched ? '正在加载账单…' : '当前条件下没有记录。' }}</td></tr>
          </tbody>
          <tbody v-else>
            <tr v-for="r in records" :key="r.id" class="motion-row">
              <td class="col-date">
                <span class="bill-date">{{ formatBillDate(r.occur_time) }}</span>
                <span class="bill-time">{{ formatBillTime(r.occur_time) }}</span>
              </td>
              <td class="col-vehicle">
                <span class="bill-vehicle">{{ r.car_no || '—' }}</span>
                <span class="bill-oil">油品 {{ r.gift_name || '—' }}</span>
              </td>
              <td class="col-card desktop-only">{{ r.card_asn || '—' }}</td>
              <td class="col-workshop desktop-only">{{ r.workshop || '—' }}</td>
              <td class="col-volume desktop-only">{{ r.volume_available ? r.volumn : '—' }}</td>
              <td class="col-price desktop-only">{{ unitPriceOf(r) }}</td>
              <td class="col-amount">
                <span class="bill-amount">{{ r.amount }}</span>
              </td>
              <td class="col-station desktop-only">{{ r.org_name || '—' }}</td>
              <td class="col-actions desktop-only"><button type="button" class="ghost bill-detail-btn" @click="openBillDetail(r)">查看详情</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="mobile-bills" aria-label="油卡账单列表">
        <p v-if="loadingRecords || !recordsSearched || !records.length" class="mobile-bills-empty hint" role="status">
          {{ loadingRecords || !recordsSearched ? '正在加载账单…' : '当前条件下没有记录。' }}
        </p>
        <article v-for="r in records" v-else :key="r.id" class="mobile-bill">
          <div class="mobile-bill-heading">
            <div class="mobile-bill-identity">
              <h3>{{ r.car_no || '未关联车辆' }}</h3>
              <span>{{ formatBillDate(r.occur_time) }} {{ formatBillTime(r.occur_time) }}</span>
            </div>
            <strong class="mobile-bill-amount"><span>¥</span> {{ r.amount }}</strong>
          </div>
          <div class="mobile-bill-facts">
            <span>{{ r.workshop || '未关联车间' }}</span>
            <span>{{ r.volume_available ? `${r.volumn} L` : '升数 —' }}<span class="fact-separator">·</span>{{ unitPriceOf(r) }} 元/L</span>
          </div>
          <dl class="mobile-bill-meta">
            <div><dt>油品</dt><dd>{{ r.gift_name || '—' }}</dd></div>
            <div><dt>卡号</dt><dd class="mobile-bill-card">{{ r.card_asn || '—' }}</dd></div>
            <div><dt>站点</dt><dd>{{ r.org_name || '站点未提供' }}</dd></div>
          </dl>
          <div class="mobile-bill-footer">
            <button type="button" class="ghost" :aria-label="`查看 ${r.car_no || r.card_asn} 账单详情`" @click="openBillDetail(r)">查看详情 <span aria-hidden="true">→</span></button>
          </div>
        </article>
      </div>
      <div v-if="isMobileRecords && recordsSearched && !loadingRecords && records.length" ref="recordMobileLoadMoreRef" class="scroll-loader" role="status">
        <span v-if="loadingMoreRecords">正在加载更多账单…</span>
        <button v-else-if="hasMoreRecords" type="button" class="ghost" @click="loadMoreRecords">加载更多 · {{ records.length }} / {{ recordsTotal }} 条</button>
        <span v-else>已加载全部 {{ recordsTotal }} 条账单</span>
      </div>

      <div v-if="recordsSearched && !loadingRecords && !isMobileRecords" class="rec-pager">
        <span class="pager-meta">共 {{ recordsTotal }} 条</span>
        <label class="inline-label">每页</label>
        <select v-model.number="recFilter.page_size" class="filter-control pager-size" :disabled="syncingRecords" @change="onRecordPageSizeChange">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
        <span class="pager-meta">条</span>
        <button type="button" class="ghost pager-btn" :disabled="syncingRecords || recFilter.page <= 1" @click="prevRecordPage">上一页</button>
        <span class="pager-meta">第 {{ recFilter.page }} / {{ totalRecordPages }} 页</span>
        <button type="button" class="ghost pager-btn" :disabled="syncingRecords || recFilter.page >= totalRecordPages" @click="nextRecordPage">
          下一页
        </button>
      </div>
    </section>
    <AppModal :open="!!selectedBill" title="账单详情" @close="closeBillDetail">
      <div v-if="selectedBill" class="bill-detail">
        <div class="detail-summary">
          <div><strong>{{ selectedBill.car_no || '未关联车辆' }}</strong><span>{{ formatBillDate(selectedBill.occur_time) }} {{ formatBillTime(selectedBill.occur_time) }}</span></div>
          <div class="detail-summary__amount"><strong>¥ {{ selectedBill.amount }}</strong><span>账单金额</span></div>
        </div>
        <p v-if="detailLoading" class="detail-notice" role="status">正在加载昆仑账单及商品明细…</p>
        <div v-if="detailError" class="detail-notice detail-notice--error" role="alert">{{ detailError }} <button type="button" class="ghost bill-detail-btn" @click="openBillDetail(selectedBill)">重试</button></div>
        <section v-for="group in detailGroups" :key="group.title" class="detail-section">
          <h3>{{ group.title }}</h3>
          <dl class="detail-grid"><div v-for="field in group.fields" :key="field.label"><dt>{{ field.label }}</dt><dd>{{ field.value }}</dd></div></dl>
        </section>
        <p v-if="!detailLoading && !selectedBill.platform_data" class="detail-notice">此账单尚未保存昆仑完整信息，请点击“查询账单”更新后查看。</p>
        <section v-if="selectedBill.platform_data" class="detail-section">
          <h3>商品明细 <span v-if="detailProducts.length">· {{ detailProducts.length }} 项</span></h3>
          <div v-for="(product, index) in detailProducts" :key="index" class="detail-product">
            <dl class="detail-grid"><div v-for="field in productFields" :key="field.key"><dt>{{ field.label }}</dt><dd>{{ detailValue(product[field.key]) }}</dd></div></dl>
          </div>
          <p v-if="!detailLoading && !detailProducts.length" class="detail-notice">{{ selectedBill.product_detail_error || '昆仑未提供商品明细。' }}</p>
        </section>
      </div>
      <template #footer><button type="button" class="ghost" @click="closeBillDetail">关闭</button></template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import * as fuelApi from '@/api/fuel'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import AppModal from '@/components/AppModal.vue'
import FuelQueryStatus from '@/components/FuelQueryStatus.vue'
import type { FuelRecord, FuelRecordDetail } from '@/api/fuel'

const selectedBill = ref<FuelRecordDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
let detailRequest = 0
const productFields = [
  { key: 'productName', label: '商品名称' }, { key: 'productCode', label: '商品编码' },
  { key: 'productType', label: '商品品类' }, { key: 'priceUnit', label: '单价（元）' },
  { key: 'unit', label: '单位' }, { key: 'productQty', label: '数量' },
]
function detailValue(value: unknown): string {
  return value === null || value === undefined || value === '' ? '—' : String(value)
}
function transactionType(value: unknown) {
  const labels: Record<string, string> = {
    '7': '室外支付', '8': '室内扫码', '9': '预授权', '10': '好客商城消费', '11': '掌纹付',
    '12': '实体卡预授权', '13': '实体卡后付费', '14': '室内实体卡消费', '15': '加油卡归集',
    '16': '分配汇总', '17': '客户迁移', '18': '昆仑网电预授权', '19': '支付宝碰一碰',
  }
  return labels[String(value)] || detailValue(value)
}
const detailProducts = computed(() => {
  const products = selectedBill.value?.platform_data?.productDetails
  return Array.isArray(products) ? products.filter((p): p is Record<string, unknown> => !!p && typeof p === 'object') : []
})
const detailGroups = computed(() => {
  const r = selectedBill.value
  if (!r) return []
  const p = r.platform_data || {}
  const fields = (pairs: [string, unknown][]) => pairs.map(([label, value]) => ({ label, value: detailValue(value) }))
  return [
    { title: '车辆与油卡', fields: fields([
      ['车牌号', r.car_no], ['车间', r.workshop], ['油卡卡号', r.card_asn], ['油品品号', r.gift_name],
      ['加油站', r.org_name], ['油量（L）', r.volume_available ? r.volumn : null],
      ['折后均价（元/L）', unitPriceOf(r)], ['交易后余额（元）', r.balance_available ? r.balance : null],
    ]) },
    ...(r.platform_data ? [
      { title: '昆仑订单与交易', fields: fields([
        ['订单号', p.orderNo], ['订单时间', p.orderTime], ['交易流水号', p.transRecordNo],
        ['商品品类', p.productTypeName], ['实付总额（元）', p.actualPayTotalAmount],
        ['交易所属机构', p.transactionPlaceName], ['交易子类型', transactionType(p.transactionSubType)], ['平台车牌号', p.licensePlate],
      ]) },
      { title: '金额与优惠', fields: fields([
        ['油品应收（元）', p.oilReceivableAmount], ['油品实收（元）', p.oilReceivedAmount], ['油品折扣（元）', p.oilDiscountAmount],
        ['非油商品', p.nonfuelProductName], ['非油应收（元）', p.nonfuelReceivableAmount],
        ['非油实收（元）', p.nonfuelReceivedAmount], ['非油折扣（元）', p.nonfuelDiscountAmount],
      ]) },
      { title: '驾驶员与会员', fields: fields([
        ['驾驶员姓名', p.driverName], ['驾驶员编号', p.staffNo], ['账户编号', p.accountNo],
        ['会员名称', p.memberName], ['会员手机号', p.memberPhone],
      ]) },
    ] : []),
  ]
})
async function openBillDetail(row: FuelRecord) {
  const request = ++detailRequest
  selectedBill.value = { ...row, platform_data: null, product_detail_error: null }
  detailLoading.value = true
  detailError.value = ''
  try {
    const detail = await fuelApi.getFuelRecordDetail(row.id)
    if (request !== detailRequest) return
    selectedBill.value = detail
    detailError.value = detail.product_detail_error || ''
  } catch {
    if (request === detailRequest) detailError.value = '详情加载失败，请稍后重试。'
  } finally {
    if (request === detailRequest) detailLoading.value = false
  }
}
function closeBillDetail() {
  detailRequest++
  selectedBill.value = null
  detailLoading.value = false
  detailError.value = ''
}

const records = ref<FuelRecord[]>([])
const recordWorkshops = ref<string[]>([])
const recordCards = ref<fuelApi.FuelRecordCardOption[]>([])
const recordVehicles = ref<string[]>([])
const msg = ref('')
const syncStatus = ref('')
const syncingRecords = ref(false)
const loadingRecords = ref(false)
const exportingRecords = ref(false)
const recordsSearched = ref(false)
const recordsTotal = ref(0)
const loadingMoreRecords = ref(false)
const recordMobileLoadMoreRef = ref<HTMLElement | null>(null)
const isMobileRecords = ref(typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches)
let recordLoadObserver: IntersectionObserver | null = null
let recordMobileMediaQuery: MediaQueryList | null = null

const recFilter = reactive({
  card_asn_id: 0,
  workshop_id: 0,
  vehicle_id: 0,
  date_from: '',
  date_to: '',
  page: 1,
  page_size: 20,
})
const recSort = reactive({
  by: 'occur_time' as 'occur_time' | 'car_no',
  dir: 'desc' as 'asc' | 'desc',
  secondary_by: 'car_no' as 'occur_time' | 'car_no',
  secondary_dir: 'asc' as 'asc' | 'desc',
})
let recordsRequest = 0
let filtersPaused = false

watch(
  () => [recFilter.card_asn_id, recFilter.workshop_id, recFilter.vehicle_id,
    recFilter.date_from, recFilter.date_to, recSort.by, recSort.dir, recSort.secondary_by, recSort.secondary_dir],
  () => {
    if (!recordsSearched.value || syncingRecords.value || filtersPaused) return
    recFilter.page = 1
    if (recFilter.date_from && recFilter.date_to && recFilter.date_from > recFilter.date_to) {
      recordsRequest++
      loadingRecords.value = false
      loadingMoreRecords.value = false
      recordLoadObserver?.disconnect()
      msg.value = '起始日期不能晚于截止日期'
      return
    }
    void fetchRecordsPage()
  },
)

const totalRecordPages = computed(() =>
  Math.max(1, Math.ceil(recordsTotal.value / recFilter.page_size) || 1),
)
const hasMoreRecords = computed(() => records.value.length < recordsTotal.value)

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
    label: `${card.car_no || '未关联车辆'}：${card.card_asn}`,
    keywords: `${card.car_no} ${card.card_asn}`,
  })),
)

const recordVehicleOptions = computed<SearchableOption[]>(() =>
  recordVehicles.value.map((plate, idx) => ({ id: idx + 1, label: plate, keywords: plate })),
)

function selectedRecordVehicle(): string {
  return recordVehicleOptions.value.find((x) => x.id === recFilter.vehicle_id)?.label ?? ''
}

function selectedRecordWorkshopName(): string {
  if (!recFilter.workshop_id) return ''
  return recordWorkshopOptions.value.find((x) => x.id === recFilter.workshop_id)?.label ?? ''
}

function selectedRecordCardNo(): string {
  if (!recFilter.card_asn_id) return ''
  return recordCards.value[recFilter.card_asn_id - 1]?.card_asn ?? ''
}

function monthStartIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function ensureRecordDateRange() {
  if (!recFilter.date_from) recFilter.date_from = monthStartIso()
  if (!recFilter.date_to) recFilter.date_to = todayIso()
}

function billDate(raw: string) {
  // SQLite 返回的无时区时间遵循后端约定，按 UTC 解读。
  return new Date(/[zZ]$|[+-]\d{2}:\d{2}$/.test(raw) ? raw : `${raw}Z`)
}

function formatBillDate(raw: string) {
  const d = billDate(raw)
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatBillTime(raw: string) {
  const d = billDate(raw)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false, hour: '2-digit', minute: '2-digit' })
}

function unitPriceOf(r: FuelRecord) {
  if (!r.volume_available) return '—'
  const vol = Number(r.volumn || 0)
  const amount = Number(r.amount || 0)
  if (vol <= 0) return '0.00'
  return (amount / vol).toFixed(2)
}

function toggleRecordSort(by: 'occur_time' | 'car_no') {
  if (recSort.by === by) {
    recSort.dir = recSort.dir === 'asc' ? 'desc' : 'asc'
  } else {
    recSort.secondary_dir = recSort.secondary_dir === 'asc' ? 'desc' : 'asc'
  }
}

function swapRecordSort() {
  const { by, dir } = recSort
  recSort.by = recSort.secondary_by
  recSort.dir = recSort.secondary_dir
  recSort.secondary_by = by
  recSort.secondary_dir = dir
}

function recordSortMark(by: 'occur_time' | 'car_no') {
  const dir = recSort.by === by ? recSort.dir : recSort.secondary_dir
  return dir === 'asc' ? ' ↑' : ' ↓'
}

async function reload() {
  msg.value = ''
  loadingRecords.value = true
  try {
    const [rws, cards, vehicles] = await Promise.all([
      fuelApi.listFuelRecordWorkshops(),
      fuelApi.listFuelRecordCardOptions(),
      fuelApi.listFuelRecordVehicles(),
    ])
    recordWorkshops.value = rws
    recordCards.value = cards
    recordVehicles.value = vehicles
    recFilter.page = 1
    await fetchRecordsPage()
    recordsSearched.value = true
  } catch {
    msg.value = '加载加油流水失败'
  } finally {
    loadingRecords.value = false
  }
}

function buildRecordQueryParams(): fuelApi.ListFuelRecordsParams {
  const params: fuelApi.ListFuelRecordsParams = {
    has_card_only: true,
    page: recFilter.page,
    page_size: recFilter.page_size,
    sort_by: recSort.by,
    sort_dir: recSort.dir,
    sort_secondary_by: recSort.secondary_by,
    sort_secondary_dir: recSort.secondary_dir,
  }
  const vehicle = selectedRecordVehicle()
  if (vehicle) params.car_no = vehicle
  const cardAsn = selectedRecordCardNo()
  if (cardAsn) params.card_asn = cardAsn
  const workshop = selectedRecordWorkshopName()
  if (workshop) params.workshop = workshop
  if (recFilter.date_from) params.date_from = recFilter.date_from
  if (recFilter.date_to) params.date_to = recFilter.date_to
  return params
}

async function fetchRecordsPage(append = false, background = false) {
  const request = ++recordsRequest
  const params = buildRecordQueryParams()
  if (append) loadingMoreRecords.value = true
  else {
    loadingMoreRecords.value = false
    if (!background) loadingRecords.value = true
  }
  msg.value = ''
  try {
    const res = await fuelApi.listFuelRecordsPaged(params)
    if (request !== recordsRequest) return false
    const maxPage = Math.max(1, Math.ceil(res.total / recFilter.page_size) || 1)
    if (res.total > 0 && recFilter.page > maxPage) {
      recFilter.page = maxPage
      const res2 = await fuelApi.listFuelRecordsPaged({ ...params, page: maxPage })
      if (request !== recordsRequest) return false
      records.value = res2.items
      recordsTotal.value = res2.total
    } else {
      records.value = append ? [...records.value, ...res.items] : res.items
      recordsTotal.value = res.total
    }
    recordsSearched.value = true
    return true
  } catch {
    if (request === recordsRequest) msg.value = '加载加油流水失败'
    return false
  } finally {
    if (request === recordsRequest) {
      if (append) loadingMoreRecords.value = false
      else if (!background) loadingRecords.value = false
      await nextTick()
      if (request === recordsRequest) setupRecordLoadObserver()
    }
  }
}

async function loadMoreRecords() {
  if (syncingRecords.value || !isMobileRecords.value || loadingRecords.value || loadingMoreRecords.value || !hasMoreRecords.value) return
  recFilter.page += 1
  const request = recordsRequest + 1
  const ok = await fetchRecordsPage(true)
  if (!ok && request === recordsRequest) recFilter.page = Math.max(1, recFilter.page - 1)
}

function setupRecordLoadObserver() {
  recordLoadObserver?.disconnect()
  recordLoadObserver = null
  if (!isMobileRecords.value || typeof IntersectionObserver === 'undefined') return
  const target = recordMobileLoadMoreRef.value
  if (!target) return
  recordLoadObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMoreRecords()
    },
    { rootMargin: '120px 0px' },
  )
  recordLoadObserver.observe(target)
}

function onRecordViewportChange(event: MediaQueryListEvent | MediaQueryList) {
  const changed = isMobileRecords.value !== event.matches
  isMobileRecords.value = event.matches
  if (!changed) return
  recFilter.page = 1
  void fetchRecordsPage()
}

async function searchRecords(forceSync = false) {
  if (syncingRecords.value) return
  ensureRecordDateRange()
  if (recFilter.date_from > recFilter.date_to) {
    msg.value = '起始日期不能晚于截止日期'
    return
  }
  recFilter.page = 1
  syncingRecords.value = true
  loadingRecords.value = true
  msg.value = ''
  syncStatus.value = '正在读取已保存账单…'
  const loaded = await fetchRecordsPage()
  // 读取失败不能当成“数据库没有数据”，也不能使用上次查询的总数。
  if (!loaded || (!forceSync && recordsTotal.value > 0)) {
    syncStatus.value = loaded ? `共 ${recordsTotal.value} 条账单` : ''
    syncingRecords.value = false
    loadingRecords.value = false
    setupRecordLoadObserver()
    return
  }
  syncStatus.value = forceSync ? '正在更新昆仑账单…' : '没有已保存账单，正在查询昆仑并保存…'
  try {
    const result = await fuelApi.syncFuelFromPlatform(
      {
        target: 'bills',
        date_from: recFilter.date_from,
        date_to: recFilter.date_to,
      },
      (message) => {
        syncStatus.value = message
      },
      async () => {
        await fetchRecordsPage(false, true)
      },
    )
    syncStatus.value = `共 ${result.record_written ?? 0} 条账单`
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '同步中国石油油卡数据失败'
    syncStatus.value = ''
    loadingRecords.value = false
    syncingRecords.value = false
    return
  }

  const completedStatus = syncStatus.value
  syncStatus.value = '账单已获取，正在刷新列表…'
  const selectedCard = selectedRecordCardNo()
  const selectedWorkshop = selectedRecordWorkshopName()
  const selectedVehicle = selectedRecordVehicle()
  loadingRecords.value = true
  filtersPaused = true
  try {
    const [rws, cards, vehicles] = await Promise.all([
      fuelApi.listFuelRecordWorkshops(),
      fuelApi.listFuelRecordCardOptions(),
      fuelApi.listFuelRecordVehicles(),
    ])
    recordWorkshops.value = rws
    recordCards.value = cards
    recordVehicles.value = vehicles
    const selectedCardIndex = recordCards.value.findIndex((card) => card.card_asn === selectedCard)
    recFilter.card_asn_id = selectedCardIndex < 0 ? 0 : selectedCardIndex + 1
    recFilter.workshop_id = recordWorkshopOptions.value.find((x) => x.label === selectedWorkshop)?.id ?? 0
    recFilter.vehicle_id = recordVehicleOptions.value.find((x) => x.label === selectedVehicle)?.id ?? 0
    await nextTick()
    filtersPaused = false
    await fetchRecordsPage()
    recordsSearched.value = true
    syncStatus.value = completedStatus
  } catch {
    msg.value = '数据已同步，但刷新加油流水失败，请稍后重试'
    syncStatus.value = ''
  } finally {
    syncingRecords.value = false
    filtersPaused = false
    loadingRecords.value = false
  }
}

async function exportRecords() {
  if (recFilter.date_from && recFilter.date_to && recFilter.date_from > recFilter.date_to) {
    msg.value = '起始日期不能晚于截止日期'
    return
  }
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

onMounted(() => {
  recordMobileMediaQuery = window.matchMedia('(max-width: 768px)')
  recordMobileMediaQuery.addEventListener('change', onRecordViewportChange)
  ensureRecordDateRange()
  void reload()
})

onBeforeUnmount(() => {
  recordsRequest++
  recordLoadObserver?.disconnect()
  recordMobileMediaQuery?.removeEventListener('change', onRecordViewportChange)
})
</script>

<style scoped>
.fuel-bills-view {
  width: 100%;
  min-width: 0;
}
.rec-panel {
  padding: 16px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 16px;
  background: var(--cl-ivory);
  min-width: 0;
  box-sizing: border-box;
}
.hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.hd h2 { margin: 0; font-size: 16px; font-weight: 600; }
.record-count { margin-left: auto; color: var(--cl-charcoal); font-size: 15px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.record-count span { color: var(--cl-olive); font-size: 12px; margin-left: 4px; }
.rec-toolbar { margin-bottom: 10px; }
.rec-filters { display: grid; grid-template-columns: minmax(140px, 1.3fr) minmax(90px, .8fr) minmax(110px, 1fr) repeat(2, minmax(130px, 1fr)); gap: 8px; min-width: 0; }
.filter-group { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.filter-label, .inline-label { color: var(--cl-olive); font-size: 12px; }
.filter-control { height: 40px; padding: 0 10px; border: 1px solid var(--cl-border-cream); border-radius: 8px; background: var(--cl-white); color: var(--cl-charcoal); font: inherit; font-size: 13px; min-width: 0; box-sizing: border-box; }
.filter-date { width: 100%; }
.filter-group :deep(.searchable-select) { flex: none; width: 100%; max-width: none; min-width: 0; }
.filter-group :deep(.searchable-select__trigger) { width: 100%; height: 40px; min-height: 40px; border-radius: 8px; padding: 0 10px; font-size: 13px; box-sizing: border-box; }
.rec-actions { display: flex; gap: 6px; }
.primary, .ghost { min-height: 40px; padding: 0 14px; border-radius: 8px; font: inherit; font-size: 13px; font-weight: 500; white-space: nowrap; cursor: pointer; }
.rec-query { min-height: 34px; padding: 0 10px; }
.primary { border: 1px solid var(--cl-brand); background: var(--cl-brand); color: var(--cl-white); }
.ghost { border: 1px solid var(--cl-border-warm); background: var(--cl-white); color: var(--cl-charcoal); }
.primary:hover:not(:disabled) { filter: brightness(.95); }
.ghost:hover:not(:disabled) { background: var(--cl-warm-sand); }
button:disabled { opacity: .55; cursor: not-allowed; }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--cl-brand); outline-offset: 2px; }
.msg { margin-bottom: 16px; padding: 10px 12px; border-radius: 8px; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; }
.msg { background: rgba(181, 51, 51, .08); color: var(--cl-error); }
.rec-table-wrap { overflow-x: auto; border: 1px solid var(--cl-border-cream); border-radius: 10px; }
.tbl-records { width: 100%; min-width: 1150px; border-collapse: collapse; table-layout: fixed; font-size: 13px; background: var(--cl-white); }
.tbl-records th, .tbl-records td { box-sizing: border-box; padding: 13px 12px; text-align: left; border-bottom: 1px solid var(--cl-border-cream); line-height: 1.5; overflow-wrap: anywhere; }
.tbl-records th { background: var(--cl-warm-sand); color: var(--cl-olive); font-size: 12px; font-weight: 600; white-space: nowrap; }
.col-date { width: 104px; }
.col-vehicle { width: 110px; }
.col-card { width: 182px; font-variant-numeric: tabular-nums; }
.col-workshop { width: 80px; }
.tbl-records .col-volume, .tbl-records .col-price { width: 86px; text-align: right; font-variant-numeric: tabular-nums; }
.tbl-records .col-amount { width: 102px; text-align: right; font-variant-numeric: tabular-nums; }
.bill-date, .bill-time { display: block; white-space: nowrap; }
.bill-time { color: var(--cl-olive); font-size: 12px; margin-top: 3px; }
.bill-vehicle { font-weight: 600; }
.bill-oil { display: block; margin-top: 4px; color: var(--cl-olive); font-size: 12px; }
.col-actions { width: 100px; }
.bill-detail-btn { min-height: 34px; padding: 5px 10px; font-size: 12px; }
.bill-detail { min-width: 0; }
.detail-summary { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding-bottom: 16px; }
.detail-summary > div { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.detail-summary strong { font-size: 18px; overflow-wrap: anywhere; }
.detail-summary span { color: var(--cl-olive); font-size: 12px; }
.detail-summary__amount { text-align: right; }
.detail-summary__amount strong { color: var(--cl-brand); }
.detail-section { padding: 16px 0; border-top: 1px solid var(--cl-border-cream); }
.detail-section h3 { margin: 0 0 12px; font-size: 14px; }
.detail-section h3 span { color: var(--cl-olive); font-size: 12px; font-weight: 400; }
.detail-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 20px; margin: 0; }
.detail-grid > div { min-width: 0; }
.detail-grid dt { margin-bottom: 4px; color: var(--cl-olive); font-size: 12px; }
.detail-grid dd { margin: 0; font-size: 13px; line-height: 1.6; overflow-wrap: anywhere; white-space: pre-wrap; }
.detail-product + .detail-product { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--cl-border-cream); }
.detail-notice { color: var(--cl-olive); font-size: 13px; line-height: 1.6; }
.detail-notice--error { color: var(--cl-error); }
.bill-amount { font-weight: 650; color: var(--cl-brand); }
.mobile-bills { display: grid; gap: 14px; min-width: 0; }
.mobile-bills-empty { margin: 0; padding: 32px 16px; }
.mobile-bill { min-width: 0; padding: 18px 16px 10px; border: 1px solid var(--cl-border-cream); border-radius: 12px; background: var(--cl-white); }
.mobile-bill-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.mobile-bill-identity { min-width: 0; }
.mobile-bill-identity h3 { margin: 0 0 6px; color: var(--cl-charcoal); font-size: 17px; font-weight: 650; line-height: 1.4; overflow-wrap: anywhere; }
.mobile-bill-identity > span { display: block; color: var(--cl-olive); font-size: 12px; line-height: 1.5; }
.mobile-bill-amount { flex-shrink: 0; color: var(--cl-brand); font-size: 20px; font-weight: 650; line-height: 1.4; font-variant-numeric: tabular-nums; white-space: nowrap; }
.mobile-bill-amount > span { font-size: 13px; font-weight: 500; }
.mobile-bill-facts { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px 12px; margin: 14px 0; padding-bottom: 14px; border-bottom: 1px solid var(--cl-border-cream); color: var(--cl-olive); font-size: 12px; line-height: 1.6; }
.mobile-bill-facts > span { min-width: 0; overflow-wrap: anywhere; }
.fact-separator { margin: 0 7px; }
.mobile-bill-meta { display: grid; gap: 10px; margin: 0; font-size: 13px; line-height: 1.65; }
.mobile-bill-meta > div { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 10px; }
.mobile-bill-meta dt { color: var(--cl-olive); }
.mobile-bill-meta dd { margin: 0; color: var(--cl-charcoal); overflow-wrap: anywhere; }
.mobile-bill-card { font-variant-numeric: tabular-nums; }
.mobile-bill-footer { display: flex; justify-content: flex-end; margin-top: 10px; }
.mobile-bill-footer .ghost { display: inline-flex; align-items: center; gap: 12px; min-height: 44px; padding: 0 8px; border: 0; background: transparent; color: var(--cl-brand); font-size: 13px; }
.list-toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px; margin: 0 0 8px; }
.list-caption { color: var(--cl-olive); font-size: 12px; }
.sort-actions { display: flex; align-items: center; gap: 6px; }
.sort-label { color: var(--cl-olive); font-size: 12px; margin-right: 4px; }
.sort-actions button { display: inline-flex; align-items: center; gap: 4px; min-height: 32px; padding: 0 8px; border: 1px solid var(--cl-border-cream); border-radius: 6px; background: var(--cl-white); color: var(--cl-charcoal); font-size: 12px; cursor: pointer; }
.sort-priority { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border-radius: 50%; background: var(--cl-brand); color: var(--cl-white); font-size: 10px; }
.sort-actions button.active { border-color: var(--cl-brand); color: var(--cl-brand); background: var(--cl-warm-sand); }
.scroll-loader { padding-top: 16px; color: var(--cl-olive); text-align: center; font-size: 12px; }
.tbl-records tbody tr:last-child td { border-bottom: 0; }
.tbl-records tbody tr:hover td { background: var(--cl-ivory); }
.tbl-records td.hint { padding: 40px 12px; text-align: center; }
.th-sort-btn { border: 0; background: transparent; color: inherit; font: inherit; padding: 0; cursor: pointer; min-height: 24px; }
.hint { color: var(--cl-olive); text-align: center; font-size: 13px; }
.rec-pager { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 16px; }
.rec-pager > .pager-meta:first-child { margin-right: auto; }
.pager-meta { color: var(--cl-olive); font-size: 12px; }
.pager-size { width: 64px; height: 34px; }
.pager-btn { min-height: 34px; font-size: 12px; }
@media (max-width: 1000px) {
  .rec-filters { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  .rec-panel { padding: 14px 12px; border-radius: 12px; }
  .hd { gap: 6px; margin-bottom: 10px; }
  .hd h2 { font-size: 14px; }
  .record-count { font-size: 12px; }
  .record-count span { margin-left: 2px; font-size: 10px; }
  .rec-toolbar { margin-bottom: 8px; }
  .rec-filters { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .filter-group { gap: 3px; max-width: 100%; }
  .filter-group--date { overflow: hidden; }
  .filter-group--date .filter-date { display: block; width: 100%; max-width: 100%; min-width: 0; -webkit-appearance: none; appearance: none; padding: 0 7px; overflow: hidden; }
  .filter-date::-webkit-date-and-time-value { min-width: 0; text-align: left; }
  .filter-date::-webkit-datetime-edit { min-width: 0; padding: 0; }
  .filter-group:first-child { grid-column: 1 / -1; }
  .filter-control, .filter-group :deep(.searchable-select__trigger) { height: 44px; min-height: 44px; font-size: 16px; }
  .filter-group :deep(.searchable-select__search) { font-size: 16px; }
  .rec-query { min-height: 40px; padding: 0 8px; font-size: 12px; }
  .detail-summary { gap: 10px; }
  .detail-summary strong { font-size: 16px; }
  .detail-grid { gap: 12px; }
  .list-toolbar { gap: 8px; margin: 12px 0 16px; }
  .list-caption { width: 100%; }
  .sort-actions { flex-wrap: wrap; gap: 8px; }
  .sort-actions button { min-height: 40px; padding: 0 10px; }
  .scroll-loader .ghost { min-height: 44px; }
}
@media (max-width: 380px) {
  .hd { flex-wrap: wrap; }
  .rec-actions { margin-left: auto; }
  .list-caption { width: 100%; }
  .detail-grid { grid-template-columns: minmax(0, 1fr); }
  .mobile-bill { padding: 16px 12px 8px; }
  .mobile-bill-identity h3 { font-size: 16px; }
  .mobile-bill-amount { font-size: 18px; }
}
</style>
