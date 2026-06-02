<template>
  <div class="vehicles-view">
    <div class="toolbar">
      <input
        v-model="q"
        class="q"
        type="search"
        placeholder="车牌、单位、种类、类型、品牌等（支持正则；空格为多关键字同时匹配）"
        @keydown.enter.prevent="reload"
      />
      <button v-if="canManageFleet" type="button" class="primary" @click="openCreate">新增车辆</button>
      <button type="button" class="ghost" :disabled="loading" @click="reload">刷新</button>
    </div>

    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <section v-else class="panel analytics">
      <div class="panel-hd panel-hd--split" :class="{ 'panel-hd--filters-open': orgUnitComboOpen }">
        <div>公务用车数据</div>
        <div class="filters">
          <div ref="orgUnitComboRef" class="sel-combo" :class="{ 'sel-combo--open': orgUnitComboOpen }">
            <button
              type="button"
              class="sel-combo__btn sel"
              title="使用单位"
              :aria-expanded="orgUnitComboOpen"
              aria-haspopup="listbox"
              @click="toggleOrgUnitCombo"
            >
              <span class="sel-combo__btn-text">{{ orgUnitDisplayLabel }}</span>
              <span class="sel-combo__caret" aria-hidden="true" />
            </button>
            <div v-show="orgUnitComboOpen" class="sel-combo__panel" @click.stop>
              <input
                ref="orgUnitSearchInputRef"
                v-model="orgUnitSearchQ"
                type="search"
                class="sel-combo__search"
                placeholder="关键字筛选单位…"
                autocomplete="off"
                @keydown.esc.stop.prevent="closeOrgUnitCombo"
              />
              <ul class="sel-combo__list" role="listbox" aria-label="使用单位">
                <li
                  role="option"
                  :aria-selected="filterOrgUnit === 'all'"
                  class="sel-combo__opt"
                  @click="selectOrgUnit('all')"
                >
                  全部使用单位
                </li>
                <li
                  v-for="o in orgUnitFilteredOptions"
                  :key="o"
                  role="option"
                  :aria-selected="filterOrgUnit === o"
                  class="sel-combo__opt"
                  @click="selectOrgUnit(o)"
                >
                  {{ o === EMPTY_OPT ? '未填写' : o }}
                </li>
                <li
                  v-if="orgUnitFilteredOptions.length === 0 && orgUnitSearchQ.trim()"
                  class="sel-combo__hint"
                >
                  无匹配单位，请更换关键字
                </li>
              </ul>
            </div>
          </div>
          <select v-model="filterBrand" class="sel" title="车辆品牌">
            <option value="all">全部品牌</option>
            <option v-for="b in brandFilterOptions" :key="b" :value="b">
              {{ b === EMPTY_OPT ? '未填写' : b }}
            </option>
          </select>
          <select v-model="filterSeats" class="sel" title="座位数">
            <option value="all">全部座数</option>
            <option v-for="n in seatFilterOptions" :key="n" :value="String(n)">{{ n }} 座</option>
          </select>
          <select v-model="filterYear" class="sel" title="登记年份（按注册登记时间）">
            <option value="all">全部年份</option>
            <option v-for="y in yearFilterOptions" :key="y" :value="y">
              {{ y === NO_YEAR_OPT ? '未登记年份' : `${y} 年` }}
            </option>
          </select>
          <select v-model="filterVehicleTypeLabel" class="sel" title="车辆类型（与条形图一致，可点击图表快捷筛选）">
            <option value="all">全部车辆类型</option>
            <option v-for="t in vehicleTypeLabelFilterOptions" :key="t" :value="t">{{ t }}</option>
          </select>
          <select v-model="statusSlice" class="sel">
            <option value="all">全部状态</option>
            <option value="active">在役</option>
            <option value="inactive">停用</option>
            <option value="repairing">维修中</option>
          </select>
          <select v-model="metricSlice" class="sel">
            <option value="count">按车辆数</option>
            <option value="mileage">按总里程</option>
          </select>
        </div>
      </div>

      <div class="kpis">
        <div class="mini">
          <div class="mk">车辆总数</div>
          <div class="mv">{{ filteredRows.length }}</div>
        </div>
        <div class="mini">
          <div class="mk">总里程</div>
          <div class="mv">{{ formatNum(kpi.totalMileage) }} km</div>
        </div>
        <div class="mini">
          <div class="mk">平均座位数</div>
          <div class="mv">{{ formatNum(kpi.avgSeats) }}</div>
        </div>
        <div class="mini">
          <div class="mk">平均单车里程</div>
          <div class="mv">{{ formatNum(kpi.avgMileagePerCar) }} km</div>
        </div>
      </div>

      <div class="charts">
        <article class="chart">
          <div class="ct">车间（使用单位）分布 <span class="ct-hint">· 点击筛选表格</span></div>
          <div class="bars bars--scroll">
            <button
              v-for="(x, idx) in orgUnitStats"
              :key="x.name"
              type="button"
              class="bar-row bar-row--interactive"
              :class="{ 'bar-row--active': orgUnitBarActive(x) }"
              :title="`筛选使用单位：${x.name}（再点一次取消）`"
              @click="onOrgUnitBarClick(x)"
            >
              <div class="bar-label">{{ x.name }}</div>
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill" :style="chartBarFillStyle(x.value, orgUnitMax, idx)" />
              </div>
              <div class="bar-value">{{ formatMetricValue(x.value) }}</div>
            </button>
          </div>
        </article>

        <article class="chart">
          <div class="ct">品牌分布（Top 8） <span class="ct-hint">· 点击筛选表格</span></div>
          <div class="bars bars--scroll">
            <button
              v-for="(x, idx) in brandStats"
              :key="x.name"
              type="button"
              class="bar-row bar-row--interactive"
              :class="{ 'bar-row--active': brandBarActive(x) }"
              :title="`筛选品牌：${x.name}（再点一次取消）`"
              @click="onBrandBarClick(x)"
            >
              <div class="bar-label">{{ x.name }}</div>
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill" :style="chartBarFillStyle(x.value, brandMax, idx)" />
              </div>
              <div class="bar-value">{{ formatMetricValue(x.value) }}</div>
            </button>
          </div>
        </article>

        <!-- 宽屏两列网格：注册登记在左、座位数在右（同排）；窄屏单列自上而下 -->
        <article class="chart">
          <div class="ct">注册登记时间分布（按登记年份，与上方 KPI 筛选一致） <span class="ct-hint">· 点击筛选表格</span></div>
          <div class="bars bars--scroll">
            <button
              v-for="(row, idx) in registrationYearChart"
              :key="row.name"
              type="button"
              class="bar-row bar-row--interactive"
              :class="{ 'bar-row--active': yearBarActive(row) }"
              :title="`筛选登记年份：${row.name === '未登记' ? '未登记' : row.name + '年'}（再点一次取消）`"
              @click="onYearBarClick(row)"
            >
              <div class="bar-label">{{ row.name === '未登记' ? '未登记' : `${row.name}年` }}</div>
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill" :style="chartBarFillStyle(row.value, registrationYearChartMax, idx)" />
              </div>
              <div class="bar-value">{{ formatMetricValue(row.value) }}</div>
            </button>
          </div>
        </article>

        <article class="chart">
          <div class="ct">座位数分布 <span class="ct-hint">· 点击筛选表格</span></div>
          <div class="bars bars--scroll">
            <button
              v-for="(x, idx) in seatStats"
              :key="x.name"
              type="button"
              class="bar-row bar-row--interactive"
              :class="{ 'bar-row--active': seatBarActive(x) }"
              :title="`筛选座位数：${x.name} 座（再点一次取消）`"
              @click="onSeatBarClick(x)"
            >
              <div class="bar-label">{{ x.name }}座</div>
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill" :style="chartBarFillStyle(x.value, seatMax, idx)" />
              </div>
              <div class="bar-value">{{ formatMetricValue(x.value) }}</div>
            </button>
          </div>
        </article>

        <article class="chart chart--wide">
          <div class="ct">车辆类型标签占比（bus_vehicle.vehicle_type_label） <span class="ct-hint">· 点击筛选表格</span></div>
          <p class="chart-note">
            与上方车间、品牌、座数、登记年份、车辆类型、状态及搜索筛选一致；指标随「按车辆数 / 按总里程」切换，占比为当前筛选结果内合计的份额。
          </p>
          <div v-if="!vehicleTypeLabelStats.length" class="bars bars--scroll bars--empty">
            <p class="empty-hint">当前筛选下没有车辆，请调整条件或刷新。</p>
          </div>
          <div v-else class="bars bars--scroll">
            <button
              v-for="(x, idx) in vehicleTypeLabelStats"
              :key="x.name"
              type="button"
              class="bar-row bar-row--interactive"
              :class="{ 'bar-row--active': vehicleTypeBarActive(x) }"
              :title="`筛选车辆类型：${x.name}（再点一次取消）`"
              @click="onVehicleTypeBarClick(x)"
            >
              <div class="bar-label" :title="x.name">{{ x.name }}</div>
              <div class="bar-track" aria-hidden="true">
                <div class="bar-fill" :style="chartBarFillStyle(x.value, vehicleTypeLabelMax, idx)" />
              </div>
              <div class="bar-value bar-value--share">
                {{ formatMetricValue(x.value) }}（{{ formatVehicleTypeShare(x.value) }}）
              </div>
            </button>
          </div>
        </article>
      </div>
    </section>

    <div v-if="!loading" ref="tblWrapRef" class="tbl-wrap">
      <table class="tbl tbl--desktop">
        <thead>
          <tr>
            <th class="col-unit">使用单位</th>
            <th class="col-narrow">种类</th>
            <th class="col-plate">车牌号</th>
            <th class="col-type">车辆类型</th>
            <th class="col-brand">车辆品牌</th>
            <th class="col-narrow">排放标准</th>
            <th class="col-narrow">排量</th>
            <th class="col-spec">车辆规格</th>
            <th class="w">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredRows.length === 0">
            <td colspan="9" class="empty-hint">当前筛选条件下没有车辆，请调整筛选或点击刷新。</td>
          </tr>
          <tr v-for="v in pagedTableRows" :key="v.id">
            <td class="t col-unit" :title="v.org_unit || undefined">{{ cell(v.org_unit) }}</td>
            <td class="t col-narrow" :title="v.vehicle_class || undefined">{{ cell(v.vehicle_class) }}</td>
            <td class="strong col-plate">{{ v.plate_number }}</td>
            <td class="t col-type" :title="v.vehicle_type_label || undefined">{{ cell(v.vehicle_type_label) }}</td>
            <td class="t col-brand" :title="v.brand || undefined">{{ cell(v.brand) }}</td>
            <td class="t col-narrow">{{ cell(v.emission_std) }}</td>
            <td class="t col-narrow">{{ cell(v.displacement) }}</td>
            <td class="t col-spec" :title="vehicleSpec(v)">{{ vehicleSpec(v) }}</td>
            <td class="w">
              <button v-if="canManageFleet" type="button" class="link" @click="openEdit(v)">编辑</button>
              <button v-if="canManageFleet" type="button" class="link danger" @click="onDelete(v)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="vehicle-cards-mobile" aria-label="车辆列表">
        <p v-if="filteredRows.length === 0" class="empty-hint vehicle-cards-mobile__empty">
          当前筛选条件下没有车辆，请调整筛选或点击刷新。
        </p>
        <ul v-else class="vehicle-cards">
          <li v-for="v in pagedTableRows" :key="`m-${v.id}`" class="vehicle-card">
            <div class="vehicle-card__top">
              <span class="vehicle-card__plate">{{ v.plate_number }}</span>
              <span class="vehicle-card__pill">{{ cell(v.vehicle_class) }}</span>
            </div>
            <div class="vehicle-card__unit">{{ cell(v.org_unit) }}</div>
            <div class="vehicle-card__grid">
              <div class="vehicle-card__row">
                <span class="vehicle-card__k">类型</span>
                <span class="vehicle-card__v">{{ cell(v.vehicle_type_label) }}</span>
              </div>
              <div class="vehicle-card__row">
                <span class="vehicle-card__k">品牌</span>
                <span class="vehicle-card__v">{{ cell(v.brand) }}</span>
              </div>
              <div class="vehicle-card__row">
                <span class="vehicle-card__k">排放</span>
                <span class="vehicle-card__v">{{ cell(v.emission_std) }}</span>
              </div>
              <div class="vehicle-card__row">
                <span class="vehicle-card__k">排量</span>
                <span class="vehicle-card__v">{{ cell(v.displacement) }}</span>
              </div>
            </div>
            <div class="vehicle-card__spec">
              <span class="vehicle-card__k">规格</span>
              <p class="vehicle-card__spec-text">{{ vehicleSpec(v) }}</p>
            </div>
            <div v-if="canManageFleet" class="vehicle-card__actions">
              <button type="button" class="vehicle-card__btn" @click="openEdit(v)">编辑</button>
              <button type="button" class="vehicle-card__btn vehicle-card__btn--danger" @click="onDelete(v)">
                删除
              </button>
            </div>
          </li>
        </ul>
      </div>

      <div v-if="filteredRows.length > 0" class="tbl-pager" role="navigation" aria-label="车辆列表分页">
        <button
          type="button"
          class="ghost tbl-pager__btn"
          :disabled="tablePage <= 1"
          @click="tablePage = Math.max(1, tablePage - 1)"
        >
          上一页
        </button>
        <span class="tbl-pager__meta">
          第 {{ tablePage }} / {{ tableTotalPages }} 页 · 本页 {{ pagedTableRows.length }} 条 · 共
          {{ filteredRows.length }} 条
        </span>
        <button
          type="button"
          class="ghost tbl-pager__btn"
          :disabled="tablePage >= tableTotalPages"
          @click="tablePage = Math.min(tableTotalPages, tablePage + 1)"
        >
          下一页
        </button>
      </div>
    </div>

    <AppModal :open="modalOpen" :title="modalTitle" @close="modalOpen = false">
      <div class="form form--vehicles">
        <label>车牌号</label>
        <input v-model.trim="form.plate_number" />

        <label>使用单位</label>
        <SearchableSelect
          v-model="formWorkshopId"
          :options="workshopFormOptions"
          allow-empty
          empty-label="请选择使用单位"
          search-placeholder="搜索车间名称…"
        />

        <label>种类</label>
        <input v-model.trim="form.vehicle_class" />

        <label>车辆类型</label>
        <input v-model.trim="form.vehicle_type_label" />

        <label>车辆品牌</label>
        <input v-model.trim="form.brand" />

        <label>型号（计入车辆规格）</label>
        <input v-model.trim="form.model" />

        <label>排放标准</label>
        <input v-model.trim="form.emission_std" />

        <label>排量</label>
        <input v-model.trim="form.displacement" />

        <label>注册登记时间（可选）</label>
        <input v-model="form.registered_at" type="date" />

        <label>VIN（可选）</label>
        <input v-model.trim="form.vin" />

        <label>颜色（计入车辆规格）</label>
        <input v-model.trim="form.color" />

        <label>座位数（计入车辆规格）</label>
        <input v-model.number="form.seats" type="number" min="1" max="60" />

        <label>里程（km）</label>
        <input v-model.number="form.mileage" type="number" min="0" />

        <label>状态</label>
        <select v-model="form.status">
          <option value="active">在役</option>
          <option value="inactive">停用</option>
          <option value="repairing">维修中</option>
        </select>

        <label>备注</label>
        <textarea v-model.trim="form.remarks" rows="3" />
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
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import * as api from '@/api/vehicles'
import { fetchWorkshops, type Workshop } from '@/api/workshops'
import AppModal from '@/components/AppModal.vue'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import { usePermissions } from '@/composables/usePermissions'
import type { Vehicle } from '@/api/types'

const { canManageFleet } = usePermissions()

const loading = ref(true)
const saving = ref(false)
const rows = ref<Vehicle[]>([])
/** 点击条形图后滚动到表格区域 */
const tblWrapRef = ref<HTMLElement | null>(null)
const q = ref('')
const msg = ref('')
const statusSlice = ref<'all' | 'active' | 'inactive' | 'repairing'>('all')
const metricSlice = ref<'count' | 'mileage'>('count')

/** 表格每页条数（仅影响列表 DOM；KPI/图表仍基于完整筛选结果） */
const TABLE_PAGE_SIZE = 15

/** 下拉中用占位表示「未填写」文本类字段，避免 option value 为空 */
const EMPTY_OPT = '__empty__'
/** 登记年份筛选用：无有效 registered_at 时占位 */
const NO_YEAR_OPT = '__no_year__'

const filterOrgUnit = ref<string>('all')
const filterBrand = ref<string>('all')
const filterSeats = ref<string>('all')
const filterYear = ref<string>('all')
/** 车辆类型标签；「未填写」与条形图空值桶一致 */
const filterVehicleTypeLabel = ref<string>('all')

/** 使用单位：可搜索下拉 */
const orgUnitComboRef = ref<HTMLElement | null>(null)
const orgUnitSearchInputRef = ref<HTMLInputElement | null>(null)
const orgUnitComboOpen = ref(false)
const orgUnitSearchQ = ref('')

function orgUnitOptionLabel(o: string) {
  return o === EMPTY_OPT ? '未填写' : o
}

const orgUnitDisplayLabel = computed(() => {
  if (filterOrgUnit.value === 'all') return '全部使用单位'
  return orgUnitOptionLabel(filterOrgUnit.value)
})

function closeOrgUnitCombo() {
  orgUnitComboOpen.value = false
  orgUnitSearchQ.value = ''
}

function toggleOrgUnitCombo() {
  orgUnitComboOpen.value = !orgUnitComboOpen.value
  if (orgUnitComboOpen.value) {
    orgUnitSearchQ.value = ''
    void nextTick(() => orgUnitSearchInputRef.value?.focus())
  }
}

function selectOrgUnit(v: string) {
  filterOrgUnit.value = v
  closeOrgUnitCombo()
}

function onOrgUnitDocPointerDown(e: MouseEvent) {
  const root = orgUnitComboRef.value
  if (!root || !orgUnitComboOpen.value) return
  const t = e.target
  if (t instanceof Node && !root.contains(t)) closeOrgUnitCombo()
}

const modalOpen = ref(false)
const modalTitle = ref('新增车辆')
const editingId = ref<number | null>(null)
const workshopsMaster = ref<Workshop[]>([])
const formWorkshopId = ref(0)

const workshopFormOptions = computed<SearchableOption[]>(() =>
  workshopsMaster.value.map((w) => ({
    id: w.id,
    label: w.name,
    keywords: w.name,
  })),
)

const form = reactive({
  plate_number: '',
  vehicle_class: '',
  vehicle_type_label: '',
  brand: '',
  model: '',
  emission_std: '',
  displacement: '',
  registered_at: '',
  vin: '',
  color: '',
  seats: 5,
  mileage: 0,
  status: 'active',
  remarks: '',
})

function cell(s: string | null | undefined) {
  const t = (s ?? '').trim()
  return t || '—'
}

/** 表格「车辆规格」：型号 + 颜色（座位数单独一列，此处不重复展示） */
function vehicleSpec(v: Vehicle) {
  const parts: string[] = []
  const m = (v.model ?? '').trim()
  const c = (v.color ?? '').trim()
  if (m) parts.push(m)
  if (c) parts.push(c)
  return parts.length ? parts.join(' · ') : '—'
}

type StatItem = { name: string; value: number }

function normOrg(v: Vehicle) {
  return (v.org_unit ?? '').trim() || EMPTY_OPT
}

function normBrand(v: Vehicle) {
  return (v.brand ?? '').trim() || EMPTY_OPT
}

function normVehicleTypeLabel(v: Vehicle) {
  return (v.vehicle_type_label ?? '').trim() || '未填写'
}

function escapeRegexChars(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

/**
 * 登记日期的展示/分桶键：优先使用 ISO 日期前缀（与业务「日历日」一致），
 * 否则再按 UTC 解析整段时间，避免 +08:00 午夜在 UTC 下变成前一天。
 */
function registeredAtCalendarKey(iso: string | null | undefined): string | null {
  if (!iso || !String(iso).trim()) return null
  const s = String(iso).trim()
  const head = /^(\d{4})-(\d{2})-(\d{2})/.exec(s)
  if (head) return `${head[1]}-${head[2]}-${head[3]}`
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 列表接口字段一般为 snake_case；兼容个别环境下的 camelCase */
function resolveRegisteredAt(v: Vehicle): string | null | undefined {
  const a = v.registered_at
  if (a != null && String(a).trim() !== '') return String(a)
  const camel = (v as unknown as { registeredAt?: string | null }).registeredAt
  if (camel != null && String(camel).trim() !== '') return String(camel)
  return undefined
}

/** 与占位说明一致的可检索字段，合并为一段文本供正则匹配 */
function registeredAtSearchText(iso: string | null | undefined) {
  const key = registeredAtCalendarKey(iso)
  if (!key) return ''
  const y = key.slice(0, 4)
  return `${key} ${y}年`
}

function vehicleSearchHaystack(v: Vehicle) {
  const parts = [
    v.plate_number,
    v.org_unit,
    v.vehicle_class,
    v.vehicle_type_label,
    v.brand,
    v.model,
    v.emission_std,
    v.displacement,
    v.vin,
    v.color,
    v.remarks,
    v.history_plate,
    v.engine_no,
    v.status,
    String(v.seats ?? ''),
    String(v.mileage ?? ''),
    registeredAtSearchText(resolveRegisteredAt(v)),
  ]
  return parts.map((x) => String(x ?? '').trim()).join(' ')
}

/** 空格分隔多个模式，每项先试正则，非法则按字面量匹配；全部需命中（且） */
function searchPatternsFromQuery(raw: string): RegExp[] | null {
  const trimmed = raw.trim()
  if (!trimmed) return null
  const tokens = trimmed.split(/\s+/).filter(Boolean)
  const res: RegExp[] = []
  for (const t of tokens) {
    try {
      res.push(new RegExp(t, 'iu'))
    } catch {
      res.push(new RegExp(escapeRegexChars(t), 'iu'))
    }
  }
  return res
}

const orgUnitFilterOptions = computed(() => {
  const set = new Set<string>()
  for (const v of rows.value) set.add(normOrg(v))
  return [...set].sort((a, b) => {
    if (a === EMPTY_OPT) return 1
    if (b === EMPTY_OPT) return -1
    return a.localeCompare(b, 'zh-CN')
  })
})

/** 使用单位下拉：关键字子串过滤；空格拆成多段时需全部命中 */
const orgUnitFilteredOptions = computed(() => {
  const opts = orgUnitFilterOptions.value
  const raw = orgUnitSearchQ.value.trim()
  if (!raw) return opts
  const tokens = raw.split(/\s+/).filter(Boolean)
  return opts.filter((o) => {
    const label = orgUnitOptionLabel(o)
    return tokens.every((t) => label.includes(t))
  })
})

/** 品牌选项：随「使用单位」级联；选单位后仅显示该单位下出现的品牌 */
const brandFilterOptions = computed(() => {
  const base =
    filterOrgUnit.value === 'all'
      ? rows.value
      : rows.value.filter((v) => normOrg(v) === filterOrgUnit.value)
  const set = new Set<string>()
  for (const v of base) set.add(normBrand(v))
  return [...set].sort((a, b) => {
    if (a === EMPTY_OPT) return 1
    if (b === EMPTY_OPT) return -1
    return a.localeCompare(b, 'zh-CN')
  })
})

/** 座数选项：随「使用单位」「品牌」级联 */
const seatFilterOptions = computed(() => {
  let base = rows.value
  if (filterOrgUnit.value !== 'all') {
    base = base.filter((v) => normOrg(v) === filterOrgUnit.value)
  }
  if (filterBrand.value !== 'all') {
    base = base.filter((v) => normBrand(v) === filterBrand.value)
  }
  const set = new Set<number>()
  for (const v of base) set.add(v.seats ?? 0)
  return [...set].filter((n) => n > 0).sort((a, b) => a - b)
})

/** 车辆类型选项：随使用单位、品牌级联（与座数一致） */
const vehicleTypeLabelFilterOptions = computed(() => {
  let base = rows.value
  if (filterOrgUnit.value !== 'all') {
    base = base.filter((v) => normOrg(v) === filterOrgUnit.value)
  }
  if (filterBrand.value !== 'all') {
    base = base.filter((v) => normBrand(v) === filterBrand.value)
  }
  const set = new Set<string>()
  for (const v of base) set.add(normVehicleTypeLabel(v))
  return [...set].sort((a, b) => {
    if (a === '未填写') return 1
    if (b === '未填写') return -1
    return a.localeCompare(b, 'zh-CN')
  })
})

const filteredRows = computed(() => {
  const patterns = searchPatternsFromQuery(q.value)
  return rows.value.filter((v) => {
    if (statusSlice.value !== 'all' && v.status !== statusSlice.value) return false
    if (filterOrgUnit.value !== 'all' && normOrg(v) !== filterOrgUnit.value) return false
    if (filterBrand.value !== 'all' && normBrand(v) !== filterBrand.value) return false
    if (filterSeats.value !== 'all' && String(v.seats) !== filterSeats.value) return false
    if (filterYear.value !== 'all' && vehicleYearBucket(v) !== filterYear.value) return false
    if (filterVehicleTypeLabel.value !== 'all' && normVehicleTypeLabel(v) !== filterVehicleTypeLabel.value) {
      return false
    }
    if (patterns) {
      const hay = vehicleSearchHaystack(v)
      if (!patterns.every((re) => re.test(hay))) return false
    }
    return true
  })
})

const tablePage = ref(1)

const tableTotalPages = computed(() =>
  Math.max(1, Math.ceil(filteredRows.value.length / TABLE_PAGE_SIZE)),
)

const pagedTableRows = computed(() => {
  const start = (tablePage.value - 1) * TABLE_PAGE_SIZE
  return filteredRows.value.slice(start, start + TABLE_PAGE_SIZE)
})

watch([q, statusSlice, filterOrgUnit, filterBrand, filterSeats, filterYear, filterVehicleTypeLabel], () => {
  tablePage.value = 1
})

watch(
  () => filteredRows.value.length,
  () => {
    const max = Math.max(1, Math.ceil(filteredRows.value.length / TABLE_PAGE_SIZE))
    if (tablePage.value > max) tablePage.value = max
  },
)

watch(rows, () => {
  if (filterOrgUnit.value !== 'all' && !orgUnitFilterOptions.value.includes(filterOrgUnit.value)) {
    filterOrgUnit.value = 'all'
  }
  if (filterBrand.value !== 'all' && !brandFilterOptions.value.includes(filterBrand.value)) {
    filterBrand.value = 'all'
  }
  if (filterSeats.value !== 'all' && !seatFilterOptions.value.map(String).includes(filterSeats.value)) {
    filterSeats.value = 'all'
  }
  if (filterYear.value !== 'all') {
    const ok = rows.value.some((v) => vehicleYearBucket(v) === filterYear.value)
    if (!ok) filterYear.value = 'all'
  }
  if (
    filterVehicleTypeLabel.value !== 'all' &&
    !vehicleTypeLabelFilterOptions.value.includes(filterVehicleTypeLabel.value)
  ) {
    filterVehicleTypeLabel.value = 'all'
  }
})

watch(filterOrgUnit, () => {
  if (filterBrand.value !== 'all' && !brandFilterOptions.value.includes(filterBrand.value)) {
    filterBrand.value = 'all'
  }
  if (filterSeats.value !== 'all' && !seatFilterOptions.value.map(String).includes(filterSeats.value)) {
    filterSeats.value = 'all'
  }
  if (
    filterVehicleTypeLabel.value !== 'all' &&
    !vehicleTypeLabelFilterOptions.value.includes(filterVehicleTypeLabel.value)
  ) {
    filterVehicleTypeLabel.value = 'all'
  }
})

watch(filterBrand, () => {
  if (filterSeats.value !== 'all' && !seatFilterOptions.value.map(String).includes(filterSeats.value)) {
    filterSeats.value = 'all'
  }
  if (
    filterVehicleTypeLabel.value !== 'all' &&
    !vehicleTypeLabelFilterOptions.value.includes(filterVehicleTypeLabel.value)
  ) {
    filterVehicleTypeLabel.value = 'all'
  }
})

const kpi = computed(() => {
  const totalMileage = filteredRows.value.reduce((s, x) => s + (x.mileage || 0), 0)
  const totalSeats = filteredRows.value.reduce((s, x) => s + (x.seats || 0), 0)
  const total = filteredRows.value.length || 1
  return {
    totalMileage,
    avgSeats: totalSeats / total,
    avgMileagePerCar: totalMileage / total,
  }
})

function buildStats(getKey: (v: Vehicle) => string, limit?: number): StatItem[] {
  const map = new Map<string, number>()
  for (const v of filteredRows.value) {
    const key = getKey(v) || '未分配'
    const add = metricSlice.value === 'mileage' ? v.mileage || 0 : 1
    map.set(key, (map.get(key) || 0) + add)
  }
  const arr = Array.from(map.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
  return typeof limit === 'number' ? arr.slice(0, limit) : arr
}

/** 使用单位分布：按名称本地化顺序（中文环境约等于首字拼音 A→Z）排列 */
const orgUnitStats = computed(() => {
  const items = buildStats((v) => (v.org_unit || '').trim() || '未分配车间')
  return [...items].sort((a, b) => a.name.localeCompare(b.name, 'zh-CN', { sensitivity: 'accent' }))
})
const brandStats = computed(() => buildStats((v) => (v.brand || '').trim() || '未知品牌', 8))
/** 车辆类型标签（与列表「车辆类型」列同源）；随筛选与 metricSlice 变化 */
const vehicleTypeLabelStats = computed(() =>
  buildStats((v) => (v.vehicle_type_label || '').trim() || '未填写'),
)
/** 座位数分布：按座位数十进制升序；标签仍为「1座」「10座」（内部用数字字符串聚合） */
const seatStats = computed(() => {
  const items = buildStats((v) => String(Number(v.seats) || 0))
  return [...items].sort((a, b) => {
    const na = Number.parseInt(a.name, 10)
    const nb = Number.parseInt(b.name, 10)
    const aNum = Number.isFinite(na) && !Number.isNaN(na)
    const bNum = Number.isFinite(nb) && !Number.isNaN(nb)
    if (aNum && bNum) return na - nb
    if (aNum) return -1
    if (bNum) return 1
    return a.name.localeCompare(b.name, 'zh-CN')
  })
})

/** 从 API / 数据库的 registered_at 字符串解析公历年份（不经过 buildStats，避免与其它分桶逻辑耦合） */
function parseYearFromRegisteredAt(raw: string | null | undefined): string | null {
  if (raw == null || String(raw).trim() === '') return null
  const s = String(raw).trim()
  const isoDay = /^(\d{4})-\d{2}-\d{2}/.exec(s)
  if (isoDay) return isoDay[1]
  const d = new Date(s)
  if (!Number.isNaN(d.getTime())) return String(d.getFullYear())
  const yOnly = /^(\d{4})/.exec(s)
  return yOnly ? yOnly[1] : null
}

function vehicleYearBucket(v: Vehicle): string {
  const y = parseYearFromRegisteredAt(resolveRegisteredAt(v) ?? undefined)
  return y ?? NO_YEAR_OPT
}

/** 登记年份下拉选项（来自当前列表数据，新→旧；无登记在最后） */
const yearFilterOptions = computed(() => {
  const set = new Set<string>()
  for (const v of rows.value) set.add(vehicleYearBucket(v))
  return [...set].sort((a, b) => {
    if (a === NO_YEAR_OPT) return 1
    if (b === NO_YEAR_OPT) return -1
    return Number.parseInt(b, 10) - Number.parseInt(a, 10)
  })
})

/** 按登记年份条形图：直接遍历 filteredRows，依据 bus_vehicle.registered_at（及 camelCase 兼容） */
const registrationYearChart = computed((): StatItem[] => {
  const map = new Map<string, number>()
  for (const v of filteredRows.value) {
    const reg = resolveRegisteredAt(v)
    const year = parseYearFromRegisteredAt(reg ?? undefined)
    const bucket = year ?? '未登记'
    const add = metricSlice.value === 'mileage' ? v.mileage || 0 : 1
    map.set(bucket, (map.get(bucket) || 0) + add)
  }
  const arr = Array.from(map.entries()).map(([name, value]) => ({ name, value }))
  arr.sort((a, b) => {
    if (a.name === '未登记') return 1
    if (b.name === '未登记') return -1
    const na = Number.parseInt(a.name, 10)
    const nb = Number.parseInt(b.name, 10)
    /* 年份倒序：新在上；「未登记」仍排在最后 */
    if (Number.isFinite(na) && Number.isFinite(nb)) return nb - na
    return a.name.localeCompare(b.name, 'zh-CN')
  })
  return arr
})

const orgUnitMax = computed(() => Math.max(...orgUnitStats.value.map((x) => x.value), 1))
const brandMax = computed(() => Math.max(...brandStats.value.map((x) => x.value), 1))
const seatMax = computed(() => Math.max(...seatStats.value.map((x) => x.value), 1))
const registrationYearChartMax = computed(() =>
  Math.max(...registrationYearChart.value.map((x) => x.value), 1),
)

const vehicleTypeLabelMax = computed(() =>
  Math.max(...vehicleTypeLabelStats.value.map((x) => x.value), 1),
)

/** 当前筛选下，该类型在「台数合计」或「里程合计」中的占比 */
function formatVehicleTypeShare(segmentValue: number) {
  if (metricSlice.value === 'mileage') {
    const t = kpi.value.totalMileage
    if (t <= 0) return '—'
    return `${((segmentValue / t) * 100).toLocaleString('zh-CN', { maximumFractionDigits: 1 })}%`
  }
  const n = filteredRows.value.length
  if (n <= 0) return '—'
  return `${((segmentValue / n) * 100).toLocaleString('zh-CN', { maximumFractionDigits: 1 })}%`
}

/** 条形图「车间」桶名与顶部筛选 filterOrgUnit 的取值对齐 */
function orgChartKeyToFilter(chartName: string): string {
  return chartName === '未分配车间' ? EMPTY_OPT : chartName
}

function scrollChartFilterToTable() {
  void nextTick(() => {
    tblWrapRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function onOrgUnitBarClick(x: StatItem) {
  const key = orgChartKeyToFilter(x.name)
  filterOrgUnit.value = filterOrgUnit.value === key ? 'all' : key
  closeOrgUnitCombo()
  scrollChartFilterToTable()
}

function onBrandBarClick(x: StatItem) {
  const key = x.name === '未知品牌' ? EMPTY_OPT : x.name
  filterBrand.value = filterBrand.value === key ? 'all' : key
  scrollChartFilterToTable()
}

function onYearBarClick(row: StatItem) {
  const key = row.name === '未登记' ? NO_YEAR_OPT : row.name
  filterYear.value = filterYear.value === key ? 'all' : key
  scrollChartFilterToTable()
}

function onSeatBarClick(x: StatItem) {
  filterSeats.value = filterSeats.value === x.name ? 'all' : x.name
  scrollChartFilterToTable()
}

function onVehicleTypeBarClick(x: StatItem) {
  filterVehicleTypeLabel.value = filterVehicleTypeLabel.value === x.name ? 'all' : x.name
  scrollChartFilterToTable()
}

function orgUnitBarActive(x: StatItem) {
  return filterOrgUnit.value === orgChartKeyToFilter(x.name)
}

function brandBarActive(x: StatItem) {
  const key = x.name === '未知品牌' ? EMPTY_OPT : x.name
  return filterBrand.value === key
}

function yearBarActive(row: StatItem) {
  const key = row.name === '未登记' ? NO_YEAR_OPT : row.name
  return filterYear.value === key
}

function seatBarActive(x: StatItem) {
  return filterSeats.value === x.name
}

function vehicleTypeBarActive(x: StatItem) {
  return filterVehicleTypeLabel.value === x.name
}

/** 暖色主题条形渐变，与全局陶土/橄榄/沙色体系一致，按行索引循环 */
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

function chartBarFillStyle(value: number, max: number, idx: number): Record<string, string> {
  const m = max > 0 ? max : 1
  const pct = (value / m) * 100
  return { width: `${pct}%`, ...barFillStyle(idx) }
}

function formatNum(v: number) {
  return Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
}

function formatMetricValue(v: number) {
  return metricSlice.value === 'mileage' ? `${formatNum(v)} km` : `${formatNum(v)} 台`
}

async function reload() {
  loading.value = true
  msg.value = ''
  try {
    rows.value = await api.listVehicles({ limit: 200 })
  } catch {
    msg.value = '加载车辆列表失败'
  } finally {
    loading.value = false
  }
}

function toDateInputValue(iso: string | null | undefined) {
  return registeredAtCalendarKey(iso ?? '') ?? ''
}

function resetForm() {
  form.plate_number = ''
  formWorkshopId.value = 0
  form.vehicle_class = ''
  form.vehicle_type_label = ''
  form.brand = ''
  form.model = ''
  form.emission_std = ''
  form.displacement = ''
  form.registered_at = ''
  form.vin = ''
  form.color = ''
  form.seats = 5
  form.mileage = 0
  form.status = 'active'
  form.remarks = ''
}

function openCreate() {
  editingId.value = null
  modalTitle.value = '新增车辆'
  resetForm()
  modalOpen.value = true
}

function resolveFormWorkshopId(v: Vehicle): number {
  if (v.workshop_id) return v.workshop_id
  const name = (v.org_unit ?? '').trim()
  if (!name) return 0
  return workshopsMaster.value.find((w) => w.name === name)?.id ?? 0
}

function syncFormWorkshopId(): number | null {
  return formWorkshopId.value > 0 ? formWorkshopId.value : null
}

function openEdit(v: Vehicle) {
  editingId.value = v.id
  modalTitle.value = '编辑车辆'
  form.plate_number = v.plate_number
  formWorkshopId.value = resolveFormWorkshopId(v)
  form.vehicle_class = v.vehicle_class || ''
  form.vehicle_type_label = v.vehicle_type_label || ''
  form.brand = v.brand
  form.model = v.model
  form.emission_std = v.emission_std || ''
  form.displacement = v.displacement || ''
  form.registered_at = toDateInputValue(resolveRegisteredAt(v))
  form.vin = v.vin || ''
  form.color = v.color
  form.seats = v.seats
  form.mileage = v.mileage
  form.status = v.status
  form.remarks = v.remarks || ''
  modalOpen.value = true
}

async function save() {
  saving.value = true
  msg.value = ''
  try {
    const reg = form.registered_at.trim()
    const workshopId = syncFormWorkshopId()
    if (!workshopId) {
      msg.value = '请选择使用单位'
      saving.value = false
      return
    }
    const payload: Record<string, unknown> = {
      plate_number: form.plate_number,
      workshop_id: workshopId,
      vehicle_class: form.vehicle_class,
      vehicle_type_label: form.vehicle_type_label,
      brand: form.brand,
      model: form.model,
      emission_std: form.emission_std,
      displacement: form.displacement,
      registered_at: reg || null,
      vin: form.vin || null,
      color: form.color,
      seats: form.seats,
      mileage: form.mileage,
      status: form.status,
      remarks: form.remarks || null,
    }
    if (editingId.value) {
      await api.updateVehicle(editingId.value, {
        plate_number: form.plate_number,
        workshop_id: workshopId,
        vehicle_class: form.vehicle_class,
        vehicle_type_label: form.vehicle_type_label,
        brand: form.brand,
        model: form.model,
        emission_std: form.emission_std,
        displacement: form.displacement,
        registered_at: reg || null,
        vin: form.vin || null,
        color: form.color,
        seats: form.seats,
        mileage: form.mileage,
        status: form.status,
        remarks: form.remarks || null,
      })
    } else {
      await api.createVehicle(payload as { plate_number: string })
    }
    modalOpen.value = false
    await reload()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '保存失败') : '保存失败'
  } finally {
    saving.value = false
  }
}

async function onDelete(v: Vehicle) {
  if (!confirm(`确定删除车辆 ${v.plate_number} ？`)) return
  msg.value = ''
  try {
    await api.deleteVehicle(v.id)
    await reload()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '删除失败') : '删除失败'
  }
}

onMounted(async () => {
  try {
    workshopsMaster.value = await fetchWorkshops()
  } catch {
    msg.value = '加载车间列表失败'
  }
  await reload()
  document.addEventListener('pointerdown', onOrgUnitDocPointerDown, true)
})
onUnmounted(() => {
  document.removeEventListener('pointerdown', onOrgUnitDocPointerDown, true)
})
</script>

<style scoped>
.vehicles-view {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.q {
  flex: 1;
  min-width: 220px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--cl-ring-warm);
  background: var(--cl-white);
  color: var(--cl-near-black);
  box-shadow:
    inset 0 1px 2px rgba(20, 20, 19, 0.05),
    0 1px 2px rgba(20, 20, 19, 0.06);
}

.q::placeholder {
  color: var(--cl-stone);
}

.q:hover {
  border-color: var(--cl-warm-silver);
}

.q:focus {
  outline: none;
  border-color: var(--cl-terracotta);
  box-shadow:
    inset 0 1px 2px rgba(20, 20, 19, 0.04),
    0 0 0 2px rgba(201, 100, 66, 0.22);
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

.panel {
  margin-bottom: 14px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
}

.panel-hd {
  padding: 12px 14px;
  border-bottom: 1px solid var(--cl-border-cream);
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 1.03rem;
}

.panel-hd--split {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: nowrap;
  min-width: 0;
}

.panel-hd--split > div:first-child {
  flex-shrink: 0;
}

/* 使用单位下拉展开时避免被 .filters 横向滚动容器裁切 */
.panel-hd--filters-open .filters {
  overflow: visible;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  flex: 1;
  min-width: 0;
  justify-content: flex-end;
  overflow-x: auto;
  overflow-y: visible;
  -webkit-overflow-scrolling: touch;
  padding-bottom: 4px;
  scrollbar-gutter: stable;
}

.filters::-webkit-scrollbar {
  height: 6px;
}

.filters::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(77, 76, 72, 0.28);
}

.sel {
  flex-shrink: 0;
  min-width: 118px;
  max-width: 200px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 13px;
}

.sel-combo {
  position: relative;
  flex-shrink: 0;
  min-width: 118px;
  max-width: 200px;
}

.sel-combo__btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  box-sizing: border-box;
  cursor: pointer;
  font: inherit;
  color: inherit;
  text-align: left;
}

.sel-combo__btn-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sel-combo__caret {
  flex-shrink: 0;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid var(--cl-charcoal);
  opacity: 0.55;
}

.sel-combo--open .sel-combo__btn {
  border-color: var(--cl-warm-silver);
  box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.12);
}

.sel-combo__panel {
  position: absolute;
  left: 0;
  top: calc(100% + 4px);
  z-index: 50;
  min-width: 240px;
  max-width: min(380px, 92vw);
  padding: 8px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 10px;
  background: var(--cl-white);
  box-shadow: 0 10px 32px rgba(20, 20, 19, 0.14);
}

.sel-combo__search {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  font-size: 13px;
  color: var(--cl-near-black);
}

.sel-combo__search:focus {
  outline: none;
  border-color: var(--cl-warm-silver);
}

.sel-combo__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 260px;
  overflow-y: auto;
}

.sel-combo__opt {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  line-height: 1.35;
  word-break: break-all;
}

.sel-combo__opt:hover {
  background: var(--cl-warm-sand);
}

.sel-combo__hint {
  padding: 10px 8px;
  font-size: 12px;
  color: var(--cl-olive);
  text-align: center;
}

.empty-hint {
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
  padding: 28px 16px !important;
}

.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 12px 14px;
}

.mini {
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  background: var(--cl-white);
  padding: 10px 12px;
}

.mk {
  font-size: 12px;
  color: var(--cl-olive);
}

.mv {
  margin-top: 4px;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 1.08rem;
}

.charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 0 14px 16px;
  align-items: stretch;
  align-content: start;
}

.chart {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 12px;
  padding: 12px 12px 10px;
  min-width: 0;
}

.chart--wide {
  grid-column: 1 / -1;
}

.chart--wide .bar-row {
  grid-template-columns: minmax(72px, 110px) minmax(0, 1fr) minmax(108px, 132px);
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

.bars--scroll {
  max-height: 196px;
  overflow-y: auto;
  padding-right: 4px;
}

.chart-note {
  font-size: 11px;
  color: var(--cl-stone);
  margin: -4px 0 8px;
  line-height: 1.4;
}

.bar-value--share {
  font-size: 11px;
  white-space: nowrap;
}

.bars--empty {
  min-height: 72px;
  display: flex;
  align-items: center;
}

.bars--empty .empty-hint {
  margin: 0;
}

/*
 * 769px 起保持双列（不再在 1100px 以下强制单列），行高随内容伸缩，
 * 避免固定 grid 高度 + 1fr 行把卡片压扁、条形区被「挤在一起」。
 */
@media (min-width: 769px) {
  .charts {
    grid-template-rows: auto auto auto;
    height: auto;
    min-height: 0;
  }

  .chart--wide {
    flex: 0 0 auto;
  }

  .chart--wide .bars--scroll {
    flex: 0 1 auto;
    max-height: min(300px, 38vh);
  }

  .chart {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }

  .chart .ct {
    flex-shrink: 0;
  }

  .chart .bars--scroll {
    flex: 0 1 auto;
    min-height: 140px;
    max-height: min(280px, 36vh);
  }
}

.bar-row {
  display: grid;
  grid-template-columns: minmax(88px, 32%) minmax(0, 1fr) minmax(76px, 88px);
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
  outline: 2px solid var(--cl-terracotta);
  outline-offset: 1px;
}

.bar-row--active {
  background: rgba(201, 100, 66, 0.1);
  box-shadow: inset 0 0 0 1px rgba(201, 100, 66, 0.22);
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
}

.tbl-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-top: 0;
  min-width: 0;
}

.tbl-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px 16px;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  background: var(--cl-ivory);
}

.tbl-pager__meta {
  font-size: 13px;
  color: var(--cl-charcoal);
  text-align: center;
  line-height: 1.4;
}

.tbl-pager__btn {
  min-width: 88px;
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
  min-width: 960px;
}

.vehicle-cards-mobile {
  display: none;
}

.vehicle-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.vehicle-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  background: var(--cl-ivory);
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.04) 0 4px 16px;
}

.vehicle-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.vehicle-card__plate {
  font-size: 1.08rem;
  font-weight: 900;
  color: var(--cl-near-black);
  letter-spacing: 0.02em;
}

.vehicle-card__pill {
  flex-shrink: 0;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  font-size: 12px;
  font-weight: 700;
  color: var(--cl-olive);
}

.vehicle-card__unit {
  font-size: 13px;
  color: var(--cl-charcoal);
  line-height: 1.4;
  margin-bottom: 12px;
  word-break: break-word;
}

.vehicle-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
}

.vehicle-card__row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  min-width: 0;
}

.vehicle-card__k {
  font-size: 11px;
  font-weight: 700;
  color: var(--cl-olive);
}

.vehicle-card__v {
  color: var(--cl-near-black);
  word-break: break-word;
  line-height: 1.35;
}

.vehicle-card__spec {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
}

.vehicle-card__spec-text {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--cl-charcoal);
  word-break: break-word;
}

.vehicle-card__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--cl-border-cream);
}

.vehicle-card__btn {
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

.vehicle-card__btn--danger {
  color: var(--cl-error);
  border-color: rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.06);
}

.vehicle-cards-mobile__empty {
  margin: 0;
  padding: 24px 12px !important;
}

th,
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--cl-border-cream);
  text-align: left;
}

th {
  color: var(--cl-olive);
  font-weight: 800;
  background: var(--cl-warm-sand);
}

.strong {
  font-weight: 900;
}

.t {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-unit {
  min-width: 112px;
  max-width: 200px;
}

.col-plate {
  white-space: nowrap;
}

.col-type {
  min-width: 96px;
  max-width: 160px;
}

.col-brand {
  min-width: 96px;
  max-width: 140px;
}

.col-spec {
  min-width: 160px;
  max-width: 280px;
}

.col-narrow {
  white-space: nowrap;
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
  grid-template-columns: minmax(140px, 168px) 1fr;
  gap: 10px 12px;
  align-items: center;
}

label {
  color: var(--cl-charcoal);
  font-size: 12px;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  color: var(--cl-near-black);
}

textarea {
  resize: vertical;
}

@media (max-width: 1100px) {
  .kpis {
    grid-template-columns: 1fr;
    grid-template-rows: none;
    height: auto;
    min-height: 0;
  }
}

/* 仅窄屏单列图表；平板/小笔记本宽度仍可两列并排 */
@media (max-width: 768px) {
  .charts {
    grid-template-columns: 1fr;
    grid-template-rows: none;
    height: auto;
    min-height: 0;
    gap: 12px;
  }
}

/* 手机 / 小平板：筛选区纵向排列；去掉横向滚动与父级裁切，避免原生 select 无法弹出、自定义下拉被截断 */
@media (max-width: 768px) {
  .primary,
  .ghost {
    min-height: 44px;
    touch-action: manipulation;
  }

  .panel.analytics {
    overflow: visible;
  }

  .panel-hd {
    position: relative;
    z-index: 6;
  }

  .panel-hd--split {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .panel-hd--split > div:first-child {
    flex-shrink: 1;
  }

  .filters {
    display: grid;
    /* 表格式多列：窄屏也尽量并排，避免一长串各占一行 */
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 10px;
    row-gap: 10px;
    flex: none;
    width: 100%;
    min-width: 0;
    overflow-x: visible;
    overflow-y: visible;
    align-items: stretch;
    padding-bottom: 0;
    scrollbar-gutter: auto;
    -webkit-overflow-scrolling: auto;
  }

  .sel,
  .sel-combo {
    flex: none;
    width: 100%;
    max-width: none;
    min-width: 0;
  }

  /* 略宽手机 / 小平板：三列，进一步压缩纵向高度 */
  @media (min-width: 420px) {
    .filters {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  .sel {
    min-height: 48px;
    font-size: 16px;
    padding: 10px 12px;
    touch-action: manipulation;
    -webkit-tap-highlight-color: rgba(20, 20, 19, 0.06);
    /* 避免部分 WebView 把 select 画成不可点状态 */
    appearance: auto;
    -webkit-appearance: menulist;
  }

  .sel-combo__btn {
    min-height: 48px;
    padding: 10px 12px;
    font-size: 16px;
    touch-action: manipulation;
    -webkit-tap-highlight-color: rgba(20, 20, 19, 0.06);
  }

  .sel-combo__panel {
    z-index: 400;
    width: min(420px, calc(100vw - 32px));
    left: 50%;
    transform: translateX(-50%);
  }

  .sel-combo__search {
    font-size: 16px;
  }

  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    padding: 10px 12px;
  }

  .mini {
    padding: 8px 10px;
  }

  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar .q {
    min-width: 0;
    width: 100%;
    flex: none;
    font-size: 16px;
  }

  .toolbar .primary,
  .toolbar .ghost {
    width: 100%;
  }

  .tbl-wrap {
    overflow-x: visible;
  }

  .tbl--desktop {
    display: none;
  }

  .vehicle-cards-mobile {
    display: block;
  }

  .form--vehicles {
    grid-template-columns: 1fr;
    gap: 8px 0;
  }

  .form--vehicles label {
    margin-top: 4px;
    font-weight: 700;
  }

  .form--vehicles input,
  .form--vehicles select,
  .form--vehicles textarea {
    font-size: 16px;
  }
}
</style>
