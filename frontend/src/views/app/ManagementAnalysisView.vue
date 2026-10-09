<template>
  <div class="analysis-page">
    <header class="analysis-header">
      <button type="button" class="back-btn" aria-label="返回管理页面" @click="goBack">
        <span aria-hidden="true">←</span>
        <span>返回</span>
      </button>
      <div class="analysis-header__title">
        <h1>运营数据分析</h1>
        <p>{{ activeMeta.description }}</p>
      </div>
      <button type="button" class="refresh-btn" :disabled="activeLoading" @click="refreshActive">
        {{ activeLoading ? '加载中' : '刷新' }}
      </button>
    </header>

    <nav class="scope-tabs" aria-label="分析对象">
      <RouterLink
        v-for="item in scopes"
        :key="item.id"
        class="scope-tab"
        :class="{ 'is-active': scope === item.id }"
        :to="{ name: 'managementAnalysis', query: { scope: item.id } }"
      >
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div v-if="activeError" class="analysis-state analysis-state--error">
      <strong>数据加载失败</strong>
      <span>{{ activeError }}</span>
      <button type="button" @click="refreshActive">重新加载</button>
    </div>
    <div v-else-if="activeLoading && !activeLoaded" class="analysis-state">
      <span class="loading-dot" aria-hidden="true" />
      <span>正在整理分析数据…</span>
    </div>

    <template v-else-if="scope === 'vehicles'">
      <section class="kpi-grid kpi-grid--single" aria-label="车辆关键指标">
        <article class="kpi-card kpi-card--accent">
          <span>车辆总数</span>
          <strong>{{ vehicleRows.length }}<small> 台</small></strong>
          <p>当前账号可访问车辆</p>
        </article>
      </section>

      <section class="content-grid">
        <article class="data-card data-card--wide">
          <div class="data-card__head">
            <div><h2>使用单位分布</h2><p>按车辆数量排序，显示主要使用单位</p></div>
            <span>{{ vehicleOrgStats.length }} 个单位</span>
          </div>
          <div class="rank-bars rank-bars--scroll">
            <div v-for="(item, index) in vehicleOrgStats" :key="item.name" class="rank-row">
              <span class="rank-row__index">{{ index + 1 }}</span>
              <span class="rank-row__label" :title="item.name">{{ item.name }}</span>
              <span class="rank-row__track"><span :style="barStyle(item.value, vehicleOrgMax, index)" /></span>
              <strong>{{ item.value }} 台</strong>
            </div>
            <p v-if="!vehicleOrgStats.length" class="empty-copy">暂无使用单位数据</p>
          </div>
        </article>

        <article class="data-card">
          <div class="data-card__head"><div><h2>车辆类型</h2><p>不同车辆类型的数量对比</p></div></div>
          <div class="compact-bars">
            <div v-for="(item, index) in vehicleTypeStats" :key="item.name" class="compact-bar">
              <div><span :title="item.name">{{ item.name }}</span><strong>{{ item.value }}</strong></div>
              <span class="compact-bar__track"><span :style="barStyle(item.value, vehicleTypeMax, index)" /></span>
            </div>
            <p v-if="!vehicleTypeStats.length" class="empty-copy">暂无车辆类型数据</p>
          </div>
        </article>

        <article class="data-card data-card--wide">
          <div class="data-card__head"><div><h2>注册年份</h2><p>按机动车注册登记年份观察车辆结构</p></div></div>
          <div class="year-strip">
            <div v-for="(item, index) in vehicleYearStats" :key="item.name" class="year-item">
              <strong>{{ item.value }}</strong>
              <span class="year-item__bar"><span :style="verticalBarStyle(item.value, vehicleYearMax, index)" /></span>
              <small>{{ item.name }}</small>
            </div>
            <p v-if="!vehicleYearStats.length" class="empty-copy">暂无登记年份数据</p>
          </div>
        </article>
      </section>
    </template>

    <template v-else-if="scope === 'drivers'">
      <section class="kpi-grid" aria-label="驾驶员关键指标">
        <article class="kpi-card kpi-card--accent"><span>驾驶员总数</span><strong>{{ driverStats?.total ?? 0 }}<small> 人</small></strong></article>
        <article class="kpi-card"><span>覆盖车间</span><strong>{{ driverWorkshopStats.length }}<small> 个</small></strong></article>
        <article class="kpi-card"><span>本单位</span><strong>{{ driverLocalCount }}<small> 人</small></strong><p>占比 {{ percent(driverLocalCount, driverStats?.total ?? 0) }}</p></article>
        <article class="kpi-card"><span>外包人员</span><strong>{{ driverOutsourceCount }}<small> 人</small></strong><p>占比 {{ percent(driverOutsourceCount, driverStats?.total ?? 0) }}</p></article>
      </section>

      <section class="content-grid">
        <article class="data-card data-card--wide">
          <div class="data-card__head"><div><h2>车间人员分布</h2><p>按驾驶员数量从高到低排列</p></div><span>{{ driverWorkshopStats.length }} 个车间</span></div>
          <div class="rank-bars">
            <div v-for="(item, index) in driverWorkshopStats" :key="item.name" class="rank-row">
              <span class="rank-row__index">{{ index + 1 }}</span><span class="rank-row__label" :title="item.name">{{ item.name }}</span>
              <span class="rank-row__track"><span :style="barStyle(item.value, driverWorkshopMax, index)" /></span><strong>{{ item.value }} 人</strong>
            </div>
          </div>
        </article>

        <article class="data-card">
          <div class="data-card__head"><div><h2>准驾车型</h2><p>人员资质结构</p></div></div>
          <div class="compact-bars">
            <div v-for="(item, index) in driverLicenseStats" :key="item.name" class="compact-bar">
              <div><span>{{ item.name }}</span><strong>{{ item.value }} 人</strong></div>
              <span class="compact-bar__track"><span :style="barStyle(item.value, driverLicenseMax, index)" /></span>
            </div>
            <p v-if="!driverLicenseStats.length" class="empty-copy">暂无准驾车型数据</p>
          </div>
        </article>

        <article class="data-card">
          <div class="data-card__head"><div><h2>用工属性</h2><p>本单位与外包人员构成</p></div></div>
          <div class="segment-list">
            <div v-for="(item, index) in driverEmploymentStats" :key="item.name" class="segment-item">
              <span class="segment-item__dot" :style="dotStyle(index)" /><span>{{ item.name }}</span><strong>{{ item.value }} 人</strong>
              <small>{{ percent(item.value, driverStats?.total ?? 0) }}</small>
            </div>
          </div>
        </article>

        <article class="data-card data-card--wide">
          <div class="data-card__head"><div><h2>年龄结构</h2><p>按周岁年龄区间统计，无法识别的数据单独显示</p></div></div>
          <div class="age-grid">
            <div v-for="(item, index) in driverAgeStats" :key="item.name" class="age-item">
              <span>{{ item.name }}</span><strong>{{ item.value }} 人</strong>
              <span class="age-item__track"><span :style="barStyle(item.value, driverAgeMax, index)" /></span>
            </div>
          </div>
        </article>
      </section>
    </template>

    <template v-else>
      <section class="kpi-grid kpi-grid--two" aria-label="油卡关键指标">
        <article class="kpi-card kpi-card--accent"><span>油卡总数</span><strong>{{ fuelTotal }}<small> 张</small></strong><p>当前余额数据中的油卡</p></article>
        <article class="kpi-card"><span>余额合计</span><strong>{{ compactMoney(fuelTotalAmount) }}</strong><p>金额与备用金合计</p></article>
      </section>

      <section class="content-grid">
        <article class="data-card data-card--wide fuel-workshop-card">
          <div class="data-card__head">
            <div><h2>车间余额对比</h2><p>按车间油卡余额合计排序</p></div>
            <span>{{ fuelWorkshopStats.length }} 个车间</span>
          </div>
          <div class="compact-bars compact-bars--scroll fuel-workshop-list">
            <div v-for="(item, index) in fuelWorkshopStats" :key="item.name" class="compact-bar fuel-workshop-row">
              <div class="fuel-workshop-row__meta">
                <span :title="item.name">{{ item.name }}</span>
                <strong :title="compactMoney(item.value)">{{ compactMoney(item.value) }}</strong>
              </div>
              <span class="compact-bar__track"><span :style="barStyle(item.value, fuelWorkshopMax, index)" /></span>
            </div>
            <p v-if="!fuelWorkshopStats.length" class="empty-copy">暂无车间余额数据</p>
          </div>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import * as driverApi from '@/api/drivers'
import * as fuelApi from '@/api/fuel'
import * as vehicleApi from '@/api/vehicles'
import type { DriverStats } from '@/api/drivers'
import type { FuelBalance } from '@/api/fuel'
import type { Vehicle } from '@/api/types'

type ScopeId = 'vehicles' | 'drivers' | 'fuel'
type StatItem = { name: string; value: number; amount?: number }

const route = useRoute()
const router = useRouter()
const scopes = [
  { id: 'vehicles' as const, label: '车辆', description: '车队规模、状态、类型与车龄结构' },
  { id: 'drivers' as const, label: '驾驶员', description: '人员分布、资质、用工属性与年龄结构' },
  { id: 'fuel' as const, label: '油卡', description: '余额规模、有效区间、车间分布与高余额卡片' },
]

const scope = computed<ScopeId>(() => {
  const raw = String(route.query.scope || 'vehicles')
  return raw === 'drivers' || raw === 'fuel' ? raw : 'vehicles'
})
const activeMeta = computed(() => scopes.find((item) => item.id === scope.value) ?? scopes[0])
const loaded = reactive<Record<ScopeId, boolean>>({ vehicles: false, drivers: false, fuel: false })
const loading = reactive<Record<ScopeId, boolean>>({ vehicles: false, drivers: false, fuel: false })
const errors = reactive<Record<ScopeId, string>>({ vehicles: '', drivers: '', fuel: '' })
const activeLoaded = computed(() => loaded[scope.value])
const activeLoading = computed(() => loading[scope.value])
const activeError = computed(() => errors[scope.value])

const vehicleRows = ref<Vehicle[]>([])
const driverStats = ref<DriverStats | null>(null)
const fuelRows = ref<FuelBalance[]>([])
const fuelTotal = ref(0)
const fuelTotalAmount = ref(0)

const PALETTE = ['#c96442', '#9a7340', '#d68462', '#6f7564', '#b58a5a', '#75584c', '#c7a15b']

function groupCount(values: string[]): StatItem[] {
  const map = new Map<string, number>()
  for (const raw of values) {
    const name = raw.trim() || '未填写'
    map.set(name, (map.get(name) ?? 0) + 1)
  }
  return [...map.entries()].map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, 'zh-CN'))
}

function recordStats(source: Record<string, number>, order?: string[]): StatItem[] {
  const rows = Object.entries(source).map(([name, value]) => ({ name, value: Number(value) || 0 })).filter((item) => item.value > 0)
  if (!order) return rows.sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, 'zh-CN'))
  return rows.sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name))
}

function maxOf(items: StatItem[]) {
  return Math.max(1, ...items.map((item) => item.value))
}

function barStyle(value: number, max: number, index: number) {
  return { width: `${value > 0 ? Math.max(3, (value / Math.max(1, max)) * 100) : 0}%`, background: PALETTE[index % PALETTE.length] }
}

function dotStyle(index: number) {
  return { background: PALETTE[index % PALETTE.length] }
}

function verticalBarStyle(value: number, max: number, index: number) {
  return {
    height: `${value > 0 ? Math.max(4, (value / Math.max(1, max)) * 100) : 0}%`,
    background: PALETTE[index % PALETTE.length],
  }
}

function percent(value: number, total: number) {
  return total > 0 ? `${((value / total) * 100).toFixed(1)}%` : '0%'
}

function compactMoney(value: number) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const vehicleOrgStats = computed(() => groupCount(vehicleRows.value.map((row) => row.org_unit)))
const vehicleTypeStats = computed(() => groupCount(vehicleRows.value.map((row) => row.vehicle_type_label || row.vehicle_class)).slice(0, 8))
const vehicleYearStats = computed(() => {
  const stats = groupCount(vehicleRows.value.map((row) => {
    if (!row.registered_at) return '未登记'
    const year = new Date(row.registered_at).getFullYear()
    return Number.isFinite(year) ? String(year) : '未登记'
  }))
  return stats.sort((a, b) => a.name === '未登记' ? 1 : b.name === '未登记' ? -1 : Number(a.name) - Number(b.name))
})
const vehicleOrgMax = computed(() => maxOf(vehicleOrgStats.value))
const vehicleTypeMax = computed(() => maxOf(vehicleTypeStats.value))
const vehicleYearMax = computed(() => maxOf(vehicleYearStats.value))

const driverWorkshopStats = computed(() => recordStats(driverStats.value?.by_workshop ?? {}))
const driverLicenseStats = computed(() => recordStats(driverStats.value?.by_license_type ?? {}))
const driverEmploymentStats = computed(() => recordStats(driverStats.value?.by_employment_status ?? {}, ['本单位', '外包']))
const driverAgeStats = computed(() => recordStats(driverStats.value?.by_age_group ?? {}, ['29岁及以下', '30–39岁', '40–49岁', '50–59岁', '60岁及以上', '未知']))
const driverLocalCount = computed(() => Number(driverStats.value?.by_employment_status['本单位']) || 0)
const driverOutsourceCount = computed(() => Number(driverStats.value?.by_employment_status['外包']) || 0)
const driverWorkshopMax = computed(() => maxOf(driverWorkshopStats.value))
const driverLicenseMax = computed(() => maxOf(driverLicenseStats.value))
const driverAgeMax = computed(() => maxOf(driverAgeStats.value))

const fuelWorkshopStats = computed(() => {
  const map = new Map<string, number>()
  for (const row of fuelRows.value) {
    const name = displayWorkshop(row.workshop)
    map.set(name, (map.get(name) ?? 0) + Number(row.total || 0))
  }
  return [...map.entries()].map(([name, value]) => ({ name, value })).filter((item) => item.value > 0).sort((a, b) => b.value - a.value)
})
const fuelWorkshopMax = computed(() => maxOf(fuelWorkshopStats.value))

function displayWorkshop(raw: string) {
  return raw === '/' ? '未分配车间' : raw.trim() || '未分配车间'
}

async function loadFuelAnalysis() {
  const rows: FuelBalance[] = []
  let page = 1
  let total = 0
  do {
    const result = await fuelApi.listFuelBalancesPaged({ page, page_size: 100, sort_by: 'total', sort_dir: 'desc' })
    if (page === 1) {
      total = result.total
      fuelTotal.value = result.total
      fuelTotalAmount.value = Number(result.total_amount || 0)
    }
    rows.push(...result.items)
    if (!result.items.length) break
    page += 1
  } while (rows.length < total)
  fuelRows.value = rows
}

async function loadScope(target: ScopeId, force = false) {
  if (loading[target] || (loaded[target] && !force)) return
  loading[target] = true
  errors[target] = ''
  try {
    if (target === 'vehicles') vehicleRows.value = await vehicleApi.listAllVehicles()
    else if (target === 'drivers') driverStats.value = await driverApi.getDriverStats()
    else await loadFuelAnalysis()
    loaded[target] = true
  } catch {
    errors[target] = '请检查网络或登录状态后重试。'
  } finally {
    loading[target] = false
  }
}

function refreshActive() {
  void loadScope(scope.value, true)
}

function goBack() {
  const target = scope.value === 'vehicles' ? '/app/vehicles' : scope.value === 'drivers' ? '/app/drivers' : '/app/fuel'
  void router.push(target)
}

watch(scope, (value) => void loadScope(value), { immediate: true })
onMounted(() => void loadScope(scope.value))
</script>

<style scoped>
.analysis-page { width: 100%; max-width: 1180px; min-width: 0; margin: 0 auto; padding: 0 0 24px; box-sizing: border-box; color: var(--cl-near-black); }
.analysis-header { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 14px; margin-bottom: 12px; padding: 14px 16px; border: 1px solid rgba(201, 100, 66, .18); border-radius: 18px; background: radial-gradient(circle at 92% 0, rgba(201, 100, 66, .13), transparent 38%), var(--cl-ivory); }
.analysis-header__title { min-width: 0; }
.analysis-header h1 { margin: 0; font: 700 1.15rem/1.25 Georgia, 'Songti SC', serif; }
.analysis-header p { margin: 3px 0 0; color: var(--cl-olive); font-size: 12px; }
.back-btn, .refresh-btn { min-height: 40px; padding: 8px 12px; border: 1px solid var(--cl-border-cream); border-radius: 11px; background: var(--cl-white); color: var(--cl-near-black); font: inherit; cursor: pointer; }
.back-btn { display: inline-flex; align-items: center; gap: 5px; }
.refresh-btn:disabled { opacity: .55; cursor: default; }
.scope-tabs { position: sticky; top: 0; z-index: 5; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-bottom: 12px; padding: 5px; border: 1px solid var(--cl-border-cream); border-radius: 14px; background: rgba(255, 253, 249, .94); backdrop-filter: blur(10px); }
.scope-tab { display: flex; align-items: center; justify-content: center; gap: 7px; min-width: 0; min-height: 42px; border-radius: 10px; color: var(--cl-charcoal); text-decoration: none; font-size: 14px; font-weight: 700; }
.scope-tab.is-active { color: var(--cl-brand); background: rgba(201, 100, 66, .1); box-shadow: inset 0 0 0 1px rgba(201, 100, 66, .18); }
.kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; }
.kpi-grid--single { grid-template-columns: minmax(220px, 300px); }
.kpi-grid--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.kpi-card { min-width: 0; padding: 14px; border: 1px solid var(--cl-border-cream); border-radius: 15px; background: var(--cl-white); box-shadow: 0 4px 18px rgba(50, 44, 38, .04); }
.kpi-card--accent { background: linear-gradient(145deg, rgba(201, 100, 66, .13), rgba(255, 253, 249, .98)); border-color: rgba(201, 100, 66, .25); }
.kpi-card > span { color: var(--cl-olive); font-size: 12px; }
.kpi-card strong { display: block; margin-top: 7px; font-size: clamp(1.2rem, 2.5vw, 1.65rem); line-height: 1; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.kpi-card small { font-size: 11px; font-weight: 600; color: var(--cl-charcoal); }
.kpi-card p { margin: 8px 0 0; color: var(--cl-olive); font-size: 11px; line-height: 1.35; }
.content-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.data-card { min-width: 0; padding: 14px; border: 1px solid var(--cl-border-cream); border-radius: 16px; background: var(--cl-white); box-shadow: 0 5px 22px rgba(50, 44, 38, .04); }
.data-card--wide { grid-column: 1 / -1; }
.data-card__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 13px; }
.data-card__head h2 { margin: 0; font-size: 14px; }
.data-card__head p { margin: 4px 0 0; color: var(--cl-olive); font-size: 11px; }
.data-card__head > span { flex: 0 0 auto; padding: 4px 7px; border-radius: 999px; background: var(--cl-warm-sand); color: var(--cl-olive); font-size: 10px; }
.rank-bars, .compact-bars, .segment-list, .record-list, .bucket-grid { display: flex; flex-direction: column; gap: 9px; }
.rank-bars--scroll,
.compact-bars--scroll {
  max-height: 360px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 5px;
  scrollbar-gutter: stable;
}
.rank-bars--scroll::-webkit-scrollbar,
.compact-bars--scroll::-webkit-scrollbar { width: 5px; }
.rank-bars--scroll::-webkit-scrollbar-thumb,
.compact-bars--scroll::-webkit-scrollbar-thumb { border-radius: 999px; background: rgba(107, 93, 75, .28); }
.fuel-workshop-card {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  box-sizing: border-box;
}
.fuel-workshop-list {
  width: 100%;
  max-width: 100%;
  max-height: clamp(280px, 48dvh, 480px);
  box-sizing: border-box;
}
.fuel-workshop-row {
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid rgba(232, 224, 212, .78);
  border-radius: 11px;
  background: rgba(255, 253, 249, .72);
  box-sizing: border-box;
}
.fuel-workshop-row__meta {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) minmax(min-content, 42%);
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.fuel-workshop-row__meta > span,
.fuel-workshop-row__meta > strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fuel-workshop-row__meta > strong {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.rank-row { display: grid; grid-template-columns: 24px minmax(80px, 160px) minmax(0, 1fr) 54px; align-items: center; gap: 8px; min-width: 0; }
.rank-row__index { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 7px; background: rgba(107, 93, 75, .08); color: var(--cl-olive); font-size: 10px; }
.rank-row__label, .compact-bar div span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.rank-row__track, .compact-bar__track, .bucket-item__track, .age-item__track { display: block; height: 9px; overflow: hidden; border-radius: 999px; background: rgba(107, 93, 75, .1); }
.rank-row__track > span, .compact-bar__track > span, .bucket-item__track > span, .age-item__track > span { display: block; height: 100%; border-radius: inherit; }
.rank-row > strong { text-align: right; font-size: 11px; white-space: nowrap; }
.segment-item { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto 48px; align-items: center; gap: 8px; padding: 10px; border-radius: 11px; background: rgba(239, 232, 215, .42); }
.segment-item__dot { width: 9px; height: 9px; border-radius: 50%; }
.segment-item span { font-size: 12px; }.segment-item strong { font-size: 12px; }.segment-item small { color: var(--cl-olive); text-align: right; }
.compact-bar div { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 5px; }.compact-bar div strong { flex: 0 0 auto; font-size: 11px; }
.year-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(68px, 1fr)); gap: 8px; align-items: end; }
.year-item { display: grid; grid-template-rows: auto 72px auto; justify-items: center; gap: 5px; min-width: 0; }
.year-item > strong { font-size: 12px; }.year-item small { color: var(--cl-olive); font-size: 10px; white-space: nowrap; }
.year-item__bar { display: flex; width: 12px; height: 72px; align-items: flex-end; overflow: hidden; border-radius: 999px; background: rgba(107, 93, 75, .1); }
.year-item__bar > span { width: 100%; min-height: 3px; border-radius: inherit; }
.age-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.age-item { min-width: 0; padding: 10px; border-radius: 11px; background: rgba(239, 232, 215, .42); }.age-item > span:first-child { display: block; color: var(--cl-olive); font-size: 11px; }.age-item strong { display: block; margin: 5px 0 8px; font-size: 14px; }
.bucket-item { padding: 10px; border: 1px solid rgba(232, 224, 212, .9); border-radius: 12px; }.bucket-item__top, .bucket-item__bottom { display: flex; justify-content: space-between; gap: 10px; }.bucket-item__top { margin-bottom: 7px; font-size: 12px; }.bucket-item__bottom { margin-top: 6px; color: var(--cl-olive); font-size: 10px; }
.record-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid rgba(232, 224, 212, .8); }.record-row:last-child { border-bottom: 0; }.record-row > div { min-width: 0; }.record-row div strong, .record-row div span { display: block; }.record-row div strong { font-size: 12px; }.record-row div span { margin-top: 2px; color: var(--cl-olive); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.record-row > strong { flex: 0 0 auto; font-size: 12px; font-variant-numeric: tabular-nums; }
.analysis-state { display: flex; min-height: 220px; align-items: center; justify-content: center; gap: 9px; border: 1px solid var(--cl-border-cream); border-radius: 16px; background: var(--cl-white); color: var(--cl-olive); }.analysis-state--error { flex-direction: column; }.analysis-state--error strong { color: var(--cl-near-black); }.analysis-state--error button { padding: 8px 12px; border: 0; border-radius: 9px; background: var(--cl-brand); color: white; }.loading-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--cl-brand); animation: pulse 1s ease-in-out infinite alternate; }.empty-copy { margin: 8px 0; color: var(--cl-olive); font-size: 12px; text-align: center; }
.kpi-card, .data-card {
  animation: analysis-card-in 280ms cubic-bezier(0.22, 1, 0.36, 1);
}
.scope-tab { transition: background-color 180ms ease, color 180ms ease; }
.rank-row__track > span, .compact-bar__track > span,
.bucket-item__track > span, .age-item__track > span {
  transform-origin: left center;
  animation: analysis-bar-in 420ms cubic-bezier(0.22, 1, 0.36, 1);
  transition: width 300ms cubic-bezier(0.22, 1, 0.36, 1);
}
.year-item__bar > span {
  transform-origin: center bottom;
  animation: analysis-column-in 420ms cubic-bezier(0.22, 1, 0.36, 1);
  transition: height 300ms ease;
}
@keyframes analysis-card-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes analysis-bar-in { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes analysis-column-in { from { transform: scaleY(0); } to { transform: scaleY(1); } }
@media (prefers-reduced-motion: reduce) {
  .kpi-card, .data-card, .loading-dot,
  .rank-row__track > span, .compact-bar__track > span,
  .bucket-item__track > span, .age-item__track > span, .year-item__bar > span {
    animation: none;
    transition: none;
  }
  .scope-tab { transition: none; }
}
@keyframes pulse { to { opacity: .25; transform: scale(.75); } }

@media (max-width: 768px) {
  .analysis-page { padding-bottom: calc(18px + env(safe-area-inset-bottom, 0px)); }
  .analysis-header { grid-template-columns: auto minmax(0, 1fr) auto; gap: 8px; margin-bottom: 8px; padding: 10px; border-radius: 14px; }
  .analysis-header__title p { display: none; }.analysis-header h1 { font-size: 15px; }.back-btn, .refresh-btn { min-height: 36px; padding: 6px 9px; font-size: 12px; }.back-btn span:last-child { display: none; }
  .scope-tabs { margin-bottom: 8px; border-radius: 12px; }.scope-tab { min-height: 40px; font-size: 13px; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; margin-bottom: 8px; }.kpi-card { padding: 11px; border-radius: 13px; }.kpi-card strong { font-size: 1.25rem; }.kpi-card p { margin-top: 6px; }
  .kpi-grid--single { grid-template-columns: minmax(0, 1fr); }
  .kpi-grid--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .content-grid { grid-template-columns: minmax(0, 1fr); gap: 8px; }.data-card, .data-card--wide { grid-column: auto; padding: 11px; border-radius: 14px; }.data-card__head { margin-bottom: 10px; }.data-card__head p { line-height: 1.35; }
  .rank-row { grid-template-columns: 22px minmax(72px, 104px) minmax(0, 1fr) 46px; gap: 6px; }.rank-row__label { font-size: 11px; }
  .age-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }.year-strip { display: flex; gap: 10px; overflow-x: auto; padding: 2px 1px 8px; }.year-item { flex: 0 0 58px; }
  .segment-item { padding: 9px; }.record-row { padding: 9px 1px; }
  .rank-bars--scroll,
  .compact-bars--scroll { max-height: 320px; }
  .fuel-workshop-card { padding: 10px; }
  .fuel-workshop-list {
    max-height: min(46dvh, 420px);
    padding-right: 3px;
  }
  .fuel-workshop-row {
    padding: 8px;
    border-radius: 10px;
  }
  .fuel-workshop-row__meta {
    grid-template-columns: minmax(0, 1fr) minmax(min-content, 48%);
    gap: 7px;
  }
}

@media (max-width: 390px) {
  .rank-row { grid-template-columns: 20px minmax(64px, 84px) minmax(0, 1fr) 43px; }.kpi-card { padding: 10px; }.kpi-card p { font-size: 10px; }
  .fuel-workshop-row__meta { grid-template-columns: minmax(0, 1fr) minmax(min-content, 52%); }
  .fuel-workshop-row__meta > strong { font-size: 10px; }
}
</style>
