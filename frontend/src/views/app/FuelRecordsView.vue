<template>
  <div class="fuel-records">
    <header class="fuel-records__head">
      <h1 class="fuel-records__title">加油记录</h1>
      <p class="fuel-records__eyebrow">移动登记 · 自动留痕</p>
      <p class="fuel-records__desc muted">现场登记车辆、里程与时间，照片将作为加油凭证安全保存。</p>
    </header>

    <form class="form" @submit.prevent="onSubmit">
      <div v-if="formMsg" class="form-msg" :class="`form-msg--${formMsg.kind}`" role="status">
        {{ formMsg.text }}
      </div>

      <div class="form-section-title"><span>01</span> 基本信息</div>

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
        <label class="field__label" for="fuel-odometer">公里表 <em>必填</em></label>
        <div class="field__body">
          <input
            id="fuel-odometer"
            v-model="odometerDigits"
            type="text"
            class="field__input"
            inputmode="numeric"
            autocomplete="off"
            placeholder="公里表读数"
            maxlength="10"
            @input="odometerDigits = sanitizeOdometerValue(($event.target as HTMLInputElement).value)"
            @keydown="onOdometerKeydown"
            @paste="onOdometerPaste"
          />
        </div>
      </div>

      <div class="field field--row">
        <label class="field__label" for="fuel-datetime">加油日期 <em>必填</em></label>
        <div class="field__body">
          <div class="field__datetime-shell">
            <input
              id="fuel-datetime"
              v-model="fuelDateTimeLocal"
              type="datetime-local"
              class="field__input field__input--datetime"
              step="60"
            />
          </div>
          <p class="field__format muted">显示格式：<strong>{{ fuelDateDisplay }}</strong></p>
        </div>
      </div>

      <div class="form-section-title form-section-title--media"><span>02</span> 加油小票照片</div>

      <div class="field field--row field--capture field--capture-only">
        <div class="field__body field__body--capture" aria-label="加油小票照片">
        <MobileMediaCapture
          ref="captureRef"
          compact
          panel-aria-label="加油小票照片拍摄与预览"
          photo-heading=""
          photo-file-base="fuel_record_photo"
          :photo-input-capture="false"
          :enable-video="false"
          :single-photo="true"
          :show-photo-download="false"
          photo-hint="将加油小票放置在里程表上，拍摄时应保证小票内容与公里表清晰可见。"
        />
        </div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn btn--primary" :disabled="submitting">
          {{ submitting ? '提交中…' : '保存记录' }}
        </button>
        <button type="button" class="btn btn--ghost" :disabled="submitting" @click="resetForm">重置表单</button>
      </div>

      <p class="form-foot muted">业务字段写入数据库；照片写入私有媒体存储，仅授权用户可访问。</p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { createFuelEntry } from '@/api/fuel'
import { listAllVehicles } from '@/api/vehicles'
import type { Vehicle } from '@/api/types'
import MobileMediaCapture from '@/components/MobileMediaCapture.vue'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'

const vehicles = ref<Vehicle[]>([])
const vehiclesLoading = ref(true)
const vehicleId = ref(0)

const odometerDigits = ref('')

const captureRef = ref<InstanceType<typeof MobileMediaCapture> | null>(null)

const fuelDateTimeLocal = ref('')

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

const fuelDateDisplay = computed(() => {
  const s = fuelDateTimeLocal.value.trim()
  if (!s) return 'YYYY-MM-DD HH:MM（请选择上方日期时间）'
  const [d, t] = s.split('T')
  if (!d) return s
  const hm = (t || '00:00').slice(0, 5)
  return `${d} ${hm}`
})

function pad2(n: number) {
  return String(n).padStart(2, '0')
}

function defaultLocalDatetime(): string {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

function sanitizeOdometerValue(raw: string): string {
  return raw.replace(/\D/g, '').slice(0, 10)
}

function onOdometerKeydown(e: KeyboardEvent) {
  const allowed =
    ['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(
      e.key,
    ) ||
    (e.ctrlKey || e.metaKey)
  if (allowed) return
  if (e.key.length === 1 && /\d/.test(e.key)) return
  e.preventDefault()
}

function onOdometerPaste(e: ClipboardEvent) {
  e.preventDefault()
  const t = (e.clipboardData?.getData('text') ?? '').replace(/\D/g, '').slice(0, 10)
  odometerDigits.value = t
}

async function loadVehicles() {
  vehiclesLoading.value = true
  try {
    vehicles.value = await listAllVehicles()
  } catch {
    vehicles.value = []
    formMsg.value = { kind: 'err', text: '车辆列表加载失败，请检查网络或稍后重试。' }
  } finally {
    vehiclesLoading.value = false
  }
}

function resetForm() {
  vehicleId.value = 0
  odometerDigits.value = ''
  fuelDateTimeLocal.value = defaultLocalDatetime()
  captureRef.value?.clearPhoto()
  formMsg.value = null
}

async function onSubmit() {
  formMsg.value = null
  if (!vehicleId.value) {
    formMsg.value = { kind: 'err', text: '请选择车牌号。' }
    return
  }
  const odo = sanitizeOdometerValue(odometerDigits.value)
  if (!odo) {
    formMsg.value = { kind: 'err', text: '请填写公里表读数（仅数字）。' }
    return
  }
  if (!fuelDateTimeLocal.value) {
    formMsg.value = { kind: 'err', text: '请选择加油日期与时间。' }
    return
  }

  const photo = captureRef.value?.getPhotoFile?.() ?? null

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('vehicle_id', String(vehicleId.value))
    fd.append('odometer', odo)
    fd.append('fueled_at', new Date(fuelDateTimeLocal.value).toISOString())
    if (photo) fd.append('photo', photo)
    const record = await createFuelEntry(fd)
    formMsg.value = {
      kind: 'ok',
      text: `保存成功：${record.plate_number} · ${record.odometer} km · ${fuelDateDisplay.value}${record.has_photo ? ' · 凭证已上传' : ''}`,
    }
    vehicleId.value = 0
    odometerDigits.value = ''
    fuelDateTimeLocal.value = defaultLocalDatetime()
    captureRef.value?.clearPhoto()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formMsg.value = { kind: 'err', text: err.response?.data?.detail || '保存失败，请检查网络后重试。' }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fuelDateTimeLocal.value = defaultLocalDatetime()
  void loadVehicles()
})
</script>

<style scoped>
.fuel-records {
  --fuel-control-h: 48px;
  --fuel-control-radius: 10px;
  --fuel-control-fs: 0.9375rem;
  --fuel-label-w: 7.25rem;
  /* 避免在窄屏 + 侧栏/安全区内，子元素按「最小内容宽度」撑破视口 */
  --fuel-datetime-pad-x: 10px;
  --fuel-datetime-pad-right-icon: 2.35rem;

  width: 100%;
  max-width: min(640px, 100%);
  min-width: 0;
  margin: 0 auto;
  padding-left: max(0px, env(safe-area-inset-left, 0px));
  padding-right: max(0px, env(safe-area-inset-right, 0px));
  box-sizing: border-box;
  overflow-x: hidden;
}

.fuel-records__head {
  margin-bottom: 1.25rem;
}

.fuel-records__title {
  margin: 0 0 0.35rem;
  font-size: clamp(1.1rem, 2.5vw, 1.35rem);
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
}

.fuel-records__eyebrow {
  margin: 0 0 0.25rem;
  color: var(--cl-terracotta, #c96442);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.fuel-records__desc {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.fuel-records__desc code {
  font-size: 0.85em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(142, 132, 109, 0.12);
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

.form-section-title--media {
  margin-top: 1.5rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(142, 132, 109, 0.18);
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

.field__input::-webkit-datetime-edit-fields-wrapper {
  padding: 0;
}

.field__datetime-shell {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  height: var(--fuel-control-h);
  min-height: var(--fuel-control-h);
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  border-radius: var(--fuel-control-radius);
  background: rgba(255, 255, 255, 0.95);
  position: relative;
}

.field__datetime-shell:focus-within {
  outline: 2px solid var(--cl-terracotta, #c96442);
  outline-offset: -2px;
}

.field__input--datetime {
  display: block;
  position: absolute;
  inset: 0;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  height: 100%;
  min-height: 0;
  margin: 0;
  z-index: 0;
  text-align: start;
  direction: ltr;
  border: 0;
  border-radius: inherit;
  background: transparent;
  -webkit-appearance: none;
  appearance: none;
  padding-left: var(--fuel-datetime-pad-x);
  padding-right: var(--fuel-datetime-pad-right-icon);
}

.field__input--datetime:focus {
  outline: none;
}

/* WebKit：压缩分段日期时间的水平占位，减少窄屏横向溢出 */
.field__input--datetime::-webkit-datetime-edit {
  padding: 0;
  min-width: 0;
}

.field__input--datetime::-webkit-datetime-edit-fields-wrapper {
  padding: 0;
  min-width: 0;
}

.field__input--datetime::-webkit-datetime-edit-text {
  padding: 0 1px;
}

.field__input--datetime::-webkit-datetime-edit-month-field,
.field__input--datetime::-webkit-datetime-edit-day-field,
.field__input--datetime::-webkit-datetime-edit-year-field,
.field__input--datetime::-webkit-datetime-edit-hour-field,
.field__input--datetime::-webkit-datetime-edit-minute-field {
  padding: 0 1px;
}

/* 日历图标不占文档流宽度，为文本留出稳定右侧留白 */
.field__input--datetime::-webkit-calendar-picker-indicator {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  margin: 0;
  padding: 0;
  width: 1.35rem;
  height: 1.35rem;
  cursor: pointer;
  opacity: 0.88;
}

.field__format {
  margin: 0.4rem 0 0;
  font-size: 0.8125rem;
  line-height: 1.45;
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

/* 拍照主按钮改为描边样式，避免与下方「保存记录」实心主按钮视觉混淆 */
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
  .fuel-records__head {
    display: none;
  }

  .fuel-records {
    display: flex;
    flex-direction: column;
    min-height: 100%;
  }

  .form {
    display: flex;
    flex: 1 0 auto;
    flex-direction: column;
    padding: 1rem;
    border-radius: 16px;
    box-shadow: 0 6px 24px rgba(35, 32, 27, 0.055);
  }

  .fuel-records {
    --fuel-control-h: 48px;
    --fuel-control-fs: 16px;
    --fuel-datetime-pad-x: 8px;
    --fuel-datetime-pad-right-icon: 2.15rem;
    max-width: 100%;
  }

  .form-section-title {
    gap: 0.45rem;
    margin-bottom: 0.9rem;
    font-size: 0.9rem;
  }

  .form-section-title span {
    width: 1.6rem;
    height: 1.6rem;
    border-radius: 8px;
    font-size: 0.72rem;
  }

  .form-section-title--media {
    margin-top: 1rem;
    padding-top: 0.9rem;
  }

  .field {
    margin-bottom: 0.9rem;
  }

  .field__label {
    font-size: 0.86rem;
  }

  .field__input {
    min-height: var(--fuel-control-h);
    padding: 10px 11px;
  }

  .field__format {
    display: none;
  }

  .field__datetime-shell {
    width: 100%;
    max-width: 100%;
    min-width: 0;
  }

  .field__input--datetime {
    width: 100%;
    max-width: 100%;
    min-width: 0;
    height: var(--fuel-control-h);
    box-sizing: border-box;
    margin: 0;
    letter-spacing: normal;
    overflow: hidden;
  }

  .field--capture {
    margin-bottom: 0.9rem;
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
    margin-top: 0.25rem;
    padding-top: 1rem;
    gap: 0.5rem;
    background: transparent;
  }

  .form-actions .btn {
    width: auto;
    justify-content: center;
    min-height: 46px;
    padding: 0.5rem 0.7rem;
    font-size: 0.94rem;
  }

  .form-foot {
    display: none;
  }
}

/* 超窄屏再收一档（折叠外屏、部分老年机浏览器） */
@media (max-width: 380px) {
  .fuel-records {
    --fuel-datetime-pad-x: 6px;
    --fuel-datetime-pad-right-icon: 2rem;
    --fuel-control-fs: 16px;
  }

  .field__input--datetime {
    font-size: 16px;
  }
}
</style>

<style>
/* 与 .field__input 同高同宽：加油 / 维修等台账表单共用 */
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
