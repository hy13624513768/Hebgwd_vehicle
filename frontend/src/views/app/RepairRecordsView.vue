<template>
  <div class="repair-records">
    <header class="repair-records__head">
      <h1 class="repair-records__title">维修记录</h1>
      <p class="repair-records__eyebrow">现场上报 · 智能归档</p>
      <p class="repair-records__desc muted">
        先登记车辆与驾驶员，再补充现场资料。结算单提交后自动识别并归档到维修保养。
      </p>
    </header>

    <form class="form" @submit.prevent="onSubmit">
      <div v-if="formMsg" class="form-msg" :class="`form-msg--${formMsg.kind}`" role="status">
        {{ formMsg.text }}
      </div>

      <div class="form-section-title"><span>01</span> 送修信息</div>

      <div class="field field--row">
        <label class="field__label">车牌号 <em>必填</em></label>
        <div class="field__body">
          <div v-if="vehiclesLoading" class="muted field__placeholder">正在加载车辆列表…</div>
          <SearchableSelect
            v-else
            v-model="vehicleId"
            class="field__control searchable-select--block"
            trigger-class="searchable-select--ledger-form"
            :options="vehicleOptions"
            allow-empty
            empty-label="请选择车牌"
            search-placeholder="输入车牌号、品牌、车型等关键字…"
          />
        </div>
      </div>

      <div class="field field--row">
        <label class="field__label">驾驶员 <em>必填</em></label>
        <div class="field__body">
          <div v-if="driversLoading" class="muted field__placeholder">正在加载驾驶员列表…</div>
          <SearchableSelect
            v-else
            v-model="driverId"
            class="field__control searchable-select--block"
            trigger-class="searchable-select--ledger-form"
            :options="driverOptions"
            allow-empty
            empty-label="请选择驾驶员"
            search-placeholder="输入姓名、手机号、身份证号等关键字…"
          />
        </div>
      </div>

      <div class="field field--row">
        <label class="field__label" for="repair-order-no">维修单号 <em>必填</em></label>
        <div class="field__body">
          <input
            id="repair-order-no"
            v-model="repairOrderNo"
            type="text"
            class="field__input"
            autocomplete="off"
            placeholder="例如：W-20260804-001"
            pattern="W-[0-9]{8}-.*"
            title="格式应为 W-8位数字-后续编号，例如 W-20260804-001"
            maxlength="128"
          />
        </div>
      </div>

      <div class="form-section-title form-section-title--media">
        <span>02</span> 驾驶员与车辆合影 <em>必填</em>
      </div>

      <p class="form-section-hint">请将维修材料摆放好，与驾驶员和车辆一并拍照，最多上传 5 张。</p>

      <div class="field field--row field--capture field--capture-only">
        <div class="field__body field__body--capture">
          <MobileMediaCapture
            ref="captureDuoRef"
            compact
            panel-aria-label="驾驶员、车辆及维修材料合影"
            photo-heading=""
            photo-file-base="repair_duo_photo"
            :photo-input-capture="false"
            :enable-video="false"
            :single-photo="false"
            :max-photos="5"
            :show-photo-download="false"
            photo-hint=""
          />
        </div>
      </div>

      <div class="form-section-title form-section-title--media">
        <span>03</span> 结算单照片 <em>必填</em>
      </div>

      <div class="field field--row field--capture field--capture-only">
        <div class="field__body field__body--capture">
          <MobileMediaCapture
            ref="captureSettlementRef"
            compact
            panel-aria-label="结算单照片"
            photo-heading=""
            photo-file-base="repair_settlement_photo"
            :photo-input-capture="false"
            :enable-video="false"
            :single-photo="true"
            :show-photo-download="false"
            photo-hint=""
          />
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn--primary" :disabled="submitting">
          {{ submitting ? '提交中…' : '保存记录' }}
        </button>
        <button type="button" class="btn btn--ghost" :disabled="submitting" @click="resetForm()">重置表单</button>
      </div>

      <p class="form-foot muted">媒体文件存入私有存储；提交后可在「费用管理 → 维修保养」查看识别结果。</p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { createRepairRecord } from '@/api/repairRecords'
import { listAllDrivers } from '@/api/drivers'
import { listAllVehicles } from '@/api/vehicles'
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
const repairOrderPattern = /^W-\d{8}-.*$/

const captureDuoRef = ref<InstanceType<typeof MobileMediaCapture> | null>(null)
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

async function loadVehicles() {
  vehiclesLoading.value = true
  try {
    vehicles.value = await listAllVehicles()
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
    drivers.value = await listAllDrivers()
  } catch {
    drivers.value = []
    formMsg.value = { kind: 'err', text: '驾驶员列表加载失败，请稍后重试。' }
  } finally {
    driversLoading.value = false
  }
}

function resetForm(clearMessage = true) {
  vehicleId.value = 0
  driverId.value = 0
  repairOrderNo.value = ''
  captureDuoRef.value?.clearPhoto()
  captureSettlementRef.value?.clearPhoto()
  if (clearMessage) formMsg.value = null
}

async function onSubmit() {
  formMsg.value = null
  if (!vehicleId.value) {
    formMsg.value = { kind: 'err', text: '请选择车牌号。' }
    return
  }
  if (!driverId.value) {
    formMsg.value = { kind: 'err', text: '请选择驾驶员。' }
    return
  }
  const order = repairOrderNo.value.trim()
  if (!order) {
    formMsg.value = { kind: 'err', text: '请填写维修单号。' }
    return
  }
  if (!repairOrderPattern.test(order)) {
    formMsg.value = { kind: 'err', text: '维修单号格式不正确，应为 W-8位数字-后续编号，例如 W-20260804-001。' }
    return
  }
  const duoPhotos = captureDuoRef.value?.getPhotoFiles?.() ?? []
  const settle = captureSettlementRef.value?.getPhotoFile?.() ?? null

  if (!duoPhotos.length) {
    formMsg.value = { kind: 'err', text: '请上传驾驶员、车辆及维修材料合影。' }
    return
  }
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
    for (const photo of duoPhotos) fd.append('photo_duo', photo)
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
    if (status === 'done') resetForm(false)
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

.repair-records__eyebrow {
  margin: 0 0 0.25rem;
  color: var(--cl-terracotta, #c96442);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
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
  min-width: 0;
  margin-bottom: 1.1rem;
}

.field--row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  min-width: 0;
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

.field__label em {
  margin-left: 0.2rem;
  color: var(--cl-terracotta, #c96442);
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 700;
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  margin: 0 0 1rem;
  color: var(--cl-charcoal, #2c2b28);
  font-size: 0.9rem;
  font-weight: 700;
}

.form-section-title span {
  display: inline-grid;
  width: 1.75rem;
  height: 1.75rem;
  place-items: center;
  border-radius: 8px;
  background: rgba(201, 100, 66, 0.12);
  color: var(--cl-terracotta, #c96442);
  font-size: 0.72rem;
}

.form-section-title em {
  color: var(--cl-terracotta, #c96442);
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 700;
}

.form-section-title--media {
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(142, 132, 109, 0.18);
}

.form-section-hint {
  margin: -0.45rem 0 0.7rem;
  color: var(--cl-olive, #6b6558);
  font-size: 0.75rem;
  line-height: 1.45;
}

.field__body {
  min-width: 0;
  max-width: 100%;
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
  outline-offset: -2px;
}

.field__body--capture :deep(.mobile-capture) {
  width: 100%;
}

.field--capture-only .field__body {
  grid-column: 1 / -1;
}

.field__body--capture :deep(.panel) {
  margin: 0;
}

.field__body--capture :deep(.actions .btn.primary) {
  background: var(--cl-terracotta, #c96442);
  color: #fff;
  border: 1px solid var(--cl-terracotta, #c96442);
  box-shadow: 0 2px 6px rgba(201, 100, 66, 0.18);
  font-weight: 650;
}

.field__body--capture :deep(.actions .btn.primary:hover) {
  background: #b95739;
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
  .repair-records__head {
    display: none;
  }

  .form {
    padding: clamp(0.65rem, 1.2dvh, 1rem);
    border-radius: 16px;
    box-shadow: 0 6px 24px rgba(35, 32, 27, 0.055);
  }

  .repair-records {
    --fuel-control-h: clamp(44px, 5.2dvh, 48px);
    --fuel-control-fs: 16px;
    max-width: 100%;
  }

  .form-section-title {
    gap: 0.45rem;
    margin-bottom: clamp(0.4rem, 0.85dvh, 0.9rem);
    font-size: 0.9rem;
  }

  .form-section-title span {
    width: 1.6rem;
    height: 1.6rem;
    border-radius: 8px;
    font-size: 0.72rem;
  }

  .form-section-title--media {
    margin-top: clamp(0.45rem, 0.9dvh, 1rem);
    padding-top: clamp(0.45rem, 0.9dvh, 0.9rem);
  }

  .field {
    margin-bottom: clamp(0.45rem, 0.9dvh, 0.9rem);
  }

  .field__label {
    font-size: 0.86rem;
  }

  .field__input {
    min-height: var(--fuel-control-h);
    padding: 10px 11px;
  }

  .field--capture {
    margin-bottom: clamp(0.35rem, 0.7dvh, 0.65rem);
  }

  .field__body--capture :deep(.actions) {
    flex-direction: row;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0;
  }

  .field__body--capture :deep(.actions .btn) {
    width: auto;
    min-height: 40px;
  }

  .field__body--capture :deep(.actions .btn--link) {
    width: auto;
  }

  .form-actions {
    display: grid;
    grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
    margin-top: 0;
    padding-top: clamp(0.55rem, 1dvh, 1rem);
    gap: 0.5rem;
    background: transparent;
  }

  .form-actions .btn {
    width: auto;
    justify-content: center;
    min-height: 44px;
    padding: 0.45rem 0.7rem;
    font-size: 0.9rem;
  }

  .form-foot {
    display: none;
  }
}

@media (max-width: 559px) and (max-height: 760px) {
  .form-section-title span {
    width: 1.45rem;
    height: 1.45rem;
  }

  .field__body--capture :deep(.actions .btn) {
    min-height: 38px;
    padding-top: 0.35rem;
    padding-bottom: 0.35rem;
  }

  .form-actions .btn {
    min-height: 42px;
  }
}

@media (max-width: 380px) {
  .repair-records {
    --fuel-control-fs: 16px;
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

@media (max-width: 559px) {
  :is(.fuel-records, .repair-records) .searchable-select .searchable-select__trigger.searchable-select--ledger-form {
    min-height: var(--fuel-control-h, 48px);
    padding: 10px 11px;
  }
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
