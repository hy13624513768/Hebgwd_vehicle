<template>
  <div>
    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <template v-else-if="data">
      <section class="dashboard-overview" aria-label="车辆与驾驶员汇总">
        <div class="summary-grid">
          <RouterLink class="summary-card" :to="{ name: 'vehicles' }">
            <div>
              <div class="k">车辆总数</div>
              <div class="summary-card__value">
                <span class="v">{{ data.vehicles_total }}</span>
                <span class="summary-card__unit">辆</span>
              </div>
            </div>
          </RouterLink>
          <RouterLink class="summary-card" :to="{ name: 'drivers' }">
            <div>
              <div class="k">驾驶员总数</div>
              <div class="summary-card__value">
                <span class="v">{{ data.drivers_total }}</span>
                <span class="summary-card__unit">人</span>
              </div>
            </div>
          </RouterLink>
        </div>

        <div class="quick-section">
          <div class="quick-section__heading">
            <div>
              <h2>快捷入口</h2>
              <p>常用业务一键直达</p>
            </div>
          </div>
          <nav class="quick-grid" aria-label="工作台快捷入口">
            <RouterLink class="quick-card" :to="{ name: 'fuel' }">
              <span class="quick-card__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M5 20V5.5A1.5 1.5 0 0 1 6.5 4h7A1.5 1.5 0 0 1 15 5.5V20M4 20h12M8 8h4M15 8.5h1.2l2.3 2.5v6.5a1.5 1.5 0 0 0 3 0V11l-2-2" /></svg>
              </span>
              <span class="quick-card__content">
                <strong>油卡查询</strong>
                <small>查询余额与油卡信息</small>
              </span>
              <span class="quick-card__arrow" aria-hidden="true">›</span>
            </RouterLink>
            <RouterLink class="quick-card" :to="{ name: 'locationNavigation' }">
              <span class="quick-card__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M12 21s6-5.2 6-11a6 6 0 1 0-12 0c0 5.8 6 11 6 11Z" /><circle cx="12" cy="10" r="2.2" /></svg>
              </span>
              <span class="quick-card__content">
                <strong>段内导航</strong>
                <small>查找段内地点与路线</small>
              </span>
              <span class="quick-card__arrow" aria-hidden="true">›</span>
            </RouterLink>
            <RouterLink class="quick-card" :to="{ name: 'fuelRecords' }">
              <span class="quick-card__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="M7 3h10v18H7zM9.5 7h5M10 12h4M10 16h4" /></svg>
              </span>
              <span class="quick-card__content">
                <strong>加油记录</strong>
                <small>录入并查看加油记录</small>
              </span>
              <span class="quick-card__arrow" aria-hidden="true">›</span>
            </RouterLink>
            <RouterLink class="quick-card" :to="{ name: 'repairRecords' }">
              <span class="quick-card__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24"><path d="m14.7 6.3 3-3a5 5 0 0 1-6.4 6.4L5 16l3 3 6.3-6.3a5 5 0 0 0 6.4-6.4l-3 3" /><path d="m4 17-1 1 3 3 1-1" /></svg>
              </span>
              <span class="quick-card__content">
                <strong>维修记录</strong>
                <small>录入并查看维修记录</small>
              </span>
              <span class="quick-card__arrow" aria-hidden="true">›</span>
            </RouterLink>
          </nav>
        </div>
      </section>

      <section class="panel analytics">
        <div class="panel-hd panel-hd--split">
          <div>油耗分析看板</div>
          <div class="filters">
            <select v-model="yearFilter" class="sel">
              <option value="all">全部年份</option>
              <option v-for="y in yearOptions" :key="y" :value="String(y)">{{ y }}年</option>
            </select>
            <select v-model="metric" class="sel">
              <option value="avg" :disabled="!fuelKpi.totalMileage">百公里油耗（需里程数据）</option>
              <option value="amount">金额</option>
              <option value="liters">升数</option>
            </select>
            <select v-model.number="topN" class="sel">
              <option :value="5">TOP 5</option>
              <option :value="8">TOP 8</option>
              <option :value="10">TOP 10</option>
            </select>
          </div>
        </div>

        <div class="analytics-kpis">
          <div class="mini">
            <div class="mk">总加油升数</div>
            <div class="mv">{{ formatNum(fuelKpi.totalLiters) }} L</div>
          </div>
          <div class="mini">
            <div class="mk">总加油金额</div>
            <div class="mv">￥{{ formatNum(fuelKpi.totalAmount) }}</div>
          </div>
          <div class="mini">
            <div class="mk">推算里程</div>
            <div class="mv">{{ formatNum(fuelKpi.totalMileage || null) }} km</div>
          </div>
          <div class="mini">
            <div class="mk">平均油耗</div>
            <div class="mv">{{ formatNum(fuelKpi.avg100) }} L/100km</div>
          </div>
        </div>

        <div class="charts">
          <div class="chart">
            <div class="ct">月度趋势（{{ metricLabel }}）</div>
            <svg viewBox="0 0 760 220" class="line-chart" role="img" aria-label="月度趋势图">
              <defs>
                <linearGradient id="dashTrendStroke" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#c96442" />
                  <stop offset="38%" stop-color="#d97757" />
                  <stop offset="72%" stop-color="#9a7340" />
                  <stop offset="100%" stop-color="#b8883a" />
                </linearGradient>
              </defs>
              <polyline
                :points="trendPoints"
                fill="none"
                stroke="url(#dashTrendStroke)"
                stroke-width="3"
                stroke-linecap="round"
              />
              <line x1="24" y1="190" x2="736" y2="190" stroke="#ddd7ca" stroke-width="1" />
              <g v-for="(m, idx) in monthlySeries" :key="`${m.year}-${m.month}`">
                <circle
                  :cx="pointX(idx, monthlySeries.length)"
                  :cy="pointY(valueOf(m), maxTrendValue)"
                  r="3.5"
                  :fill="trendDotFill(idx)"
                  stroke="rgba(255,255,255,0.85)"
                  stroke-width="1"
                />
              </g>
            </svg>
            <div class="axis">
              <span v-for="m in monthlySeries" :key="`${m.year}-${m.month}-label`">{{ shortMonthLabel(m.year, m.month) }}</span>
            </div>
          </div>

          <div class="chart">
            <div class="ct">车辆对比（{{ metricLabel }}）</div>
            <div class="bars">
              <div v-for="(item, idx) in vehicleTopList" :key="`${item.year}-${item.plate_number}`" class="bar-row">
                <div class="bar-label">{{ item.plate_number }}</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ width: `${barWidth(item)}%`, ...barFillStyle(idx) }" />
                </div>
                <div class="bar-value">{{ formatMetric(item) }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="quarter">
          <div class="ct">季度表现</div>
          <table class="tbl">
            <thead>
              <tr>
                <th>季度</th>
                <th>百公里油耗</th>
                <th>升数</th>
                <th>金额</th>
                <th>里程</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterSeries" :key="`${q.year}-${q.quarter}`">
                <td>{{ q.year }} Q{{ q.quarter }}</td>
                <td>{{ formatNum(q.avg_l_per_100km) }} L/100km</td>
                <td>{{ formatNum(q.total_liters) }}</td>
                <td>￥{{ formatNum(q.total_amount) }}</td>
                <td>{{ formatNum(q.total_mileage || null) }} km</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { fetchDashboardSummary } from '@/api/dashboard'
import { listDrivers } from '@/api/drivers'
import { listFuelBalancesPaged, listFuelRecordsPaged } from '@/api/fuel'
import { listMaintenance } from '@/api/maintenance'
import type { DashboardSummary } from '@/api/types'
import { listTrips } from '@/api/trips'
import { listVehicles } from '@/api/vehicles'

type FuelMonth = DashboardSummary['fuel_analysis']['monthly'][number]
type FuelQuarter = DashboardSummary['fuel_analysis']['quarterly'][number]
type FuelVehicle = DashboardSummary['fuel_analysis']['vehicles'][number]

const loading = ref(true)
const data = ref<DashboardSummary | null>(null)
const msg = ref('')

const yearFilter = ref('all')
const metric = ref<'avg' | 'amount' | 'liters'>('amount')
const topN = ref(8)

function emptyDashboardSummary(): DashboardSummary {
  return {
    vehicles_total: 0,
    drivers_total: 0,
    trip_requests_total: 0,
    pending_trip_requests: 0,
    maintenance_records_total: 0,
    fuel_cards_total: 0,
    fuel_records_total: 0,
    fuel_analysis: {
      years: [],
      overview: {
        total_liters: 0,
        total_amount: 0,
        total_mileage: 0,
        avg_l_per_100km: 0,
        records: 0,
        valid_segments: 0,
        invalid_segments: 0,
      },
      yearly: [],
      monthly: [],
      quarterly: [],
      vehicles: [],
    },
  }
}

async function fallbackDashboardSummaryFromTables(): Promise<DashboardSummary> {
  const pageSize = 200
  async function countVehicles() {
    let total = 0
    let skip = 0
    while (true) {
      const batch = await listVehicles({ skip, limit: pageSize })
      total += batch.length
      if (batch.length < pageSize) break
      skip += pageSize
    }
    return total
  }

  async function countTrips(status?: string) {
    let total = 0
    let skip = 0
    while (true) {
      const batch = await listTrips({ status, skip, limit: pageSize })
      total += batch.length
      if (batch.length < pageSize) break
      skip += pageSize
    }
    return total
  }

  async function countMaintenance() {
    let total = 0
    let skip = 0
    while (true) {
      const batch = await listMaintenance({ skip, limit: pageSize })
      total += batch.length
      if (batch.length < pageSize) break
      skip += pageSize
    }
    return total
  }

  const [vehiclesTotal, driversResp, tripsTotal, pendingTripsTotal, maintenanceTotal, fuelCardsTotal, fuelRecordsPage] =
    await Promise.all([
      countVehicles(),
      listDrivers({ limit: 1 }),
      countTrips(),
      countTrips('pending'),
      countMaintenance(),
      listFuelBalancesPaged({ page: 1, page_size: 1 }).then((x) => x.total ?? 0),
      listFuelRecordsPaged({ page: 1, page_size: 1 }),
    ])

  return {
    ...emptyDashboardSummary(),
    vehicles_total: vehiclesTotal,
    drivers_total: driversResp.total ?? 0,
    trip_requests_total: tripsTotal,
    pending_trip_requests: pendingTripsTotal,
    maintenance_records_total: maintenanceTotal,
    fuel_cards_total: fuelCardsTotal,
    fuel_records_total: fuelRecordsPage.total ?? 0,
  }
}

const yearOptions = computed(() => data.value?.fuel_analysis.years ?? [])
const selectedYear = computed<number | null>(() => (yearFilter.value === 'all' ? null : Number(yearFilter.value)))
const metricLabel = computed(() => {
  if (metric.value === 'amount') return '金额'
  if (metric.value === 'liters') return '升数'
  return '百公里油耗'
})

const monthlySeries = computed<FuelMonth[]>(() => {
  const src = data.value?.fuel_analysis.monthly ?? []
  return src.filter((x) => selectedYear.value === null || x.year === selectedYear.value)
})

const quarterSeries = computed<FuelQuarter[]>(() => {
  const src = data.value?.fuel_analysis.quarterly ?? []
  return src.filter((x) => selectedYear.value === null || x.year === selectedYear.value)
})

const fuelKpi = computed(() => {
  const months = monthlySeries.value
  const totalLiters = months.reduce((s, x) => s + x.total_liters, 0)
  const totalAmount = months.reduce((s, x) => s + x.total_amount, 0)
  const totalMileage = months.reduce((s, x) => s + x.total_mileage, 0)
  return {
    totalLiters,
    totalAmount,
    totalMileage,
    avg100: totalMileage > 0 ? (totalLiters * 100) / totalMileage : null,
  }
})

const vehicleTopList = computed<FuelVehicle[]>(() => {
  const src = data.value?.fuel_analysis.vehicles ?? []
  const filtered = src.filter((x) => selectedYear.value === null || x.year === selectedYear.value)
  return filtered
    .sort((a, b) => metricValue(b) - metricValue(a))
    .slice(0, topN.value)
})

const maxBarValue = computed(() => Math.max(...vehicleTopList.value.map((v) => metricValue(v)), 1))
const maxTrendValue = computed(() => Math.max(...monthlySeries.value.map((m) => valueOf(m)), 1))

const trendPoints = computed(() => {
  const total = monthlySeries.value.length
  if (total < 1) return ''
  return monthlySeries.value.map((m, idx) => `${pointX(idx, total)},${pointY(valueOf(m), maxTrendValue.value)}`).join(' ')
})

function metricValue(item: FuelVehicle) {
  if (metric.value === 'amount') return item.total_amount
  if (metric.value === 'liters') return item.total_liters
  return item.avg_l_per_100km ?? 0
}

function valueOf(item: FuelMonth) {
  if (metric.value === 'amount') return item.total_amount
  if (metric.value === 'liters') return item.total_liters
  return item.avg_l_per_100km ?? 0
}

function pointX(index: number, total: number) {
  if (total <= 1) return 380
  return 24 + (712 * index) / (total - 1)
}

function pointY(value: number, max: number) {
  if (max <= 0) return 190
  return 190 - (156 * value) / max
}

function formatNum(v: number | null) {
  if (v === null) return '—'
  return Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function shortMonthLabel(year: number, month: number) {
  return selectedYear.value === null ? `${year % 100}-${String(month).padStart(2, '0')}` : `${month}月`
}

function barWidth(item: FuelVehicle) {
  return (metricValue(item) / maxBarValue.value) * 100
}

/** 与车辆管理页一致的暖色条形渐变。 */
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

const TREND_DOT_FILLS = [
  '#c96442',
  '#d97757',
  '#9a7340',
  '#b8883a',
  '#6b5d4b',
  '#a76b52',
  '#5c5347',
  '#c47a5f',
] as const

function barFillStyle(index: number): Record<string, string> {
  return {
    background: BAR_FILL_GRADIENTS[index % BAR_FILL_GRADIENTS.length],
    boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.32)',
  }
}

function trendDotFill(index: number) {
  return TREND_DOT_FILLS[index % TREND_DOT_FILLS.length]
}

function formatMetric(item: FuelVehicle) {
  if (metric.value === 'amount') return `￥${formatNum(item.total_amount)}`
  if (metric.value === 'liters') return `${formatNum(item.total_liters)} L`
  return `${formatNum(item.avg_l_per_100km)} L/100km`
}

onMounted(async () => {
  loading.value = true
  try {
    data.value = await fetchDashboardSummary()
  } catch {
    try {
      data.value = await fallbackDashboardSummaryFromTables()
      msg.value = '工作台主汇总接口异常，已切换为表数据统计视图'
    } catch {
      data.value = emptyDashboardSummary()
      msg.value = '工作台数据暂不可用，已展示默认视图'
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.msg {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.08);
  color: var(--cl-error);
  font-size: 13px;
}

.muted {
  color: var(--cl-olive);
  font-size: 13px;
}

.dashboard-overview {
  display: grid;
  gap: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 124px;
  border: 1px solid var(--cl-border-cream);
  background:
    radial-gradient(circle at 92% 15%, rgba(201, 100, 66, 0.13), transparent 32%),
    var(--cl-ivory);
  border-radius: 16px;
  padding: 20px;
  text-align: center;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.12s ease;
}

.summary-card::after {
  position: absolute;
  right: 22%;
  bottom: 0;
  left: 22%;
  height: 3px;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(90deg, transparent, rgba(201, 100, 66, 0.78), transparent);
  content: '';
}

.summary-card:hover,
.quick-card:hover {
  border-color: rgba(201, 100, 66, 0.45);
  box-shadow: rgba(0, 0, 0, 0.08) 0px 6px 28px;
  transform: translateY(-1px);
}

.summary-card:focus-visible,
.quick-card:focus-visible {
  outline: 2px solid rgba(201, 100, 66, 0.55);
  outline-offset: 2px;
}

.summary-card__unit {
  color: var(--cl-olive);
  font-size: 13px;
  font-weight: 500;
}

.k {
  color: var(--cl-charcoal);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.summary-card__value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
  margin-top: 8px;
}

.v {
  color: #a94f32;
  font-size: 2.45rem;
  font-weight: 700;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  line-height: 1;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.75);
}

.quick-section {
  border: 1px solid var(--cl-border-cream);
  border-radius: 16px;
  padding: 16px;
  background: var(--cl-ivory);
  box-shadow: rgba(0, 0, 0, 0.04) 0 4px 20px;
}

.quick-section__heading {
  margin-bottom: 12px;
}

.quick-section__heading h2 {
  margin: 0;
  color: var(--cl-charcoal);
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 1.05rem;
  font-weight: 500;
}

.quick-section__heading p {
  margin: 3px 0 0;
  color: var(--cl-olive);
  font-size: 12px;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.quick-card {
  position: relative;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-height: 76px;
  padding: 12px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 13px;
  background: var(--cl-white);
  color: inherit;
  text-decoration: none;
  overflow: hidden;
  animation: quick-card-enter 0.48s ease-out backwards;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.18s ease,
    background-color 0.18s ease;
}

.quick-card:nth-child(2) {
  animation-delay: 0.06s;
}

.quick-card:nth-child(3) {
  animation-delay: 0.12s;
}

.quick-card:nth-child(4) {
  animation-delay: 0.18s;
}

.quick-card::before {
  position: absolute;
  top: -70%;
  bottom: -70%;
  left: -45%;
  width: 32%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.72), transparent);
  content: '';
  opacity: 0;
  pointer-events: none;
  transform: rotate(18deg);
  transition:
    left 0.5s ease,
    opacity 0.18s ease;
}

.quick-card:hover::before,
.quick-card:focus-visible::before {
  left: 118%;
  opacity: 1;
}

.quick-card:hover,
.quick-card:focus-visible {
  background: color-mix(in srgb, var(--cl-white) 94%, #f4d8ca);
  transform: translateY(-4px) scale(1.01);
}

.quick-card:active {
  transform: translateY(0) scale(0.98);
}

.quick-card__icon {
  --pulse-delay: 0s;
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(201, 100, 66, 0.1);
  color: #b95f40;
  animation: quick-icon-bob 2.8s ease-in-out infinite;
  transition:
    color 0.18s ease,
    background-color 0.18s ease,
    box-shadow 0.18s ease;
}

.quick-card__icon::before,
.quick-card__icon::after {
  position: absolute;
  z-index: -1;
  inset: 2px;
  border: 1.5px solid rgba(185, 95, 64, 0.5);
  border-radius: inherit;
  content: '';
  opacity: 0;
  pointer-events: none;
  animation: quick-icon-ripple 2.8s cubic-bezier(0.2, 0.65, 0.35, 1) infinite;
  animation-delay: var(--pulse-delay);
}

.quick-card__icon::after {
  border-color: rgba(201, 100, 66, 0.34);
  animation-delay: calc(var(--pulse-delay) + 0.85s);
}

.quick-card:nth-child(2) .quick-card__icon {
  --pulse-delay: 0.35s;
  animation-delay: 0.35s;
}

.quick-card:nth-child(3) .quick-card__icon {
  --pulse-delay: 0.7s;
  animation-delay: 0.7s;
}

.quick-card:nth-child(4) .quick-card__icon {
  --pulse-delay: 1.05s;
  animation-delay: 1.05s;
}

.quick-card:hover .quick-card__icon,
.quick-card:focus-visible .quick-card__icon {
  background: rgba(201, 100, 66, 0.16);
  box-shadow: 0 7px 16px rgba(169, 79, 50, 0.16);
  color: #a94f32;
  animation: quick-icon-hop 0.55s ease;
}

.quick-card__icon svg {
  position: relative;
  z-index: 2;
  width: 23px;
  height: 23px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.quick-card__content {
  position: relative;
  z-index: 1;
  min-width: 0;
}

.quick-card__content strong,
.quick-card__content small {
  display: block;
}

.quick-card__content strong {
  color: var(--cl-charcoal);
  font-size: 14px;
  font-weight: 600;
}

.quick-card__content small {
  margin-top: 3px;
  overflow: hidden;
  color: var(--cl-olive);
  font-size: 11px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.quick-card__arrow {
  position: relative;
  z-index: 1;
  color: var(--cl-stone);
  font-size: 23px;
  line-height: 1;
  transition:
    color 0.18s ease,
    transform 0.18s ease;
}

.quick-card:hover .quick-card__arrow,
.quick-card:focus-visible .quick-card__arrow {
  color: #a94f32;
  transform: translateX(3px);
}

@keyframes quick-card-enter {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes quick-icon-bob {
  0%,
  68%,
  100% {
    box-shadow: 0 0 0 rgba(169, 79, 50, 0);
    transform: translateY(0) scale(1);
  }
  78% {
    box-shadow: 0 8px 18px rgba(169, 79, 50, 0.2);
    transform: translateY(-5px) scale(1.045);
  }
  87% {
    box-shadow: 0 2px 8px rgba(169, 79, 50, 0.1);
    transform: translateY(0) scale(0.99);
  }
  94% {
    transform: translateY(-2px) scale(1.015);
  }
}

@keyframes quick-icon-ripple {
  0%,
  48% {
    opacity: 0;
    transform: scale(0.82);
  }
  56% {
    opacity: 0.62;
  }
  82% {
    opacity: 0;
    transform: scale(1.72);
  }
  100% {
    opacity: 0;
    transform: scale(1.72);
  }
}

@keyframes quick-icon-hop {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }
  42% {
    transform: translateY(-7px) scale(1.08);
  }
  68% {
    transform: translateY(1px) scale(0.98);
  }
}

.panel {
  margin-top: 16px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
}

.panel-hd {
  padding: 14px 16px;
  border-bottom: 1px solid var(--cl-border-cream);
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-weight: 500;
  font-size: 1.05rem;
}

.panel-hd--split {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.sel {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 13px;
}

.analytics {
  margin-top: 16px;
}

.analytics-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--cl-border-cream);
  background: linear-gradient(180deg, rgba(201, 100, 66, 0.05), rgba(201, 100, 66, 0));
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
  font-size: 1.1rem;
}

.charts {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr);
  gap: 12px;
  padding: 12px 16px;
}

.chart {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 12px;
  padding: 12px;
}

.ct {
  font-size: 13px;
  color: var(--cl-olive);
  margin-bottom: 8px;
}

.line-chart {
  width: 100%;
  height: 220px;
  display: block;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(201, 100, 66, 0.08), rgba(201, 100, 66, 0));
}

.axis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(48px, 1fr));
  gap: 4px;
  margin-top: 6px;
  color: var(--cl-stone);
  font-size: 11px;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: grid;
  grid-template-columns: 80px minmax(0, 1fr) 94px;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 12px;
  color: var(--cl-charcoal);
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

.bar-row:hover .bar-fill {
  filter: brightness(1.07) saturate(1.05);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    0 0 0 1px rgba(201, 100, 66, 0.12);
}

.bar-value {
  text-align: right;
  font-size: 12px;
  color: var(--cl-charcoal);
}

.quarter {
  padding: 0 16px 14px;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
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
  font-weight: 600;
  background: var(--cl-warm-sand);
}

@media (max-width: 1200px) {
  .quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .analytics-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .charts {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .dashboard-overview {
    gap: 12px;
  }

  .summary-grid {
    gap: 8px;
  }

  .summary-card {
    min-height: 102px;
    padding: 15px;
    border-radius: 14px;
  }

  .v {
    font-size: 2rem;
  }

  .quick-section {
    padding: 14px;
  }

  .quick-grid {
    gap: 8px;
  }

  .quick-card {
    grid-template-columns: 38px minmax(0, 1fr);
    min-height: 72px;
    padding: 10px;
  }

  .quick-card__icon {
    width: 38px;
    height: 38px;
  }

  .quick-card__arrow,
  .quick-card__content small {
    display: none;
  }

  .analytics-kpis {
    grid-template-columns: 1fr;
  }

  .bar-row {
    grid-template-columns: 64px minmax(0, 1fr) 88px;
  }
}

@media (max-width: 390px) {
  .summary-card {
    min-height: 94px;
    padding: 13px;
  }

  .quick-card {
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 8px;
    min-height: 66px;
    padding: 8px;
  }

  .quick-card__icon {
    width: 34px;
    height: 34px;
    border-radius: 10px;
  }

  .quick-card__icon svg {
    width: 20px;
    height: 20px;
  }

  .quick-card__content strong {
    font-size: 13px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .quick-card,
  .quick-card__icon,
  .quick-card__icon::before,
  .quick-card__icon::after {
    animation: none;
  }

  .quick-card__icon::before,
  .quick-card__icon::after {
    display: none;
  }

  .quick-card,
  .quick-card::before,
  .quick-card__icon,
  .quick-card__arrow {
    transition-duration: 0.01ms;
  }
}

</style>
