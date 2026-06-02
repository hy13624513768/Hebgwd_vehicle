<template>
  <div class="drivers-view">
    <section v-if="stats" class="driver-overview" aria-label="驾驶员统计">
      <div class="driver-overview__kpi">
        <span class="driver-overview__kpi-label">在册驾驶员</span>
        <strong class="driver-overview__kpi-num">{{ stats.total }}</strong>
        <span class="driver-overview__kpi-breakdown">
          本单位驾驶员 <strong>{{ employmentKpi.internal }}</strong> 人，
          外包驾驶员 <strong>{{ employmentKpi.outsourced }}</strong> 人
        </span>
        <span class="driver-overview__kpi-hint">（筛选结果共 {{ totalCount }} 条）</span>
      </div>

      <div class="driver-charts" aria-label="驾驶员分布图表">
        <div class="driver-chart driver-chart--bars">
          <h3 class="driver-chart__title">车间分布</h3>
          <p v-if="!workshopChips.length" class="driver-chart__empty">暂无车间分布数据</p>
          <ul v-else class="driver-chart__bar-list driver-chart__bar-list--scroll" role="list">
            <li v-for="([label, cnt], idx) in workshopChips" :key="'ws-bar-' + label" class="driver-chart__bar-row" role="listitem">
              <span class="driver-chart__bar-label" :title="label">{{ label }}</span>
              <div class="driver-chart__bar-track" :title="`${label}：${cnt} 人`">
                <div class="driver-chart__bar-fill" :style="workshopBarFillStyle(cnt, idx)" />
              </div>
              <span class="driver-chart__bar-val">{{ cnt }}</span>
            </li>
          </ul>
        </div>
        <div class="driver-chart driver-chart--bars">
          <h3 class="driver-chart__title">准驾类型分布</h3>
          <p v-if="!licenseChips.length" class="driver-chart__empty">暂无准驾类型数据</p>
          <ul v-else class="driver-chart__bar-list driver-chart__bar-list--scroll" role="list">
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
          <span class="toolbar-label">车间</span>
          <SearchableSelect
            v-model="filterWorkshopId"
            class="toolbar-select"
            :options="workshopFilterOptions"
            allow-empty
            empty-label="全部"
            search-placeholder="输入车间关键字…"
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
          v-if="canEditDriverRecords"
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
            <th>车间</th>
            <th>状态</th>
            <th>年龄</th>
            <th>身份证号</th>
            <th>健康体检报告</th>
            <th>外包人员入职手续</th>
            <th>首次入职</th>
            <th v-if="canEditDriverRecords" class="w">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0">
            <td :colspan="canEditDriverRecords ? 12 : 11" class="empty-hint">暂无数据，可调整筛选后点击查询。</td>
          </tr>
          <tr v-for="(d, idx) in rows" :key="d.id">
            <td class="muted">{{ displayRowSeq(idx) }}</td>
            <td class="strong">{{ d.name }}</td>
            <td>{{ d.phone }}</td>
            <td>{{ d.license_type || '—' }}</td>
            <td>{{ driverWorkshopLabel(d) }}</td>
            <td>{{ driverEmploymentStatusLabel(d) }}</td>
            <td>{{ formatAgeFromIdCard(d.id_card) }}</td>
            <td class="mono">{{ d.id_card || '—' }}</td>
            <td class="col-long" :title="d.health_check_report || ''">{{ trunc(d.health_check_report, 24) }}</td>
            <td class="col-long" :title="d.outsourcing_onboarding || ''">{{ trunc(d.outsourcing_onboarding, 24) }}</td>
            <td>{{ d.first_hire_date ? fmtDate(d.first_hire_date) : '—' }}</td>
            <td v-if="canEditDriverRecords" class="w">
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
              <span class="driver-card__status">{{ driverEmploymentStatusLabel(d) }}</span>
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
              <span class="driver-card__k">车间</span>
              <span class="driver-card__v">{{ driverWorkshopLabel(d) }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">年龄</span>
              <span class="driver-card__v">{{ formatAgeFromIdCard(d.id_card) }}</span>
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
            <div v-if="canEditDriverRecords" class="driver-card__actions">
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
        <input
          v-model.trim="form.name"
          :readonly="!canEditDriverRecords"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>电话</label>
        <input
          v-model.trim="form.phone"
          type="tel"
          inputmode="numeric"
          maxlength="11"
          pattern="\d{11}"
          placeholder="11 位手机号"
          :readonly="!canEditDriverRecords"
          @input="onPhoneInput"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>准驾</label>
        <SearchableSelect
          v-model="formLicenseId"
          :options="licenseFormOptions"
          allow-empty
          empty-label="请选择准驾类型"
          search-placeholder="输入准驾关键字…"
          :disabled="!canEditDriverRecords"
          @denied="denyEdit"
        />

        <label>车间</label>
        <SearchableSelect
          v-model="formWorkshopId"
          :options="workshopFormOptions"
          allow-empty
          empty-label="请选择车间"
          search-placeholder="输入车间关键字…"
          :disabled="!canEditDriverRecords"
          @denied="denyEdit"
        />

        <label>状态</label>
        <SearchableSelect
          v-model="formEmploymentStatusId"
          :options="employmentStatusFormOptions"
          allow-empty
          empty-label="请选择状态"
          search-placeholder="本单位 / 外包…"
          :disabled="!canEditDriverRecords"
          @denied="denyEdit"
        />

        <label>身份证号</label>
        <input
          v-model.trim="form.id_card"
          class="mono"
          maxlength="18"
          placeholder="18 位身份证号"
          :readonly="!canEditDriverRecords"
          @input="onIdCardInput"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>年龄</label>
        <div class="form-readonly" aria-live="polite">{{ formAgeDisplay }}</div>

        <label>健康体检报告</label>
        <textarea
          v-model.trim="form.health_check_report"
          rows="2"
          :readonly="!canEditDriverRecords"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>外包人员入职手续</label>
        <textarea
          v-model.trim="form.outsourcing_onboarding"
          rows="2"
          :readonly="!canEditDriverRecords"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>首次入职时间</label>
        <input
          v-model="form.first_hire_date"
          type="date"
          :readonly="!canEditDriverRecords"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />
      </div>

      <template #footer>
        <button type="button" class="ghost" @click="modalOpen = false">取消</button>
        <button
          v-if="canEditDriverRecords"
          type="button"
          class="primary"
          :disabled="saving"
          @click="save"
        >
          保存
        </button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, reactive, ref } from 'vue'

import * as api from '@/api/drivers'
import type { DriverStats } from '@/api/drivers'
import { fetchWorkshops, type Workshop } from '@/api/workshops'
import type { Driver } from '@/api/types'
import AppModal from '@/components/AppModal.vue'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import { usePermissions } from '@/composables/usePermissions'
import { fmtDate } from '@/utils/format'
import { ageFromIdCard, formatAgeFromIdCard } from '@/utils/idCard'

const EDIT_DENIED_MSG = '当前账号无权修改驾驶员档案，请联系段级或超级管理员。'

/** 人员状态：仅本单位 / 外包 */
const EMPLOYMENT_STATUS_OPTIONS: SearchableOption[] = [
  { id: 1, label: '本单位', keywords: '本单位 在岗 在职' },
  { id: 2, label: '外包', keywords: '外包 外包人员' },
]

const COMMON_LICENSE_TYPES = ['A1', 'A2', 'A3', 'B1', 'B2', 'C1'] as const

/** 编辑框准驾下拉中不展示的机型（大小写不敏感） */
const EXCLUDED_LICENSE_TYPES = new Set([
  'C2',
  'C3',
  'C4',
  'C5',
  'C6',
  'D',
  'E',
  'F',
  'M',
  'N',
  'P',
])

const PHONE_PATTERN = /^\d{11}$/
const ID_CARD_PATTERN = /^\d{17}[\dX]$/

const { canEditDriverRecords } = usePermissions()

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
const driverWorkshops = ref<string[]>([])
const driverLicenseTypes = ref<string[]>([])
const workshopsMaster = ref<Workshop[]>([])
const filterWorkshopId = ref(0)
const filterLicenseId = ref(0)
const formWorkshopId = ref(0)
const formLicenseId = ref(0)
const formEmploymentStatusId = ref(0)
const employmentStatusFormOptions = EMPLOYMENT_STATUS_OPTIONS

const modalOpen = ref(false)
const modalTitle = ref('新增驾驶员')
const editingId = ref<number | null>(null)

const form = reactive({
  name: '',
  phone: '',
  id_card: '',
  health_check_report: '',
  outsourcing_onboarding: '',
  first_hire_date: '',
})

const formAgeDisplay = computed(() => {
  const age = ageFromIdCard(form.id_card)
  if (age === null) {
    const raw = form.id_card.trim()
    return raw ? '无法识别（请检查身份证号）' : '填写身份证号后自动计算'
  }
  return `${age} 岁`
})

function driverWorkshopLabel(d: Driver) {
  return (d.workshop_name || '').trim() || '未分配'
}

function driverEmploymentStatusLabel(d: Driver) {
  const raw = (d.status || '').trim()
  if (!raw) return '—'
  if (raw === '本单位' || raw === '外包') return raw
  if (raw.includes('外包')) return '外包'
  if (raw === '在岗' || raw === '在职') return '本单位'
  return raw
}

function employmentStatusIdFromLabel(label: string): number {
  const t = label.trim()
  if (!t || t === '—') return 0
  if (t === '外包' || t.includes('外包')) return 2
  if (t === '本单位') return 1
  return 1
}

function denyEdit() {
  window.alert(EDIT_DENIED_MSG)
}

function onPhoneInput(e: Event) {
  const el = e.target as HTMLInputElement
  const digits = el.value.replace(/\D/g, '').slice(0, 11)
  if (el.value !== digits) el.value = digits
  form.phone = digits
}

function onIdCardInput(e: Event) {
  const el = e.target as HTMLInputElement
  const normalized = el.value
    .toUpperCase()
    .replace(/[^0-9X]/g, '')
    .slice(0, 18)
  if (el.value !== normalized) el.value = normalized
  form.id_card = normalized
}

function validateDriverForm(): string | null {
  const phone = form.phone.trim()
  if (!PHONE_PATTERN.test(phone)) return '电话须为 11 位数字'
  const idCard = form.id_card.trim()
  if (idCard && !ID_CARD_PATTERN.test(idCard)) return '身份证号须为 18 位（末位可为 X）'
  return null
}

function onFieldFocus() {
  if (!canEditDriverRecords.value) denyEdit()
}

function onFieldClick() {
  if (!canEditDriverRecords.value) denyEdit()
}

const workshopFilterOptions = computed<SearchableOption[]>(() => {
  const names = new Set<string>()
  for (const w of driverWorkshops.value) names.add(w)
  if (stats.value?.by_workshop) {
    for (const k of Object.keys(stats.value.by_workshop)) names.add(k)
  }
  const sorted = [...names].sort((a, b) => a.localeCompare(b, 'zh-CN'))
  const out: SearchableOption[] = []
  let nid = 1
  for (const label of sorted) {
    out.push({ id: nid, label, keywords: label })
    nid += 1
  }
  return out
})

const workshopFormOptions = computed<SearchableOption[]>(() =>
  workshopsMaster.value.map((w) => ({
    id: w.id,
    label: w.name,
    keywords: w.name,
  })),
)

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

function isSelectableLicenseType(label: string): boolean {
  const t = label.trim()
  if (!t) return false
  return !EXCLUDED_LICENSE_TYPES.has(t.toUpperCase())
}

const licenseFormOptions = computed<SearchableOption[]>(() => {
  const labels = new Set<string>()
  for (const t of COMMON_LICENSE_TYPES) labels.add(t)
  for (const s of driverLicenseTypes.value) {
    if (s && isSelectableLicenseType(s)) labels.add(s)
  }
  return [...labels].sort().map((label, idx) => ({
    id: idx + 1,
    label,
    keywords: label,
  }))
})

const employmentKpi = computed(() => {
  const m = stats.value?.by_employment_status
  return {
    internal: m?.['本单位'] ?? 0,
    outsourced: m?.['外包'] ?? 0,
  }
})

const workshopChips = computed(() => {
  if (!stats.value) return [] as [string, number][]
  return Object.entries(stats.value.by_workshop).sort((a, b) => b[1] - a[1])
})

const licenseChips = computed(() => {
  if (!stats.value) return [] as [string, number][]
  return Object.entries(stats.value.by_license_type).sort((a, b) => b[1] - a[1])
})

const workshopBarMax = computed(() => {
  const chips = workshopChips.value
  if (!chips.length) return 1
  return Math.max(...chips.map((x) => x[1]), 1)
})

const licenseBarMax = computed(() => {
  const chips = licenseChips.value
  if (!chips.length) return 1
  return Math.max(...chips.map((x) => x[1]), 1)
})

const totalDriverPages = computed(() =>
  Math.max(1, Math.ceil(totalCount.value / listPager.page_size) || 1),
)

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

/** 车间条形宽度 + 渐变（避免模板中调用独立函数名在 HMR 下偶发非函数错误） */
function workshopBarFillStyle(cnt: number, idx: number): Record<string, string> {
  const max = workshopBarMax.value
  const pct = max > 0 ? (cnt / max) * 100 : 0
  return { width: `${pct}%`, ...barFillStyle(idx) }
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

function selectedWorkshopQuery(): string | undefined {
  if (!filterWorkshopId.value) return undefined
  return workshopFilterOptions.value.find((x) => x.id === filterWorkshopId.value)?.label
}

function selectedLicenseQuery(): string | undefined {
  if (!filterLicenseId.value) return undefined
  return licenseTypeOptions.value.find((x) => x.id === filterLicenseId.value)?.label
}

function buildDriverListParams() {
  return {
    q: q.value || undefined,
    skip: (listPager.page - 1) * listPager.page_size,
    limit: listPager.page_size,
    workshop: selectedWorkshopQuery(),
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
    const [f, ws] = await Promise.all([api.getDriverFilters(), fetchWorkshops()])
    driverWorkshops.value = f.workshops
    driverLicenseTypes.value = f.license_types
    workshopsMaster.value = ws
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
  form.id_card = ''
  form.health_check_report = ''
  form.outsourcing_onboarding = ''
  form.first_hire_date = ''
  formWorkshopId.value = 0
  formLicenseId.value = 0
  formEmploymentStatusId.value = 0
}

function syncFormEmploymentStatusFromId(): string {
  return employmentStatusFormOptions.find((x) => x.id === formEmploymentStatusId.value)?.label ?? ''
}

function syncFormLicenseFromId() {
  const label = licenseFormOptions.value.find((x) => x.id === formLicenseId.value)?.label
  return label || ''
}

function syncFormWorkshopFromId(): number | null {
  if (!formWorkshopId.value) return null
  const hit = workshopsMaster.value.find((w) => w.id === formWorkshopId.value)
  return hit?.id ?? null
}

function openCreate() {
  if (!canEditDriverRecords.value) {
    denyEdit()
    return
  }
  editingId.value = null
  modalTitle.value = '新增驾驶员'
  resetForm()
  modalOpen.value = true
}

function openEdit(d: Driver) {
  if (!canEditDriverRecords.value) {
    denyEdit()
    return
  }
  editingId.value = d.id
  modalTitle.value = '编辑驾驶员'
  form.name = d.name
  form.phone = d.phone
  form.id_card = d.id_card || ''
  form.health_check_report = d.health_check_report || ''
  form.outsourcing_onboarding = d.outsourcing_onboarding || ''
  form.first_hire_date = d.first_hire_date ? d.first_hire_date.slice(0, 10) : ''
  formWorkshopId.value = d.workshop_id ?? 0
  const licOpt = licenseFormOptions.value.find((x) => x.label === (d.license_type || '').trim())
  formLicenseId.value = licOpt?.id ?? 0
  formEmploymentStatusId.value = employmentStatusIdFromLabel(driverEmploymentStatusLabel(d))
  modalOpen.value = true
}

async function save() {
  if (!canEditDriverRecords.value) {
    denyEdit()
    return
  }
  const formErr = validateDriverForm()
  if (formErr) {
    msg.value = formErr
    return
  }
  saving.value = true
  msg.value = ''
  try {
    const payload: Record<string, unknown> = {
      name: form.name,
      phone: form.phone,
      license_type: syncFormLicenseFromId(),
      workshop_id: syncFormWorkshopFromId(),
      status: syncFormEmploymentStatusFromId(),
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

.driver-overview__kpi-breakdown {
  font-size: 12px;
  color: var(--cl-charcoal);
}

.driver-overview__kpi-breakdown strong {
  font-weight: 800;
  color: var(--cl-coral);
}

.driver-overview__kpi-hint {
  font-size: 12px;
  color: var(--cl-olive);
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

/* 与 VehiclesView `.bars--scroll` 一致：固定可视高度，超出纵向滚动 */
.driver-chart__bar-list--scroll {
  max-height: 196px;
  overflow-y: auto;
  padding-right: 4px;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
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

  .driver-overview__kpi-breakdown {
    width: 100%;
    flex-basis: 100%;
    font-size: 13px;
  }

  .driver-overview__kpi-hint {
    width: 100%;
    flex-basis: 100%;
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

  .driver-chart__bar-list {
    gap: 7px;
  }

  .driver-chart__bar-list--scroll {
    max-height: min(280px, 36vh);
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

.form-readonly {
  min-height: 42px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream, #e8e0d4);
  background: var(--cl-warm-sand, #f5efe6);
  color: var(--cl-near-black, #1a1a1a);
  font-size: 14px;
  line-height: 1.45;
  display: flex;
  align-items: center;
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
