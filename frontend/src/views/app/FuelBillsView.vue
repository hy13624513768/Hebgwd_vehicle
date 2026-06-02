<template>
  <div class="stack fuel-bills-view">
    <section class="panel rec-panel">
      <div class="hd">
        <h2>加油流水</h2>
      </div>
      <div v-if="syncStatus" class="sync-status">{{ syncStatus }}</div>
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
          <button type="button" class="primary rec-query" :disabled="syncingRecords" @click="searchRecords">
            {{ syncingRecords ? '同步中…' : '查询最新油卡余额数据' }}
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
        <tbody v-if="!recordsSearched && !loadingRecords">
          <tr>
            <td colspan="9" class="hint">正在加载加油流水…</td>
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
        <p v-if="!recordsSearched && !loadingRecords" class="hint rec-mobile__hint">正在加载加油流水…</p>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import * as fuelApi from '@/api/fuel'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import type { FuelRecord } from '@/api/fuel'

const records = ref<FuelRecord[]>([])
const recordWorkshops = ref<string[]>([])
const recordCards = ref<string[]>([])
const msg = ref('')
const syncStatus = ref('')
const syncingRecords = ref(false)
const loadingRecords = ref(false)
const exportingRecords = ref(false)
const recordsSearched = ref(false)
const recordsTotal = ref(0)

const recFilter = reactive({
  card_asn_id: 0,
  workshop_id: 0,
  date_from: '',
  date_to: '',
  page: 1,
  page_size: 20,
})
const recSort = reactive({
  by: 'card_asn' as 'occur_time' | 'workshop' | 'amount' | 'volumn' | 'car_no' | 'card_asn',
  dir: 'asc' as 'asc' | 'desc',
})

const totalRecordPages = computed(() =>
  Math.max(1, Math.ceil(recordsTotal.value / recFilter.page_size) || 1),
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

function selectedRecordWorkshopName(): string {
  if (!recFilter.workshop_id) return ''
  return recordWorkshopOptions.value.find((x) => x.id === recFilter.workshop_id)?.label ?? ''
}

function selectedRecordCardNo(): string {
  if (!recFilter.card_asn_id) return ''
  return recordCardOptions.value.find((x) => x.id === recFilter.card_asn_id)?.label ?? ''
}

function monthStartIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function ensureRecordDateRange() {
  if (!recFilter.date_from) recFilter.date_from = monthStartIso()
  if (!recFilter.date_to) recFilter.date_to = todayIso()
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
  loadingRecords.value = true
  try {
    const [rws, cards] = await Promise.all([
      fuelApi.listFuelRecordWorkshops(),
      fuelApi.listFuelRecordCards(),
    ])
    recordWorkshops.value = rws
    recordCards.value = cards
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
  if (!loadingRecords.value) loadingRecords.value = true
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

async function searchRecords() {
  ensureRecordDateRange()
  recFilter.page = 1
  syncingRecords.value = true
  loadingRecords.value = true
  msg.value = ''
  syncStatus.value = '准备连接中国石油油卡平台…'
  try {
    await fuelApi.syncFuelFromPlatform(
      {
        date_from: recFilter.date_from,
        date_to: recFilter.date_to,
      },
      (message) => {
        syncStatus.value = message
      },
    )
  } catch (e) {
    msg.value = e instanceof Error ? e.message : '同步中国石油油卡数据失败'
    syncStatus.value = ''
    return
  } finally {
    syncingRecords.value = false
  }

  syncStatus.value = '同步完成，正在刷新页面…'
  loadingRecords.value = true
  try {
    const [rws, cards] = await Promise.all([
      fuelApi.listFuelRecordWorkshops(),
      fuelApi.listFuelRecordCards(),
    ])
    recordWorkshops.value = rws
    recordCards.value = cards
    await fetchRecordsPage()
    recordsSearched.value = true
    syncStatus.value = ''
  } catch {
    msg.value = '数据已同步，但刷新加油流水失败，请稍后重试'
    syncStatus.value = ''
  } finally {
    loadingRecords.value = false
  }
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

onMounted(() => {
  ensureRecordDateRange()
  void reload()
})
</script>

<style scoped>
.stack.fuel-bills-view {
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

.sync-status {
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(201, 100, 66, 0.35);
  background: rgba(201, 100, 66, 0.1);
  color: #8a4b22;
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

  .rec-filters .filter-field--date {
    display: block;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    border-radius: 12px;
    overflow: hidden;
    box-sizing: border-box;
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
