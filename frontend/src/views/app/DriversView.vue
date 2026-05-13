<template>
  <div class="drivers-view">
    <section v-if="stats" class="driver-overview" aria-label="驾驶员统计">
      <div class="driver-overview__kpi">
        <span class="driver-overview__kpi-label">在册驾驶员</span>
        <strong class="driver-overview__kpi-num">{{ stats.total }}</strong>
        <span class="driver-overview__kpi-hint">（筛选结果共 {{ totalCount }} 条）</span>
      </div>
      <div class="driver-overview__row">
        <span class="driver-overview__row-label">按状态</span>
        <div class="driver-overview__chips">
          <button
            v-for="[label, cnt] in statusChips"
            :key="'st-' + label"
            type="button"
            class="stat-chip"
            :class="{ 'stat-chip--active': statusChipActive(label) }"
            @click="toggleStatusChip(label)"
          >
            {{ label }} <em>{{ cnt }}</em>
          </button>
        </div>
      </div>
      <div class="driver-overview__row">
        <span class="driver-overview__row-label">准驾类型</span>
        <div class="driver-overview__chips">
          <button
            v-for="[label, cnt] in licenseChips"
            :key="'lt-' + label"
            type="button"
            class="stat-chip stat-chip--muted"
            :class="{ 'stat-chip--active': licenseChipActive(label) }"
            @click="toggleLicenseChip(label)"
          >
            {{ label }} <em>{{ cnt }}</em>
          </button>
        </div>
      </div>

      <div class="driver-charts" aria-label="驾驶员分布图表">
        <div class="driver-chart driver-chart--donut">
          <h3 class="driver-chart__title">状态分布</h3>
          <div class="driver-chart__donut-body">
            <div
              class="driver-chart__donut"
              role="img"
              :aria-label="statusDonutAriaLabel"
              :style="{ background: statusDonutBackground }"
            />
            <ul class="driver-chart__legend" aria-hidden="true">
              <li v-for="([label, cnt], idx) in statusChips" :key="'lg-' + label" class="driver-chart__legend-item">
                <i class="driver-chart__swatch" :style="barFillStyle(idx)" />
                <span class="driver-chart__legend-text">{{ label }}</span>
                <span class="driver-chart__legend-num">{{ cnt }}</span>
              </li>
            </ul>
          </div>
        </div>
        <div class="driver-chart driver-chart--bars">
          <h3 class="driver-chart__title">准驾类型分布</h3>
          <p v-if="!licenseChips.length" class="driver-chart__empty">暂无准驾类型数据</p>
          <ul v-else class="driver-chart__bar-list" role="list">
            <li v-for="([label, cnt], idx) in licenseChips" :key="'bar-' + label" class="driver-chart__bar-row" role="listitem">
              <span class="driver-chart__bar-label" :title="label">{{ label }}</span>
              <div class="driver-chart__bar-track" :title="`${label}：${cnt} 人`">
                <div class="driver-chart__bar-fill" :style="licenseBarFillStyle(cnt, idx)" />
              </div>
              <span class="driver-chart__bar-val">{{ cnt }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <div class="toolbar">
      <div class="toolbar__search-wrap">
        <span class="toolbar__search-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
            <path d="M20 20l-4.2-4.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </span>
        <input
          v-model.trim="q"
          class="toolbar__search"
          type="search"
          enterkeyhint="search"
          autocomplete="off"
          placeholder="姓名 / 电话 / 身份证号"
          aria-label="搜索驾驶员：姓名、电话或身份证号"
          @keydown.enter.prevent="loadList"
        />
      </div>
      <div class="toolbar__filters">
        <div class="toolbar__field">
          <span class="toolbar-label">状态</span>
          <SearchableSelect
            v-model="filterStatusId"
            class="toolbar-select"
            :options="statusOptions"
            allow-empty
            empty-label="全部"
            search-placeholder="输入状态关键字…"
          />
        </div>
        <div class="toolbar__field">
          <span class="toolbar-label">准驾</span>
          <SearchableSelect
            v-model="filterLicenseId"
            class="toolbar-select"
            :options="licenseTypeOptions"
            allow-empty
            empty-label="全部"
            search-placeholder="输入准驾关键字…"
          />
        </div>
      </div>
      <div class="toolbar__actions">
        <button type="button" class="primary toolbar__btn-query" :disabled="loading" @click="loadList">查询</button>
        <button
          v-if="canManageFleet"
          type="button"
          class="primary toolbar__btn-new"
          :disabled="loading"
          @click="openCreate"
        >
          新增驾驶员
        </button>
        <button type="button" class="ghost toolbar__btn-refresh" :disabled="loading" @click="loadAll">刷新</button>
      </div>
    </div>

    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <div v-else class="list-stack">
    <div class="list-wrap">
      <table class="tbl tbl--desktop">
        <thead>
          <tr>
            <th class="col-narrow">序号</th>
            <th>姓名</th>
            <th>电话</th>
            <th>准驾</th>
            <th>车辆类型标签</th>
            <th>状态</th>
            <th>身份证号</th>
            <th>健康体检报告</th>
            <th>外包人员入职手续</th>
            <th>首次入职</th>
            <th v-if="canManageFleet" class="w">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0">
            <td :colspan="canManageFleet ? 11 : 10" class="empty-hint">暂无数据，可调整筛选后点击查询。</td>
          </tr>
          <tr v-for="(d, idx) in rows" :key="d.id">
            <td class="muted">{{ displayRowSeq(idx) }}</td>
            <td class="strong">{{ d.name }}</td>
            <td>{{ d.phone }}</td>
            <td>{{ d.license_type || '—' }}</td>
            <td class="t" :title="d.vehicle_type_label || ''">{{ d.vehicle_type_label || '—' }}</td>
            <td>{{ d.status || '—' }}</td>
            <td class="mono">{{ d.id_card || '—' }}</td>
            <td class="col-long" :title="d.health_check_report || ''">{{ trunc(d.health_check_report, 24) }}</td>
            <td class="col-long" :title="d.outsourcing_onboarding || ''">{{ trunc(d.outsourcing_onboarding, 24) }}</td>
            <td>{{ d.first_hire_date ? fmtDate(d.first_hire_date) : '—' }}</td>
            <td v-if="canManageFleet" class="w">
              <button type="button" class="link" @click="openEdit(d)">编辑</button>
              <button type="button" class="link danger" @click="onDelete(d)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="driver-cards-mobile" aria-label="驾驶员列表">
        <p v-if="rows.length === 0" class="empty-hint driver-cards-mobile__empty">暂无数据，可调整筛选后点击查询。</p>
        <ul v-else class="driver-cards">
          <li v-for="(d, idx) in rows" :key="`m-${d.id}`" class="driver-card">
            <div class="driver-card__top">
              <span class="driver-card__name">{{ d.name }}</span>
              <span class="driver-card__status">{{ d.status || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">序号</span>
              <span class="driver-card__v">{{ displayRowSeq(idx) }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">电话</span>
              <span class="driver-card__v">{{ d.phone }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">准驾</span>
              <span class="driver-card__v">{{ d.license_type || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">车辆类型</span>
              <span class="driver-card__v">{{ d.vehicle_type_label || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">身份证</span>
              <span class="driver-card__v driver-card__mono">{{ d.id_card || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">健康体检</span>
              <span class="driver-card__v">{{ d.health_check_report || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">外包手续</span>
              <span class="driver-card__v">{{ d.outsourcing_onboarding || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">首次入职</span>
              <span class="driver-card__v">{{ d.first_hire_date ? fmtDate(d.first_hire_date) : '—' }}</span>
            </div>
            <div v-if="canManageFleet" class="driver-card__actions">
              <button type="button" class="driver-card__btn" @click="openEdit(d)">编辑</button>
              <button type="button" class="driver-card__btn driver-card__btn--danger" @click="onDelete(d)">删除</button>
            </div>
          </li>
        </ul>
      </div>
    </div>

      <div v-if="listLoaded" class="driver-pager">
        <span class="driver-pager__meta driver-pager__summary">本页 {{ rows.length }} 条 · 共 {{ totalCount }} 条</span>
        <div class="driver-pager__size-row">
          <label class="driver-pager__label">每页</label>
          <select
            v-model.number="listPager.page_size"
            class="driver-pager__size"
            @change="onDriverPageSizeChange"
          >
            <option :value="10">10</option>
            <option :value="15">15</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
            <option :value="100">100</option>
          </select>
          <span class="driver-pager__meta">条</span>
        </div>
        <span class="driver-pager__meta driver-pager__page">第 {{ listPager.page }} / {{ totalDriverPages }} 页</span>
        <div class="driver-pager__nav">
          <button type="button" class="ghost driver-pager__btn" :disabled="listPager.page <= 1" @click="prevDriverPage">
            上一页
          </button>
          <button
            type="button"
            class="ghost driver-pager__btn"
            :disabled="listPager.page >= totalDriverPages"
            @click="nextDriverPage"
          >
            下一页
          </button>
        </div>
      </div>
    </div>

    <AppModal :open="modalOpen" :title="modalTitle" @close="modalOpen = false">
      <div class="form form--drivers">
        <label>姓名</label>
        <input v-model.trim="form.name" />

        <label>电话</label>
        <input v-model.trim="form.phone" />

        <label>准驾</label>
        <input v-model.trim="form.license_type" placeholder="如 A1、C1" />

        <label>车辆类型标签</label>
        <input v-model.trim="form.vehicle_type_label" placeholder="与车辆登记「车辆类型」一致，如 小型轿车" />

        <label>状态</label>
        <input v-model.trim="form.status" placeholder="如 在岗" />

        <label>身份证号</label>
        <input v-model.trim="form.id_card" />

        <label>健康体检报告</label>
        <textarea v-model.trim="form.health_check_report" rows="2" />

        <label>外包人员入职手续</label>
        <textarea v-model.trim="form.outsourcing_onboarding" rows="2" />

        <label>首次入职时间</label>
        <input v-model="form.first_hire_date" type="date" />
      </div>

      <template #footer>
        <button type="button" class="ghost" @click="modalOpen = false">取消</button>
        <button type="button" class="primary" :disabled="saving" @click="save">保存</button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, reactive, ref } from 'vue'

import * as api from '@/api/drivers'
import type { DriverStats } from '@/api/drivers'
import type { Driver } from '@/api/types'
import AppModal from '@/components/AppModal.vue'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import { usePermissions } from '@/composables/usePermissions'
import { fmtDate } from '@/utils/format'

const { canManageFleet } = usePermissions()

const loading = ref(true)
const saving = ref(false)
const rows = ref<Driver[]>([])
const q = ref('')
const msg = ref('')
const stats = ref<DriverStats | null>(null)
const totalCount = ref(0)
const listLoaded = ref(false)
const listPager = reactive({
  page: 1,
  page_size: 15,
})
const driverStatuses = ref<string[]>([])
const driverLicenseTypes = ref<string[]>([])
const filterStatusId = ref(0)
const filterLicenseId = ref(0)

const modalOpen = ref(false)
const modalTitle = ref('新增驾驶员')
const editingId = ref<number | null>(null)

const form = reactive({
  name: '',
  phone: '',
  license_type: '',
  vehicle_type_label: '',
  status: '',
  id_card: '',
  health_check_report: '',
  outsourcing_onboarding: '',
  first_hire_date: '',
})

const statusOptions = computed<SearchableOption[]>(() => {
  const out: SearchableOption[] = []
  let nid = 1
  if (stats.value?.by_status['(未填)']) {
    out.push({ id: nid, label: '(未填)', keywords: '(未填) 未填 空' })
    nid += 1
  }
  for (const s of driverStatuses.value) {
    out.push({ id: nid, label: s, keywords: s })
    nid += 1
  }
  return out
})

const licenseTypeOptions = computed<SearchableOption[]>(() => {
  const out: SearchableOption[] = []
  let nid = 1
  if (stats.value?.by_license_type['(未填)']) {
    out.push({ id: nid, label: '(未填)', keywords: '(未填) 未填' })
    nid += 1
  }
  for (const s of driverLicenseTypes.value) {
    out.push({ id: nid, label: s, keywords: s })
    nid += 1
  }
  return out
})

const statusChips = computed(() => {
  if (!stats.value) return [] as [string, number][]
  return Object.entries(stats.value.by_status).sort((a, b) => b[1] - a[1])
})

const licenseChips = computed(() => {
  if (!stats.value) return [] as [string, number][]
  return Object.entries(stats.value.by_license_type).sort((a, b) => b[1] - a[1])
})

const licenseBarMax = computed(() => {
  const chips = licenseChips.value
  if (!chips.length) return 1
  return Math.max(...chips.map((x) => x[1]), 1)
})

const totalDriverPages = computed(() =>
  Math.max(1, Math.ceil(totalCount.value / listPager.page_size) || 1),
)

const statusDonutBackground = computed(() => {
  const t = stats.value?.total ?? 0
  if (!t || !statusChips.value.length) return 'conic-gradient(var(--cl-border-cream) 0% 100%)'
  return donutGradientFromEntries(statusChips.value, t)
})

const statusDonutAriaLabel = computed(() => {
  if (!stats.value) return '状态分布'
  return `状态分布：${statusChips.value.map(([l, c]) => `${l} ${c}人`).join('，')}`
})

/**
 * 与 BAR_FILL_GRADIENTS 逐项对应：浅色（条起点）→ 深色（条终点）。
 * 用于 conic-gradient 每段沿圆心角插值，视觉与横向条「左浅右深」同色系。
 */
const BAR_DONUT_WEDGE_STOPS = [
  ['rgba(201, 100, 66, 0.32)', '#c96442'],
  ['rgba(215, 119, 87, 0.35)', '#d97757'],
  ['rgba(181, 138, 90, 0.4)', '#9a7340'],
  ['rgba(201, 161, 91, 0.42)', '#b8883a'],
  ['rgba(94, 93, 89, 0.28)', '#6b5d4b'],
  ['rgba(167, 107, 82, 0.38)', '#a76b52'],
  ['rgba(77, 76, 72, 0.32)', '#5c5347'],
  ['rgba(201, 100, 66, 0.18)', '#c47a5f'],
] as const

function donutGradientFromEntries(entries: [string, number][], total: number): string {
  let acc = 0
  const stops: string[] = []
  entries.forEach(([_, cnt], i) => {
    const pct = (cnt / total) * 100
    if (pct <= 0) return
    const [c0, c1] = BAR_DONUT_WEDGE_STOPS[i % BAR_DONUT_WEDGE_STOPS.length]
    const s = acc
    const e = acc + pct
    stops.push(`${c0} ${s.toFixed(2)}%`, `${c1} ${e.toFixed(2)}%`)
    acc = e
  })
  return stops.length ? `conic-gradient(${stops.join(', ')})` : 'conic-gradient(var(--cl-border-cream) 0% 100%)'
}

/** 暖色主题条形渐变，与车辆管理页分布图一致（VehiclesView） */
const BAR_FILL_GRADIENTS = [
  'linear-gradient(90deg, rgba(201, 100, 66, 0.32) 0%, #c96442 94%)',
  'linear-gradient(90deg, rgba(215, 119, 87, 0.35) 0%, #d97757 94%)',
  'linear-gradient(90deg, rgba(181, 138, 90, 0.4) 0%, #9a7340 92%)',
  'linear-gradient(90deg, rgba(201, 161, 91, 0.42) 0%, #b8883a 92%)',
  'linear-gradient(90deg, rgba(94, 93, 89, 0.28) 0%, #6b5d4b 94%)',
  'linear-gradient(90deg, rgba(167, 107, 82, 0.38) 0%, #a76b52 92%)',
  'linear-gradient(90deg, rgba(77, 76, 72, 0.32) 0%, #5c5347 92%)',
  'linear-gradient(90deg, rgba(201, 100, 66, 0.18) 0%, #c47a5f 90%)',
] as const

function barFillStyle(index: number): Record<string, string> {
  return {
    background: BAR_FILL_GRADIENTS[index % BAR_FILL_GRADIENTS.length],
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.32)',
  }
}

/** 准驾条形宽度 + 渐变（避免模板中调用独立函数名在 HMR 下偶发非函数错误） */
function licenseBarFillStyle(cnt: number, idx: number): Record<string, string> {
  const max = licenseBarMax.value
  const pct = max > 0 ? (cnt / max) * 100 : 0
  return { width: `${pct}%`, ...barFillStyle(idx) }
}

function trunc(s: string | null, n: number) {
  if (!s) return '—'
  return s.length <= n ? s : `${s.slice(0, n)}…`
}

/** 当前页列表展示序号（跨页连续编号），非数据库 sort_no */
function displayRowSeq(index: number) {
  return (listPager.page - 1) * listPager.page_size + index + 1
}

function selectedStatusQuery(): string | undefined {
  if (!filterStatusId.value) return undefined
  return statusOptions.value.find((x) => x.id === filterStatusId.value)?.label
}

function selectedLicenseQuery(): string | undefined {
  if (!filterLicenseId.value) return undefined
  return licenseTypeOptions.value.find((x) => x.id === filterLicenseId.value)?.label
}

function statusChipActive(label: string) {
  const qv = selectedStatusQuery()
  return qv === label
}

function licenseChipActive(label: string) {
  const qv = selectedLicenseQuery()
  return qv === label
}

function toggleStatusChip(label: string) {
  const opt = statusOptions.value.find((x) => x.label === label)
  if (!opt) return
  filterStatusId.value = filterStatusId.value === opt.id ? 0 : opt.id
  void loadList()
}

function toggleLicenseChip(label: string) {
  const opt = licenseTypeOptions.value.find((x) => x.label === label)
  if (!opt) return
  filterLicenseId.value = filterLicenseId.value === opt.id ? 0 : opt.id
  void loadList()
}

function buildDriverListParams() {
  return {
    q: q.value || undefined,
    skip: (listPager.page - 1) * listPager.page_size,
    limit: listPager.page_size,
    status: selectedStatusQuery(),
    license_type: selectedLicenseQuery(),
  }
}

async function fetchListData() {
  const res = await api.listDrivers(buildDriverListParams())
  const maxPage = Math.max(1, Math.ceil(res.total / listPager.page_size) || 1)
  if (res.total > 0 && listPager.page > maxPage) {
    listPager.page = maxPage
    const res2 = await api.listDrivers(buildDriverListParams())
    rows.value = res2.items
    totalCount.value = res2.total
  } else {
    rows.value = res.items
    totalCount.value = res.total
  }
  listLoaded.value = true
}

async function loadList() {
  listPager.page = 1
  loading.value = true
  msg.value = ''
  try {
    await fetchListData()
  } catch {
    msg.value = '加载驾驶员列表失败'
  } finally {
    loading.value = false
  }
}

async function loadListKeepPage() {
  loading.value = true
  msg.value = ''
  try {
    await fetchListData()
  } catch {
    msg.value = '加载驾驶员列表失败'
  } finally {
    loading.value = false
  }
}

function onDriverPageSizeChange() {
  listPager.page = 1
  void loadListKeepPage()
}

function prevDriverPage() {
  if (listPager.page <= 1) return
  listPager.page -= 1
  void loadListKeepPage()
}

function nextDriverPage() {
  if (listPager.page >= totalDriverPages.value) return
  listPager.page += 1
  void loadListKeepPage()
}

async function loadAll() {
  loading.value = true
  msg.value = ''
  listPager.page = 1
  try {
    const f = await api.getDriverFilters()
    driverStatuses.value = f.statuses
    driverLicenseTypes.value = f.license_types
    stats.value = await api.getDriverStats()
    await fetchListData()
  } catch {
    msg.value = '加载统计或列表失败'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.name = ''
  form.phone = ''
  form.license_type = ''
  form.vehicle_type_label = ''
  form.status = ''
  form.id_card = ''
  form.health_check_report = ''
  form.outsourcing_onboarding = ''
  form.first_hire_date = ''
}

function openCreate() {
  editingId.value = null
  modalTitle.value = '新增驾驶员'
  resetForm()
  modalOpen.value = true
}

function openEdit(d: Driver) {
  editingId.value = d.id
  modalTitle.value = '编辑驾驶员'
  form.name = d.name
  form.phone = d.phone
  form.license_type = d.license_type
  form.vehicle_type_label = d.vehicle_type_label || ''
  form.status = d.status
  form.id_card = d.id_card || ''
  form.health_check_report = d.health_check_report || ''
  form.outsourcing_onboarding = d.outsourcing_onboarding || ''
  form.first_hire_date = d.first_hire_date ? d.first_hire_date.slice(0, 10) : ''
  modalOpen.value = true
}

async function save() {
  saving.value = true
  msg.value = ''
  try {
    const payload: Record<string, unknown> = {
      name: form.name,
      phone: form.phone,
      license_type: form.license_type,
      vehicle_type_label: form.vehicle_type_label,
      status: form.status,
      id_card: form.id_card || null,
      health_check_report: form.health_check_report || null,
      outsourcing_onboarding: form.outsourcing_onboarding || null,
      first_hire_date: form.first_hire_date ? form.first_hire_date : null,
    }
    if (editingId.value) await api.updateDriver(editingId.value, payload)
    else await api.createDriver(payload)
    modalOpen.value = false
    await loadAll()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '保存失败') : '保存失败'
  } finally {
    saving.value = false
  }
}

async function onDelete(d: Driver) {
  if (!confirm(`确定删除驾驶员 ${d.name} ？`)) return
  msg.value = ''
  try {
    await api.deleteDriver(d.id)
    await loadAll()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '删除失败') : '删除失败'
  }
}

onMounted(loadAll)
</script>

<style scoped>
.drivers-view {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.driver-overview {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-warm-sand);
  box-sizing: border-box;
}

.driver-overview__kpi {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 12px;
  margin-bottom: 10px;
}

.driver-overview__kpi-label {
  font-size: 13px;
  color: var(--cl-olive);
  font-weight: 700;
}

.driver-overview__kpi-num {
  font-size: 1.35rem;
  font-weight: 900;
  color: var(--cl-near-black);
}

.driver-overview__kpi-hint {
  font-size: 12px;
  color: var(--cl-olive);
}

.driver-overview__row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px 10px;
  align-items: start;
  margin-top: 8px;
}

.driver-overview__row-label {
  font-size: 12px;
  font-weight: 800;
  color: var(--cl-charcoal);
  padding-top: 4px;
}

.driver-overview__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stat-chip {
  cursor: pointer;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  color: var(--cl-near-black);
  font-family: inherit;
  -webkit-tap-highlight-color: transparent;
}

.stat-chip em {
  font-style: normal;
  font-weight: 800;
  color: var(--cl-coral);
  margin-left: 4px;
}

.stat-chip--muted {
  background: var(--cl-ivory);
}

.stat-chip--active {
  border-color: var(--cl-coral);
  box-shadow: 0 0 0 2px rgba(200, 90, 60, 0.2);
}

.driver-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--cl-border-cream);
  min-width: 0;
}

.driver-chart {
  min-width: 0;
  padding: 12px;
  border-radius: 12px;
  background: var(--cl-ivory);
  border: 1px solid var(--cl-border-cream);
  box-sizing: border-box;
}

/* 与 VehiclesView `.chart` 白底一致，条形区域视觉统一 */
.driver-chart--bars {
  background: var(--cl-white);
  padding: 10px;
}

.driver-chart__title {
  margin: 0 0 12px;
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--cl-charcoal);
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
}

.driver-chart__donut-body {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px 20px;
}

.driver-chart__donut {
  flex-shrink: 0;
  width: min(168px, 42vw);
  height: min(168px, 42vw);
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.06);
  -webkit-mask: radial-gradient(circle, transparent 52%, #000 53%);
  mask: radial-gradient(circle, transparent 52%, #000 53%);
}

.driver-chart__legend {
  list-style: none;
  margin: 0;
  padding: 0;
  flex: 1;
  min-width: 140px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.driver-chart__legend-item {
  display: grid;
  grid-template-columns: 12px 1fr auto;
  gap: 8px;
  align-items: center;
  color: var(--cl-near-black);
}

.driver-chart__swatch {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
}

.driver-chart__legend-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.driver-chart__legend-num {
  font-weight: 800;
  color: var(--cl-coral);
}

.driver-chart__empty {
  margin: 0;
  font-size: 13px;
  color: var(--cl-olive);
}

.driver-chart__bar-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.driver-chart__bar-row {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr) 88px;
  gap: 8px;
  align-items: center;
}

.driver-chart__bar-label {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.driver-chart__bar-track {
  height: 9px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ebe7dc, var(--cl-warm-sand));
  border: 1px solid rgba(232, 230, 220, 0.85);
  box-shadow: inset 0 1px 2px rgba(20, 20, 19, 0.06);
  overflow: hidden;
}

.driver-chart__bar-fill {
  display: block;
  height: 100%;
  min-width: 6px;
  border-radius: 999px;
  transition:
    filter 0.16s ease,
    box-shadow 0.16s ease;
}

.driver-chart__bar-row:hover .driver-chart__bar-fill {
  filter: brightness(1.07) saturate(1.05);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    0 0 0 1px rgba(201, 100, 66, 0.12);
}

.driver-chart__bar-val {
  font-size: 12px;
  text-align: right;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(200px, 1fr) minmax(128px, 200px) minmax(128px, 200px) auto;
  grid-template-rows: auto;
  align-items: end;
  gap: 14px 12px;
  margin-bottom: 12px;
  min-width: 0;
}

/* 四个格子：关键字 | 状态 | 准驾 | 按钮组（避免 flex+子组件 flex:1 把整块撑到数百像素高） */
.toolbar__filters {
  display: contents;
}

.toolbar__search-wrap {
  position: relative;
  min-width: 0;
  width: 100%;
  align-self: end;
}

.toolbar__search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  color: var(--cl-olive);
  opacity: 0.72;
}

.toolbar__search {
  display: block;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  margin: 0;
  padding: 10px 12px 10px 40px;
  min-height: 42px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  color: var(--cl-near-black);
  font-family: inherit;
  font-size: 13px;
  line-height: 1.35;
  box-shadow: 0 1px 2px rgba(20, 20, 19, 0.05);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
  -webkit-appearance: none;
  appearance: none;
}

.toolbar__search::placeholder {
  color: var(--cl-olive);
  opacity: 0.75;
}

.toolbar__search:hover {
  border-color: var(--cl-border-warm);
}

.toolbar__search:focus {
  outline: none;
  border-color: var(--cl-border-warm);
  box-shadow:
    0 1px 2px rgba(20, 20, 19, 0.06),
    0 0 0 3px rgba(158, 107, 74, 0.18);
}

.toolbar__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  width: 100%;
  max-width: 200px;
}

.toolbar :deep(.searchable-select) {
  flex: 0 1 auto;
  min-width: 0;
  width: 100%;
  max-width: 200px;
  min-height: 0;
}

.toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-self: end;
  margin-left: 0;
}

.toolbar-label {
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 700;
  white-space: nowrap;
}

.toolbar-select {
  min-width: 0;
  max-width: 200px;
}

/* 中等宽度：关键字单行占满，状态+准驾一行，按钮单独一行，避免四列挤成一团 */
@media (max-width: 900px) and (min-width: 769px) {
  .toolbar {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
  }

  .toolbar__search-wrap {
    grid-column: 1 / -1;
  }

  .toolbar > .toolbar__field:first-of-type {
    grid-column: 1;
    grid-row: 2;
  }

  .toolbar > .toolbar__field:last-of-type {
    grid-column: 2;
    grid-row: 2;
  }

  .toolbar__actions {
    grid-column: 1 / -1;
    grid-row: 3;
    justify-self: stretch;
    justify-content: flex-start;
  }
}

.q {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  color: var(--cl-near-black);
}

.primary {
  cursor: pointer;
  border: 0;
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--cl-brand);
  color: var(--cl-ivory);
  font-weight: 800;
}

.ghost {
  cursor: pointer;
  border: 1px solid var(--cl-border-warm);
  background: transparent;
  color: var(--cl-near-black);
  border-radius: 10px;
  padding: 10px 12px;
}

.msg {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.08);
  color: var(--cl-error);
  font-size: 13px;
}

.muted {
  color: var(--cl-olive);
  font-size: 13px;
}

.list-stack {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}

.list-wrap {
  min-width: 0;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.driver-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-warm-sand);
  box-sizing: border-box;
}

.driver-pager__summary {
  flex: 1 1 200px;
  min-width: 0;
}

.driver-pager__size-row {
  display: inline-flex;
  align-items: center;
  gap: 6px 8px;
  flex-wrap: nowrap;
  flex-shrink: 0;
}

.driver-pager__size-row > .driver-pager__meta {
  flex-shrink: 0;
}

.driver-pager__meta {
  font-size: 13px;
  color: var(--cl-olive);
}

.driver-pager__page {
  font-size: 13px;
  color: var(--cl-charcoal);
  font-weight: 700;
}

.driver-pager__nav {
  display: flex;
  gap: 8px;
  margin-left: auto;
  flex-wrap: wrap;
}

.driver-pager__label {
  display: inline-block;
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  margin: 0;
  cursor: default;
}

.driver-pager__size {
  width: auto;
  min-width: 5.5rem;
  max-width: 7.5rem;
  flex: 0 0 auto;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  font-size: 13px;
  font-family: inherit;
  color: var(--cl-near-black);
  min-height: 36px;
  box-sizing: border-box;
  line-height: 1.2;
}

.driver-pager__btn {
  min-height: 36px;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  overflow: hidden;
}

.tbl--desktop {
  display: table;
  min-width: 1080px;
}

.col-narrow {
  width: 64px;
  white-space: nowrap;
}

.col-long {
  max-width: 160px;
  word-break: break-word;
  line-height: 1.35;
}

.mono {
  font-family: ui-monospace, 'Cascadia Mono', 'Segoe UI Mono', monospace;
  font-size: 12px;
}

.empty-hint {
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
  padding: 28px 16px !important;
}

.driver-cards-mobile {
  display: none;
}

.driver-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.driver-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  background: var(--cl-ivory);
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.04) 0 4px 16px;
}

.driver-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.driver-card__name {
  font-size: 1.05rem;
  font-weight: 900;
  color: var(--cl-near-black);
  line-height: 1.3;
  word-break: break-word;
}

.driver-card__status {
  flex-shrink: 0;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  font-size: 12px;
  font-weight: 700;
  color: var(--cl-olive);
}

.driver-card__row {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px 12px;
  align-items: start;
  font-size: 13px;
  margin-bottom: 8px;
}

.driver-card__k {
  font-size: 11px;
  font-weight: 700;
  color: var(--cl-olive);
}

.driver-card__v {
  color: var(--cl-near-black);
  word-break: break-word;
  line-height: 1.4;
}

.driver-card__mono {
  font-family: ui-monospace, 'Cascadia Mono', 'Segoe UI Mono', monospace;
  font-size: 12px;
}

.driver-card__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--cl-border-cream);
}

.driver-card__btn {
  cursor: pointer;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-warm);
  background: var(--cl-white);
  color: var(--cl-coral);
  font-family: inherit;
  font-size: 15px;
  font-weight: 700;
  -webkit-tap-highlight-color: transparent;
}

.driver-card__btn--danger {
  color: var(--cl-error);
  border-color: rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.06);
}

.driver-cards-mobile__empty {
  margin: 0;
  padding: 24px 12px !important;
}

th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--cl-border-cream);
  text-align: left;
  vertical-align: top;
}

th {
  color: var(--cl-olive);
  font-weight: 800;
  background: var(--cl-warm-sand);
}

.strong {
  font-weight: 900;
}

.w {
  width: 160px;
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

.form {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 10px 12px;
  align-items: center;
}

.form label {
  color: var(--cl-charcoal);
  font-size: 12px;
}

.form input,
.form select,
.form textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  color: var(--cl-near-black);
}

.form textarea {
  resize: vertical;
}

@media (max-width: 768px) {
  .drivers-view {
    padding-bottom: env(safe-area-inset-bottom, 0);
  }

  .driver-overview {
    padding: 10px 12px;
    margin-bottom: 12px;
    border-radius: 12px;
  }

  .driver-overview__kpi {
    margin-bottom: 12px;
    gap: 6px 10px;
  }

  .driver-overview__kpi-num {
    font-size: 1.5rem;
  }

  .driver-overview__kpi-hint {
    width: 100%;
    flex-basis: 100%;
  }

  .driver-overview__row {
    grid-template-columns: 1fr;
    margin-top: 10px;
    gap: 6px 0;
  }

  .driver-overview__row-label {
    padding-top: 0;
    font-size: 13px;
  }

  .driver-overview__chips {
    gap: 10px;
  }

  .stat-chip {
    min-height: 44px;
    padding: 8px 14px;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    touch-action: manipulation;
  }

  .driver-charts {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-top: 12px;
    padding-top: 12px;
  }

  .driver-chart {
    padding: 14px 12px;
    border-radius: 14px;
  }

  .driver-chart--bars {
    padding: 10px;
  }

  .driver-chart__title {
    font-size: 1rem;
    margin-bottom: 14px;
  }

  .driver-chart__donut-body {
    flex-direction: column;
    align-items: center;
    text-align: left;
    gap: 14px;
  }

  .driver-chart__donut {
    width: min(220px, 72vw);
    height: min(220px, 72vw);
  }

  .driver-chart__legend {
    width: 100%;
    min-width: 0;
    font-size: 13px;
    gap: 8px;
  }

  .driver-chart__legend-item {
    grid-template-columns: 14px 1fr auto;
    gap: 10px;
  }

  .driver-chart__legend-text {
    white-space: normal;
    line-height: 1.35;
    word-break: break-word;
  }

  .driver-chart__bar-list {
    gap: 7px;
  }

  .driver-chart__bar-row {
    grid-template-columns: 90px minmax(0, 1fr) 88px;
    gap: 8px;
    align-items: center;
  }

  .driver-chart__bar-label {
    font-size: 12px;
    white-space: nowrap;
    line-height: normal;
    word-break: normal;
  }

  .driver-chart__bar-val {
    font-size: 12px;
  }

  .toolbar {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    margin-bottom: 14px;
  }

  .toolbar__search-wrap {
    min-width: 0;
    width: 100%;
    flex: none;
  }

  .toolbar__search {
    min-height: 48px;
    font-size: 16px;
    padding: 12px 14px 12px 44px;
    border-radius: 12px;
  }

  .toolbar__search-icon {
    left: 14px;
  }

  .toolbar__search-icon svg {
    width: 20px;
    height: 20px;
  }

  .toolbar__filters {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .toolbar__field {
    min-width: 0;
    width: 100%;
    max-width: none;
    gap: 6px;
  }

  .toolbar-label {
    margin-top: 0;
  }

  .toolbar-select {
    max-width: 100% !important;
    width: 100%;
  }

  .toolbar :deep(.searchable-select) {
    flex: 0 1 auto;
    min-height: 0;
    max-width: 100% !important;
    width: 100%;
  }

  .toolbar :deep(.searchable-select__trigger) {
    min-height: 48px;
    font-size: 16px;
    border-radius: 12px;
  }

  .toolbar :deep(.searchable-select__search) {
    font-size: 16px;
  }

  .toolbar :deep(.searchable-select__item) {
    padding: 12px 14px;
    font-size: 15px;
  }

  .toolbar__actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-left: 0;
    width: 100%;
    justify-self: stretch;
  }

  .toolbar__btn-query {
    grid-column: 1 / -1;
    min-height: 48px;
    font-size: 15px;
    font-weight: 800;
    border-radius: 12px;
    touch-action: manipulation;
  }

  .toolbar__btn-new,
  .toolbar__btn-refresh {
    min-height: 48px;
    font-size: 15px;
    font-weight: 700;
    border-radius: 12px;
    touch-action: manipulation;
  }

  .toolbar__actions:not(:has(.toolbar__btn-new)) .toolbar__btn-refresh {
    grid-column: 1 / -1;
  }

  .msg {
    font-size: 14px;
    padding: 12px 14px;
    line-height: 1.45;
  }

  .muted {
    font-size: 14px;
    padding: 4px 0 8px;
  }

  .list-wrap {
    overflow-x: visible;
    -webkit-overflow-scrolling: auto;
  }

  .driver-pager {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    margin-top: 12px;
    padding: 14px 12px;
  }

  .driver-pager__summary {
    flex: none;
    text-align: center;
    font-size: 14px;
    line-height: 1.4;
  }

  .driver-pager__size-row {
    justify-content: center;
    width: 100%;
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 2px;
  }

  .driver-pager__size {
    min-height: 44px;
    font-size: 16px;
    flex: 0 0 auto;
    min-width: 5.5rem;
    max-width: 8rem;
  }

  .driver-pager__page {
    text-align: center;
    width: 100%;
    font-size: 14px;
  }

  .driver-pager__nav {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    width: 100%;
    margin-left: 0;
  }

  .driver-pager__btn {
    min-height: 48px;
    font-size: 15px;
    touch-action: manipulation;
  }

  .tbl--desktop {
    display: none;
  }

  .driver-cards-mobile {
    display: block;
  }

  .driver-cards {
    gap: 14px;
  }

  .driver-card {
    padding: 16px;
    border-radius: 16px;
  }

  .driver-card__top {
    margin-bottom: 14px;
    gap: 8px;
  }

  .driver-card__name {
    font-size: 1.08rem;
  }

  .driver-card__status {
    font-size: 13px;
    padding: 4px 12px;
  }

  .driver-card__row {
    grid-template-columns: minmax(76px, 32%) 1fr;
    gap: 8px 10px;
    font-size: 14px;
    margin-bottom: 10px;
  }

  .driver-card__k {
    font-size: 12px;
  }

  .driver-card__v {
    line-height: 1.45;
  }

  .driver-card__mono {
    font-size: 13px;
    word-break: break-all;
  }

  .driver-card__actions {
    gap: 12px;
    margin-top: 16px;
    padding-top: 14px;
  }

  .driver-card__btn {
    min-height: 48px;
    border-radius: 12px;
  }

  .empty-hint {
    font-size: 14px;
    line-height: 1.5;
    padding: 32px 16px !important;
  }

  .driver-cards-mobile__empty {
    padding: 28px 14px !important;
    font-size: 14px;
    line-height: 1.5;
  }

  .form--drivers {
    grid-template-columns: 1fr;
    gap: 8px 0;
  }

  .form--drivers label {
    margin-top: 4px;
    font-weight: 700;
    font-size: 13px;
  }

  .form--drivers input,
  .form--drivers select,
  .form--drivers textarea {
    font-size: 16px;
    min-height: 48px;
    border-radius: 12px;
    padding: 12px 12px;
  }

  .form--drivers textarea {
    min-height: 88px;
    resize: vertical;
  }
}

@media (max-width: 380px) {
  .driver-chart__bar-row {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .driver-chart__bar-track {
    grid-column: 1 / -1;
  }

  .driver-chart__bar-val {
    text-align: left;
    font-variant-numeric: tabular-nums;
  }
}
</style>
