<template>
  <div class="maintenance-view">
    <div class="toolbar">
      <select v-model.number="vehicleFilter" class="sel" @change="reload">
        <option :value="0">全部车辆</option>
        <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}</option>
      </select>
      <div class="toolbar-actions">
        <button v-if="canManageFleet" type="button" class="primary" @click="openCreate">新增维修保养</button>
        <a
          class="primary primary--link"
          :href="MAINTENANCE_DOCS_URL"
          target="_blank"
          rel="noopener noreferrer"
        >
          查看具体维修单及照片
        </a>
      </div>
      <button type="button" class="ghost ghost--toolbar" :disabled="loading" @click="reload">刷新</button>
    </div>

    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>
    <div v-else-if="!rows.length" class="muted empty-hint">暂无维修保养记录</div>

    <table v-else class="tbl tbl--desktop">
      <thead>
        <tr>
          <th>ID</th>
          <th>车辆</th>
          <th>日期</th>
          <th>类别</th>
          <th>金额</th>
          <th>里程</th>
          <th>服务商</th>
          <th>说明</th>
          <th class="w">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in rows" :key="m.id">
          <td>{{ m.id }}</td>
          <td class="strong">{{ plateOf(m.vehicle_id) }}</td>
          <td>{{ fmtDate(m.service_date) }}</td>
          <td>{{ m.category }}</td>
          <td>{{ m.amount }}</td>
          <td>{{ m.mileage }}</td>
          <td>{{ m.vendor }}</td>
          <td class="t">{{ m.description || '-' }}</td>
          <td class="w">
            <button v-if="canManageFleet" type="button" class="link" @click="openEdit(m)">编辑</button>
            <button v-if="canManageFleet" type="button" class="link danger" @click="onDelete(m)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <ul v-if="!loading && rows.length" class="maint-cards" aria-label="维修保养列表">
      <li v-for="m in rows" :key="`m-${m.id}`" class="maint-card">
        <div class="maint-card__top">
          <span class="maint-card__id">#{{ m.id }}</span>
          <span class="maint-card__plate">{{ plateOf(m.vehicle_id) }}</span>
        </div>
        <div class="maint-card__sub">
          <span class="maint-card__date">{{ fmtDate(m.service_date) }}</span>
          <span class="maint-card__cat">{{ m.category }}</span>
        </div>
        <div class="maint-card__grid">
          <div class="maint-card__row">
            <span class="maint-card__k">金额</span>
            <span class="maint-card__v">{{ m.amount }}</span>
          </div>
          <div class="maint-card__row">
            <span class="maint-card__k">里程</span>
            <span class="maint-card__v">{{ m.mileage }} km</span>
          </div>
          <div class="maint-card__row maint-card__row--full">
            <span class="maint-card__k">服务商</span>
            <span class="maint-card__v">{{ m.vendor || '—' }}</span>
          </div>
        </div>
        <div class="maint-card__desc">
          <span class="maint-card__desc-label">说明</span>
          <p class="maint-card__desc-text">{{ m.description || '—' }}</p>
        </div>
        <div v-if="canManageFleet" class="maint-card__actions">
          <button type="button" class="maint-card__btn" @click="openEdit(m)">编辑</button>
          <button type="button" class="maint-card__btn maint-card__btn--danger" @click="onDelete(m)">删除</button>
        </div>
      </li>
    </ul>

    <AppModal :open="modalOpen" :title="modalTitle" @close="modalOpen = false">
      <div class="form form--maintenance">
        <label>车辆</label>
        <select v-model.number="form.vehicle_id">
          <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate_number }}</option>
        </select>

        <label>服务日期</label>
        <input v-model="form.service_date" type="date" />

        <label>类别</label>
        <select v-model="form.category">
          <option value="保养">保养</option>
          <option value="维修">维修</option>
          <option value="年检">年检</option>
        </select>

        <label>金额（元）</label>
        <input v-model="form.amount" type="number" min="0" step="0.01" />

        <label>里程（km）</label>
        <input v-model.number="form.mileage" type="number" min="0" />

        <label>服务商</label>
        <input v-model.trim="form.vendor" />

        <label>说明</label>
        <textarea v-model.trim="form.description" rows="3" />
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
import { onMounted, reactive, ref } from 'vue'

import * as mapi from '@/api/maintenance'
import * as vapi from '@/api/vehicles'
import AppModal from '@/components/AppModal.vue'
import { usePermissions } from '@/composables/usePermissions'
import type { MaintenanceRecord, Vehicle } from '@/api/types'
import { fmtDate } from '@/utils/format'

const MAINTENANCE_DOCS_URL =
  'https://docs.qq.com/sheet/DS3BYckdqVWJFeXd2?tab=8g31c3&viewId=vM95eG'

const { canManageFleet } = usePermissions()

const loading = ref(true)
const saving = ref(false)
const rows = ref<MaintenanceRecord[]>([])
const vehicles = ref<Vehicle[]>([])
const vehicleFilter = ref(0)
const msg = ref('')

const modalOpen = ref(false)
const modalTitle = ref('新增维修保养')
const editingId = ref<number | null>(null)

const form = reactive({
  vehicle_id: 0,
  service_date: '',
  category: '保养',
  amount: '0',
  mileage: 0,
  vendor: '',
  description: '',
})

function plateOf(id: number) {
  return vehicles.value.find((x) => x.id === id)?.plate_number || `#${id}`
}

async function reload() {
  loading.value = true
  msg.value = ''
  try {
    const [vs, ms] = await Promise.all([
      vapi.listVehicles({ limit: 200 }),
      mapi.listMaintenance({
        vehicle_id: vehicleFilter.value || undefined,
        limit: 200,
      }),
    ])
    vehicles.value = vs
    rows.value = ms
    if (!form.vehicle_id && vehicles.value.length) {
      form.vehicle_id = vehicles.value[0].id
    }
  } catch {
    msg.value = '加载维修保养数据失败'
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.vehicle_id = vehicles.value[0]?.id || 0
  form.service_date = new Date().toISOString().slice(0, 10)
  form.category = '保养'
  form.amount = '0'
  form.mileage = 0
  form.vendor = ''
  form.description = ''
}

function openCreate() {
  editingId.value = null
  modalTitle.value = '新增维修保养'
  resetForm()
  modalOpen.value = true
}

function openEdit(m: MaintenanceRecord) {
  editingId.value = m.id
  modalTitle.value = '编辑维修保养'
  form.vehicle_id = m.vehicle_id
  form.service_date = m.service_date.slice(0, 10)
  form.category = m.category
  form.amount = String(m.amount)
  form.mileage = m.mileage
  form.vendor = m.vendor
  form.description = m.description || ''
  modalOpen.value = true
}

async function save() {
  saving.value = true
  msg.value = ''
  try {
    const payload: Record<string, unknown> = {
      vehicle_id: form.vehicle_id,
      service_date: form.service_date,
      category: form.category,
      amount: form.amount,
      mileage: form.mileage,
      vendor: form.vendor,
      description: form.description || null,
    }
    if (editingId.value) await mapi.updateMaintenance(editingId.value, payload)
    else await mapi.createMaintenance(payload)
    modalOpen.value = false
    await reload()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '保存失败') : '保存失败'
  } finally {
    saving.value = false
  }
}

async function onDelete(m: MaintenanceRecord) {
  if (!confirm(`确定删除维修保养记录 #${m.id} ？`)) return
  msg.value = ''
  try {
    await mapi.deleteMaintenance(m.id)
    await reload()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '删除失败') : '删除失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.maintenance-view {
  max-width: 100%;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.sel {
  min-width: 220px;
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
  font-family: inherit;
  font-size: inherit;
  font-weight: 800;
  line-height: 1.25;
  -webkit-font-smoothing: antialiased;
}

a.primary--link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  box-sizing: border-box;
  font-weight: 800;
  text-align: center;
  line-height: 1.3;
  word-break: break-word;
}

a.primary--link:link,
a.primary--link:visited {
  color: var(--cl-ivory);
}

a.primary--link:hover {
  filter: brightness(1.03);
}

a.primary--link:focus-visible {
  outline: 2px solid var(--cl-focus);
  outline-offset: 2px;
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

.empty-hint {
  padding: 24px 12px;
  text-align: center;
}

/* 桌面端表格；窄屏隐藏 */
.tbl--desktop {
  display: table;
}

.maint-cards {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0;
}

.maint-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  background: var(--cl-ivory);
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.04) 0 4px 16px;
}

.maint-card__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.maint-card__id {
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 700;
}

.maint-card__plate {
  font-size: 1.05rem;
  font-weight: 900;
  color: var(--cl-near-black);
  letter-spacing: 0.02em;
}

.maint-card__sub {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--cl-charcoal);
}

.maint-card__cat {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  font-weight: 700;
  font-size: 12px;
  color: var(--cl-olive);
}

.maint-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
  margin: 0 0 12px;
}

.maint-card__row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 10px;
  align-items: baseline;
  font-size: 13px;
}

.maint-card__row--full {
  grid-column: 1 / -1;
}

.maint-card__k {
  color: var(--cl-olive);
  font-weight: 700;
  font-size: 12px;
}

.maint-card__v {
  color: var(--cl-near-black);
  word-break: break-word;
}

.maint-card__desc {
  padding-top: 10px;
  border-top: 1px solid var(--cl-border-cream);
}

.maint-card__desc-label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: var(--cl-olive);
  margin-bottom: 6px;
}

.maint-card__desc-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--cl-charcoal);
  white-space: pre-wrap;
  word-break: break-word;
}

.maint-card__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--cl-border-cream);
}

.maint-card__btn {
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

.maint-card__btn--danger {
  color: var(--cl-error);
  border-color: rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.06);
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

.strong {
  font-weight: 900;
}

.t {
  max-width: 360px;
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

/* 与 AppLayout 移动端断点一致 */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .sel {
    min-width: 0;
    width: 100%;
    font-size: 16px; /* 避免 iOS 聚焦时整页缩放 */
  }

  .toolbar-actions {
    flex-direction: column;
    width: 100%;
    align-items: stretch;
  }

  .toolbar .primary:not(.primary--link),
  .toolbar .primary--link,
  .toolbar .ghost--toolbar {
    width: 100%;
    min-height: 44px;
    padding-left: 14px;
    padding-right: 14px;
  }

  .tbl--desktop {
    display: none;
  }

  .maint-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .form--maintenance {
    grid-template-columns: 1fr;
    gap: 8px 0;
  }

  .form--maintenance label {
    margin-top: 4px;
    font-weight: 700;
  }

  .form--maintenance input,
  .form--maintenance select,
  .form--maintenance textarea {
    font-size: 16px;
  }
}
</style>
