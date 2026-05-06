<template>
  <div>
    <div class="toolbar">
      <input v-model.trim="q" class="q" type="search" placeholder="搜索用途/申请人/起止地点" @keydown.enter.prevent="reload" />
      <select v-model="statusFilter" class="sel" @change="reload">
        <option value="">全部状态</option>
        <option value="pending">待审批</option>
        <option value="approved">已批准</option>
        <option value="rejected">已驳回</option>
        <option value="in_progress">执行中</option>
        <option value="completed">已完成</option>
        <option value="cancelled">已取消</option>
      </select>
      <button type="button" class="primary" @click="openCreate">新建申请</button>
      <button type="button" class="ghost" :disabled="loading" @click="reload">刷新</button>
    </div>

    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <table v-else class="tbl">
      <thead>
        <tr>
          <th>ID</th>
          <th>用途</th>
          <th>申请人</th>
          <th>行程</th>
          <th>时间</th>
          <th>状态</th>
          <th>车辆/驾驶员</th>
          <th class="w">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in rows" :key="t.id">
          <td>{{ t.id }}</td>
          <td class="t">{{ t.purpose }}</td>
          <td>{{ t.applicant_name }}</td>
          <td class="t2">{{ t.origin }} → {{ t.destination }}</td>
          <td class="mono">{{ fmtDateTime(t.start_at) }}<br />{{ fmtDateTime(t.end_at) }}</td>
          <td><span class="tag">{{ statusText(t.status) }}</span></td>
          <td class="mono">
            {{ plateOf(t.vehicle_id) }}<br />
            {{ nameOf(t.driver_id) }}
          </td>
          <td class="w">
            <button type="button" class="link" @click="openEdit(t)">办理</button>
            <button v-if="canManageFleet" type="button" class="link danger" @click="onDelete(t)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <AppModal :open="createOpen" title="新建用车申请" @close="createOpen = false">
      <div class="form">
        <label>用途说明</label>
        <textarea v-model.trim="c.purpose" rows="3" />

        <label>申请人</label>
        <input v-model.trim="c.applicant_name" />

        <label>出发地</label>
        <input v-model.trim="c.origin" />

        <label>目的地</label>
        <input v-model.trim="c.destination" />

        <label>开始时间</label>
        <input v-model="c.start_local" type="datetime-local" />

        <label>结束时间</label>
        <input v-model="c.end_local" type="datetime-local" />

        <label>人数</label>
        <input v-model.number="c.passenger_count" type="number" min="1" max="99" />

        <label>备注</label>
        <textarea v-model.trim="c.notes" rows="2" />
      </div>
      <template #footer>
        <button type="button" class="ghost" @click="createOpen = false">取消</button>
        <button type="button" class="primary" :disabled="saving" @click="saveCreate">提交</button>
      </template>
    </AppModal>

    <AppModal :open="editOpen" title="办理用车申请" @close="editOpen = false">
      <div class="form">
        <label>状态</label>
        <select v-model="e.status">
          <option value="pending">待审批</option>
          <option value="approved">已批准</option>
          <option value="rejected">已驳回</option>
          <option value="in_progress">执行中</option>
          <option value="completed">已完成</option>
          <option value="cancelled">已取消</option>
        </select>

        <label>分配车辆</label>
        <select v-model.number="e.vehicle_id">
          <option :value="0">未分配</option>
          <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}（{{ v.brand }}{{ v.model }}）</option>
        </select>

        <label>分配驾驶员</label>
        <select v-model.number="e.driver_id">
          <option :value="0">未分配</option>
          <option v-for="d in drivers" :key="d.id" :value="d.id">{{ d.name }}（{{ d.phone }}）</option>
        </select>

        <label>用途说明</label>
        <textarea v-model.trim="e.purpose" rows="3" />

        <label>申请人</label>
        <input v-model.trim="e.applicant_name" />

        <label>出发地</label>
        <input v-model.trim="e.origin" />

        <label>目的地</label>
        <input v-model.trim="e.destination" />

        <label>开始时间</label>
        <input v-model="e.start_local" type="datetime-local" />

        <label>结束时间</label>
        <input v-model="e.end_local" type="datetime-local" />

        <label>人数</label>
        <input v-model.number="e.passenger_count" type="number" min="1" max="99" />

        <label>备注</label>
        <textarea v-model.trim="e.notes" rows="2" />
      </div>
      <template #footer>
        <button type="button" class="ghost" @click="editOpen = false">取消</button>
        <button type="button" class="primary" :disabled="saving" @click="saveEdit">保存</button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import * as dapi from '@/api/drivers'
import * as tapi from '@/api/trips'
import * as vapi from '@/api/vehicles'
import AppModal from '@/components/AppModal.vue'
import { usePermissions } from '@/composables/usePermissions'
import type { Driver, TripRequest, Vehicle } from '@/api/types'
import { fmtDateTime, toIsoFromLocal, toLocalInputValue } from '@/utils/format'

const { canManageFleet } = usePermissions()
const route = useRoute()

const TRIP_STATUS_QUERY = new Set([
  '',
  'pending',
  'approved',
  'rejected',
  'in_progress',
  'completed',
  'cancelled',
])

function syncStatusFromRoute() {
  const raw = route.query.status
  const s = Array.isArray(raw) ? raw[0] : raw
  const next = typeof s === 'string' ? s : ''
  statusFilter.value = TRIP_STATUS_QUERY.has(next) ? next : ''
}

const loading = ref(true)
const saving = ref(false)
const rows = ref<TripRequest[]>([])
const vehicles = ref<Vehicle[]>([])
const drivers = ref<Driver[]>([])
const q = ref('')
const statusFilter = ref('')
const msg = ref('')

const createOpen = ref(false)
const editOpen = ref(false)
const editingId = ref<number | null>(null)

const c = reactive({
  purpose: '',
  applicant_name: '',
  origin: '',
  destination: '',
  start_local: '',
  end_local: '',
  passenger_count: 1,
  notes: '',
})

const e = reactive({
  purpose: '',
  applicant_name: '',
  origin: '',
  destination: '',
  start_local: '',
  end_local: '',
  passenger_count: 1,
  status: 'pending',
  vehicle_id: 0,
  driver_id: 0,
  notes: '',
})

function statusText(s: string) {
  const m: Record<string, string> = {
    pending: '待审批',
    approved: '已批准',
    rejected: '已驳回',
    in_progress: '执行中',
    completed: '已完成',
    cancelled: '已取消',
  }
  return m[s] || s
}

function plateOf(id: number | null) {
  if (!id) return '-'
  return vehicles.value.find((x) => x.id === id)?.plate_number || `#${id}`
}

function nameOf(id: number | null) {
  if (!id) return '-'
  return drivers.value.find((x) => x.id === id)?.name || `#${id}`
}

async function reload() {
  loading.value = true
  msg.value = ''
  try {
    const [ts, vs, ds] = await Promise.all([
      tapi.listTrips({ q: q.value || undefined, status: statusFilter.value || undefined, limit: 200 }),
      vapi.listVehicles({ limit: 200 }),
      dapi.listDrivers({ limit: 200 }),
    ])
    rows.value = ts
    vehicles.value = vs
    drivers.value = ds.items
  } catch {
    msg.value = '加载数据失败'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  const now = new Date()
  const s = new Date(now.getTime() + 24 * 3600 * 1000)
  const en = new Date(s.getTime() + 3 * 3600 * 1000)
  c.purpose = ''
  c.applicant_name = ''
  c.origin = '总部大院'
  c.destination = ''
  c.start_local = toLocalInputValue(s.toISOString())
  c.end_local = toLocalInputValue(en.toISOString())
  c.passenger_count = 1
  c.notes = ''
  createOpen.value = true
}

async function saveCreate() {
  saving.value = true
  msg.value = ''
  try {
    await tapi.createTrip({
      purpose: c.purpose,
      applicant_name: c.applicant_name,
      origin: c.origin,
      destination: c.destination,
      start_at: toIsoFromLocal(c.start_local),
      end_at: toIsoFromLocal(c.end_local),
      passenger_count: c.passenger_count,
      notes: c.notes || null,
    })
    createOpen.value = false
    await reload()
  } catch (err) {
    msg.value = axios.isAxiosError(err) ? String(err.response?.data?.detail || '提交失败') : '提交失败'
  } finally {
    saving.value = false
  }
}

function openEdit(t: TripRequest) {
  editingId.value = t.id
  e.purpose = t.purpose
  e.applicant_name = t.applicant_name
  e.origin = t.origin
  e.destination = t.destination
  e.start_local = toLocalInputValue(t.start_at)
  e.end_local = toLocalInputValue(t.end_at)
  e.passenger_count = t.passenger_count
  e.status = t.status
  e.vehicle_id = t.vehicle_id || 0
  e.driver_id = t.driver_id || 0
  e.notes = t.notes || ''
  editOpen.value = true
}

async function saveEdit() {
  if (!editingId.value) return
  saving.value = true
  msg.value = ''
  try {
    await tapi.updateTrip(editingId.value, {
      purpose: e.purpose,
      applicant_name: e.applicant_name,
      origin: e.origin,
      destination: e.destination,
      start_at: toIsoFromLocal(e.start_local),
      end_at: toIsoFromLocal(e.end_local),
      passenger_count: e.passenger_count,
      status: e.status,
      vehicle_id: e.vehicle_id || null,
      driver_id: e.driver_id || null,
      notes: e.notes || null,
    })
    editOpen.value = false
    await reload()
  } catch (err) {
    msg.value = axios.isAxiosError(err) ? String(err.response?.data?.detail || '保存失败') : '保存失败'
  } finally {
    saving.value = false
  }
}

async function onDelete(t: TripRequest) {
  if (!confirm(`确定删除申请 #${t.id} ？`)) return
  msg.value = ''
  try {
    await tapi.deleteTrip(t.id)
    await reload()
  } catch (err) {
    msg.value = axios.isAxiosError(err) ? String(err.response?.data?.detail || '删除失败') : '删除失败'
  }
}

watch(
  () => route.query.status,
  () => {
    syncStatusFromRoute()
    reload()
  },
  { immediate: true },
)
</script>

<style scoped>
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
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  color: var(--cl-near-black);
}

.sel {
  padding: 10px 10px;
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

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  overflow: hidden;
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

.t {
  max-width: 360px;
}

.t2 {
  max-width: 280px;
}

.mono {
  font-size: 12px;
  color: var(--cl-dark-warm);
  line-height: 1.35;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--cl-border-warm);
  font-size: 12px;
  color: var(--cl-charcoal);
  background: var(--cl-white);
}

.w {
  width: 150px;
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
</style>
