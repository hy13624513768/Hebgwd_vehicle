<template>
  <div class="repair-records">
    <header class="repair-records__head">
      <h1 class="repair-records__title">维修记录</h1>
      <p class="repair-records__desc muted">
        登记送修信息并上传结算单照片；保存后系统将<strong>自动调用 AI 识别</strong>结算单，结果流转至「维修保养」页按词条归类展示。
      </p>
    </header>

    <form class="form" @submit.prevent="onSubmit">
      <div v-if="formMsg" class="form-msg" :class="`form-msg--${formMsg.kind}`" role="status">
        {{ formMsg.text }}
      </div>

      <div class="field field--row">
        <label class="field__label">车牌号</label>
        <div class="field__body">
          <div v-if="vehiclesLoading" class="muted field__placeholder">正在加载车辆列表…</div>
          <SearchableSelect
            v-else
            v-model="vehicleId"
            class="field__control"
            trigger-class="searchable-select--block searchable-select--ledger-form"
            :options="vehicleOptions"
            allow-empty
            empty-label="请选择车牌"
            search-placeholder="输入车牌号、品牌、车型等关键字…"
          />
        </div>
      </div>

      <div class="field field--row">
        <label class="field__label" for="repair-order-no">维修单号</label>
        <div class="field__body">
          <input
            id="repair-order-no"
            v-model="repairOrderNo"
            type="text"
            class="field__input"
            autocomplete="off"
            placeholder="纸质或系统维修单号"
            maxlength="128"
          />
        </div>
      </div>

      <div class="field field--row">
        <label class="field__label">驾驶员</label>
        <div class="field__body">
          <div v-if="driversLoading" class="muted field__placeholder">正在加载驾驶员列表…</div>
          <SearchableSelect
            v-else
            v-model="driverId"
            class="field__control"
            trigger-class="searchable-select--block searchable-select--ledger-form"
            :options="driverOptions"
            allow-empty
            empty-label="请选择驾驶员"
            search-placeholder="输入姓名、手机号、身份证号等关键字…"
          />
        </div>
      </div>

      <div class="field field--row field--capture">
        <span class="field__label" id="repair-label-duo">驾驶员与车辆合影</span>
        <div class="field__body field__body--capture" aria-labelledby="repair-label-duo">
          <MobileMediaCapture
            ref="captureDuoRef"
            panel-aria-label="驾驶员与车辆合影"
            photo-heading="驾驶员与车辆合影"
            photo-file-base="repair_duo_photo"
            :enable-video="false"
            :single-photo="true"
            :show-photo-download="false"
            photo-hint="每条记录限一张。建议包含驾驶员与车牌同框，便于核对。可「重新拍照」替换或「清除照片」后重选。"
          />
        </div>
      </div>

      <div class="field field--row field--capture">
        <span class="field__label" id="repair-label-item">维修项目（照片 / 视频）</span>
        <div class="field__body field__body--capture" aria-labelledby="repair-label-item">
          <MobileMediaCapture
            ref="captureRepairItemRef"
            panel-aria-label="维修项目照片与视频"
            photo-heading="维修项目照片"
            video-heading="维修项目视频"
            photo-file-base="repair_item_photo"
            video-file-base="repair_item_video"
            :enable-video="true"
            :single-photo="true"
            :single-video="true"
            :show-photo-download="false"
            :show-video-download="false"
            :video-input-capture="false"
            photo-hint="限一张：工单、报价单上的维修项目明细等。后续可对接 OCR 或结构化解析。"
            video-hint="限一段：点击按钮可在支持的环境下录像，或从相册选取已有视频（未加 capture，便于系统提供「拍摄 / 文件」等选项）。"
          />
        </div>
      </div>

      <div class="field field--row field--capture">
        <span class="field__label" id="repair-label-settle">结算单照片</span>
        <div class="field__body field__body--capture" aria-labelledby="repair-label-settle">
          <MobileMediaCapture
            ref="captureSettlementRef"
            panel-aria-label="结算单照片"
            photo-heading="结算单照片"
            photo-file-base="repair_settlement_photo"
            :enable-video="false"
            :single-photo="true"
            :show-photo-download="false"
            photo-hint="限一张：结算单、发票等。提交后将自动 AI 识别并归类到维修词条。"
          />
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn--primary" :disabled="submitting">
          {{ submitting ? '提交中…' : '保存记录' }}
        </button>
        <button type="button" class="btn btn--ghost" :disabled="submitting" @click="resetForm">重置表单</button>
      </div>

      <p class="form-foot muted">
        提交后结算单会自动识别；可在「费用管理 → 维修保养」查看归类结果。
      </p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { createRepairRecord } from '@/api/repairRecords'
import { listDrivers } from '@/api/drivers'
import { listVehicles } from '@/api/vehicles'
import type { Driver, Vehicle } from '@/api/types'
import MobileMediaCapture from '@/components/MobileMediaCapture.vue'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'

const vehicles = ref<Vehicle[]>([])
const vehiclesLoading = ref(true)
const vehicleId = ref(0)

const drivers = ref<Driver[]>([])
const driversLoading = ref(true)
const driverId = ref(0)

const repairOrderNo = ref('')

const captureDuoRef = ref<InstanceType<typeof MobileMediaCapture> | null>(null)
const captureRepairItemRef = ref<InstanceType<typeof MobileMediaCapture> | null>(null)
const captureSettlementRef = ref<InstanceType<typeof MobileMediaCapture> | null>(null)

const submitting = ref(false)
const formMsg = ref<{ kind: 'ok' | 'err'; text: string } | null>(null)

const vehicleOptions = computed<SearchableOption[]>(() =>
  vehicles.value.map((v) => ({
    id: v.id,
    label: v.plate_number,
    keywords: [v.plate_number, v.brand, v.model, v.org_unit, v.vehicle_class, v.vehicle_type_label]
      .filter(Boolean)
      .join(' '),
  })),
)

const driverOptions = computed<SearchableOption[]>(() =>
  drivers.value.map((d) => ({
    id: d.id,
    label: d.name,
    keywords: [d.name, d.phone, d.id_card ?? '', d.license_type, d.status].filter(Boolean).join(' '),
  })),
)

function driverDisplayName(): string {
  const d = drivers.value.find((x) => x.id === driverId.value)
  return d ? `${d.name}（${d.phone}）` : `#${driverId.value}`
}

async function loadVehicles() {
  vehiclesLoading.value = true
  try {
    vehicles.value = await listVehicles({ limit: 200 })
  } catch {
    vehicles.value = []
    formMsg.value = { kind: 'err', text: '车辆列表加载失败，请稍后重试。' }
  } finally {
    vehiclesLoading.value = false
  }
}

async function loadDrivers() {
  driversLoading.value = true
  try {
    const { items } = await listDrivers({ limit: 200 })
    drivers.value = items
  } catch {
    drivers.value = []
    formMsg.value = { kind: 'err', text: '驾驶员列表加载失败，请稍后重试。' }
  } finally {
    driversLoading.value = false
  }
}

function resetForm() {
  vehicleId.value = 0
  driverId.value = 0
  repairOrderNo.value = ''
  captureDuoRef.value?.clearPhoto()
  captureRepairItemRef.value?.clearPhoto()
  captureRepairItemRef.value?.clearVideo()
  captureSettlementRef.value?.clearPhoto()
  formMsg.value = null
}

async function onSubmit() {
  formMsg.value = null
  if (!vehicleId.value) {
    formMsg.value = { kind: 'err', text: '请选择车牌号。' }
    return
  }
  const order = repairOrderNo.value.trim()
  if (!order) {
    formMsg.value = { kind: 'err', text: '请填写维修单号。' }
    return
  }
  if (!driverId.value) {
    formMsg.value = { kind: 'err', text: '请选择驾驶员。' }
    return
  }

  const duo = captureDuoRef.value?.getPhotoFile?.() ?? null
  const itemPhoto = captureRepairItemRef.value?.getPhotoFile?.() ?? null
  const itemVideo = captureRepairItemRef.value?.getVideoFile?.() ?? null
  const settle = captureSettlementRef.value?.getPhotoFile?.() ?? null

  if (!settle) {
    formMsg.value = { kind: 'err', text: '请上传结算单照片（AI 识别必需）。' }
    return
  }

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('vehicle_id', String(vehicleId.value))
    fd.append('repair_order_no', order)
    fd.append('driver_id', String(driverId.value))
    fd.append('auto_recognize', 'true')
    if (duo) fd.append('photo_duo', duo)
    if (itemPhoto) fd.append('photo_item', itemPhoto)
    if (itemVideo) fd.append('photo_item_video', itemVideo)
    if (settle) fd.append('photo_settlement', settle)

    const record = await createRepairRecord(fd)
    const st = record.settlement
    const lines = st?.lines?.length ?? 0
    const status = st?.recognition_status ?? record.status
    formMsg.value = {
      kind: status === 'done' ? 'ok' : 'err',
      text:
        status === 'done'
          ? `提交成功！已识别 ${lines} 项维修明细，可在「维修保养」页查看归类。`
          : `已保存记录，但识别${status === 'failed' ? '失败' : '未完成'}：${st?.recognition_error || record.status}`,
    }
    if (status === 'done') resetForm()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formMsg.value = { kind: 'err', text: err.response?.data?.detail || '提交失败，请稍后重试。' }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadVehicles()
  void loadDrivers()
})
</script>

<style scoped>
/* 与加油台账对齐的变量名，便于共用全局 SearchableSelect 样式 */
.repair-records {
  --fuel-control-h: 48px;
  --fuel-control-radius: 10px;
  --fuel-control-fs: 0.9375rem;
  --fuel-label-w: 7.25rem;

  width: 100%;
  max-width: min(640px, 100%);
  min-width: 0;
  margin: 0 auto;
  padding-left: max(0px, env(safe-area-inset-left, 0px));
  padding-right: max(0px, env(safe-area-inset-right, 0px));
  box-sizing: border-box;
  overflow-x: hidden;
}

.repair-records__head {
  margin-bottom: 1.25rem;
}

.repair-records__title {
  margin: 0 0 0.35rem;
  font-size: clamp(1.1rem, 2.5vw, 1.35rem);
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
}

.repair-records__desc {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.repair-records__desc code {
  font-size: 0.85em;
}

.muted {
  color: var(--cl-olive, #6b6558);
}

.form {
  padding: 1.15rem 1.2rem;
  padding-bottom: max(1.15rem, env(safe-area-inset-bottom, 0px));
  border-radius: 14px;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
  background: rgba(253, 252, 247, 0.92);
  box-shadow: 0 4px 22px rgba(20, 20, 19, 0.06);
  box-sizing: border-box;
  min-width: 0;
  max-width: 100%;
}

.form-msg {
  margin-bottom: 1rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  font-size: 0.875rem;
  line-height: 1.45;
}

.form-msg--ok {
  background: rgba(60, 120, 80, 0.12);
  color: #2d4a33;
  border: 1px solid rgba(60, 120, 80, 0.25);
}

.form-msg--err {
  background: rgba(180, 60, 50, 0.1);
  color: #7a2c24;
  border: 1px solid rgba(180, 60, 50, 0.28);
}

.field {
  margin-bottom: 1.1rem;
}

.field--row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.35rem 0;
  align-items: start;
}

.field__label {
  display: block;
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
  line-height: 1.3;
}

.field__body {
  min-width: 0;
  width: 100%;
}

.field__placeholder {
  display: flex;
  align-items: center;
  min-height: var(--fuel-control-h);
  padding: 11px 12px;
  box-sizing: border-box;
  font-size: 0.875rem;
}

.field__control {
  display: block;
  width: 100%;
}

.field__input {
  display: block;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  min-height: var(--fuel-control-h);
  padding: 11px 12px;
  border-radius: var(--fuel-control-radius);
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  font: inherit;
  font-size: var(--fuel-control-fs);
  line-height: 1.25;
  background: rgba(255, 255, 255, 0.95);
  color: var(--cl-charcoal, #2c2b28);
}

.field__input:focus {
  outline: 2px solid var(--cl-terracotta, #c96442);
  outline-offset: 1px;
}

.field__body--capture :deep(.mobile-capture) {
  width: 100%;
}

.field__body--capture :deep(.panel) {
  margin: 0;
}

.field__body--capture :deep(.actions .btn.primary) {
  background: rgba(255, 255, 255, 0.98);
  color: var(--cl-terracotta, #c96442);
  border: 2px solid var(--cl-terracotta, #c96442);
  box-shadow: none;
  font-weight: 600;
}

.field__body--capture :deep(.actions .btn.primary:hover) {
  background: rgba(201, 100, 66, 0.08);
}

.field__body--capture :deep(.actions .btn.ghost) {
  background: rgba(255, 255, 255, 0.92);
}

@media (min-width: 560px) {
  .field--row {
    grid-template-columns: var(--fuel-label-w) minmax(0, 1fr);
    gap: 0.5rem 0.85rem;
    align-items: start;
  }

  .field--row .field__label {
    padding-top: calc((var(--fuel-control-h) - 1.3em) / 2);
    text-align: right;
  }

  .field--capture.field--row .field__label {
    padding-top: 0.65rem;
    align-self: start;
  }
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.25rem;
  padding-top: 1.15rem;
  border-top: 1px solid rgba(142, 132, 109, 0.2);
  clear: both;
}

.btn {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0.55rem 1.15rem;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: inherit;
  box-sizing: border-box;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn--primary {
  border: 1px solid rgba(201, 100, 66, 0.5);
  background: var(--cl-terracotta, #c96442);
  color: #fff;
  box-shadow: 0 2px 8px rgba(201, 100, 66, 0.22);
}

.btn--ghost {
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  background: rgba(255, 255, 255, 0.9);
  color: var(--cl-charcoal, #2c2b28);
}

.form-foot {
  margin: 1rem 0 0;
  font-size: 0.75rem;
  line-height: 1.5;
}

.form-foot code {
  font-size: 0.9em;
}

@media (max-width: 559px) {
  .form {
    padding: 1rem 0.85rem;
    border-radius: 12px;
  }

  .repair-records {
    --fuel-control-h: 48px;
    --fuel-control-fs: 16px;
    max-width: 100%;
  }

  .field--capture {
    margin-bottom: 1.35rem;
  }

  .field__body--capture :deep(.actions) {
    flex-direction: column;
    align-items: stretch;
    gap: 0.6rem;
    margin-bottom: 0;
  }

  .field__body--capture :deep(.actions .btn) {
    width: 100%;
    min-height: 48px;
  }

  .field__body--capture :deep(.actions .btn--link) {
    width: 100%;
  }

  .form-actions {
    flex-direction: column;
    align-items: stretch;
    margin-top: 1.5rem;
    padding-top: 1.25rem;
    gap: 0.75rem;
  }

  .form-actions .btn {
    width: 100%;
    justify-content: center;
    min-height: 50px;
    font-size: 1rem;
  }
}

@media (max-width: 380px) {
  .repair-records {
    --fuel-control-fs: 15px;
  }
}
</style>

<style>
/* 本页独立打包时需自带与加油页一致的台账下拉样式（与 FuelRecordsView 中 :is 规则保持同步） */
:is(.fuel-records, .repair-records) .searchable-select.searchable-select--block {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  flex: 1 1 auto !important;
}

:is(.fuel-records, .repair-records) .searchable-select .searchable-select__trigger.searchable-select--ledger-form {
  width: 100%;
  box-sizing: border-box;
  min-height: var(--fuel-control-h, 48px);
  padding: 11px 12px;
  border-radius: var(--fuel-control-radius, 10px);
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  font-size: var(--fuel-control-fs, 0.9375rem);
  line-height: 1.25;
  background: rgba(255, 255, 255, 0.95);
  color: var(--cl-charcoal, #2c2b28);
}

:is(.fuel-records, .repair-records)
  .searchable-select
  .searchable-select__trigger.searchable-select--ledger-form:focus-visible,
:is(.fuel-records, .repair-records)
  .searchable-select.is-open
  .searchable-select__trigger.searchable-select--ledger-form {
  outline: 2px solid var(--cl-terracotta, #c96442);
  outline-offset: 1px;
  border-color: var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  box-shadow: none;
}

@media (max-width: 559px) {
  :is(.fuel-records, .repair-records) .searchable-select .searchable-select__dropdown {
    min-width: 100% !important;
    width: 100% !important;
    max-width: calc(100vw - 32px) !important;
    left: 0 !important;
    right: auto;
  }
}
</style>
