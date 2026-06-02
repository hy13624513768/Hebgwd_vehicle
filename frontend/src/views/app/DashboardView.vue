<template>
  <div>
    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <template v-else-if="data">
      <div class="grid">
        <RouterLink class="card" :to="{ name: 'vehicles' }">
          <div class="k">车辆总数</div>
          <div class="v">{{ data.vehicles_total }}</div>
        </RouterLink>
        <RouterLink class="card" :to="{ name: 'drivers' }">
          <div class="k">驾驶员总数</div>
          <div class="v">{{ data.drivers_total }}</div>
        </RouterLink>
        <RouterLink class="card" :to="{ name: 'trips' }">
          <div class="k">用车申请</div>
          <div class="v">{{ data.trip_requests_total }}</div>
        </RouterLink>
        <RouterLink class="card warn" :to="{ name: 'trips', query: { status: 'pending' } }">
          <div class="k">待审批</div>
          <div class="v">{{ data.pending_trip_requests }}</div>
        </RouterLink>
        <RouterLink class="card" :to="{ name: 'maintenance' }">
          <div class="k">维修保养</div>
          <div class="v">{{ data.maintenance_records_total }}</div>
        </RouterLink>
        <RouterLink class="card" :to="{ name: 'fuel' }">
          <div class="k">油卡数量</div>
          <div class="v">{{ data.fuel_cards_total }}</div>
        </RouterLink>
        <RouterLink class="card" :to="{ name: 'fuelBills' }">
          <div class="k">加油笔数</div>
          <div class="v">{{ data.fuel_records_total }}</div>
        </RouterLink>
      </div>

      <section class="panel analytics">
        <div class="panel-hd panel-hd--split">
          <div>油耗分析看板</div>
          <div class="filters">
            <select v-model="yearFilter" class="sel">
              <option value="all">全部年份</option>
              <option v-for="y in yearOptions" :key="y" :value="String(y)">{{ y }}年</option>
            </select>
            <select v-model="metric" class="sel">
              <option value="avg">百公里油耗</option>
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
            <div class="mv">{{ formatNum(fuelKpi.totalMileage) }} km</div>
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
              <div v-for="(item, idx) in vehicleTopList" :key="`${item.year}-${item.vehicle_id}`" class="bar-row">
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
                <td>{{ formatNum(q.total_mileage) }} km</td>
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
const metric = ref<'avg' | 'amount' | 'liters'>('avg')
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
    avg100: totalMileage > 0 ? (totalLiters * 100) / totalMileage : 0,
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
  return item.avg_l_per_100km
}

function valueOf(item: FuelMonth) {
  if (metric.value === 'amount') return item.total_amount
  if (metric.value === 'liters') return item.total_liters
  return item.avg_l_per_100km
}

function pointX(index: number, total: number) {
  if (total <= 1) return 380
  return 24 + (712 * index) / (total - 1)
}

function pointY(value: number, max: number) {
  if (max <= 0) return 190
  return 190 - (156 * value) / max
}

function formatNum(v: number) {
  return Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function shortMonthLabel(year: number, month: number) {
  return selectedYear.value === null ? `${year % 100}-${String(month).padStart(2, '0')}` : `${month}月`
}

function barWidth(item: FuelVehicle) {
  return (metricValue(item) / maxBarValue.value) * 100
}

/** 与车辆管理页一致的暖色条形渐变 */
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.card {
  display: block;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  border-radius: 12px;
  padding: 16px 16px;
  box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 24px;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.12s ease;
}

.card:hover {
  border-color: rgba(201, 100, 66, 0.45);
  box-shadow: rgba(0, 0, 0, 0.08) 0px 6px 28px;
  transform: translateY(-1px);
}

.card:focus-visible {
  outline: 2px solid rgba(201, 100, 66, 0.55);
  outline-offset: 2px;
}

.card.warn {
  border-color: rgba(201, 100, 66, 0.4);
  background: rgba(201, 100, 66, 0.08);
}

.k {
  font-size: 12px;
  color: var(--cl-olive);
  letter-spacing: 0.12px;
}

.v {
  margin-top: 8px;
  font-size: 1.65rem;
  font-weight: 500;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  line-height: 1.15;
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
  .analytics-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .charts {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .analytics-kpis {
    grid-template-columns: 1fr;
  }

  .bar-row {
    grid-template-columns: 64px minmax(0, 1fr) 88px;
  }
}
</style>
