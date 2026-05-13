<template>
  <div class="fuel-records">
    <header class="fuel-records__head">
      <h1 class="fuel-records__title">加油记录</h1>
      <p class="fuel-records__desc muted">
        登记加油信息。车牌选项来自<strong>车辆登记表（bus_vehicle）</strong>；数据库
        <code>bus_driver</code> 不含车牌字段，故此处与车辆主数据对齐，便于后续与油卡、里程对账。
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
        <label class="field__label" for="fuel-odometer">公里表读数</label>
        <div class="field__body">
          <input
            id="fuel-odometer"
            v-model="odometerDigits"
            type="text"
            class="field__input"
            inputmode="numeric"
            autocomplete="off"
            placeholder="仅可填写数字"
            maxlength="12"
            @input="odometerDigits = sanitizeOdometerValue(($event.target as HTMLInputElement).value)"
            @keydown="onOdometerKeydown"
            @paste="onOdometerPaste"
          />
        </div>
      </div>

      <div class="field field--row">
        <label class="field__label" for="fuel-datetime">加油日期</label>
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

      <div class="field field--row field--capture">
        <span class="field__label" id="fuel-photo-label">加油照片</span>
        <div class="field__body field__body--capture" aria-labelledby="fuel-photo-label">
        <MobileMediaCapture
          ref="captureRef"
          panel-aria-label="加油照片拍摄与预览"
          photo-heading="加油照片"
          photo-file-base="fuel_record_photo"
          :enable-video="false"
          :single-photo="true"
          :show-photo-download="false"
          photo-hint="每条记录仅可添加一张加油照片。拍照后预览在上方；可点「重新拍照」替换，或「清除照片」后重选。照片仅在当前页面预览，提交后由后续接口上传。"
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
        当前为前端表单演示，提交后不会写入数据库；后续可对接 <code>/api/v1/fuel</code> 等接口。
      </p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { listVehicles } from '@/api/vehicles'
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
  return raw.replace(/\D/g, '').slice(0, 12)
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
  const t = (e.clipboardData?.getData('text') ?? '').replace(/\D/g, '').slice(0, 12)
  odometerDigits.value = t
}

async function loadVehicles() {
  vehiclesLoading.value = true
  try {
    vehicles.value = await listVehicles({ limit: 200 })
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

  const plate = vehicleOptions.value.find((o) => o.id === vehicleId.value)?.label ?? `#${vehicleId.value}`
  const photo = captureRef.value?.getPhotoFile?.() ?? null

  submitting.value = true
  try {
    await new Promise((r) => setTimeout(r, 400))
    // 后续对接 POST /fuel/records 等：payload 含 vehicle_id, odometer, fueled_at, photo File
    console.info('[fuel-record demo]', {
      vehicleId: vehicleId.value,
      plate,
      odometer: odo,
      fueledAtDisplay: fuelDateDisplay.value,
      fueledAtLocal: fuelDateTimeLocal.value,
      photo: photo ? { name: photo.name, size: photo.size, type: photo.type } : null,
    })
    formMsg.value = {
      kind: 'ok',
      text: `已校验通过（演示）：${plate} · 里程 ${odo} km · ${fuelDateDisplay.value}${photo ? ' · 已选择加油照片' : ' · 未附照片'}`,
    }
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

.field__input::-webkit-datetime-edit-fields-wrapper {
  padding: 0;
}

.field__datetime-shell {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  border-radius: var(--fuel-control-radius);
  /* 不用 overflow:hidden，避免部分 WebView 裁剪原生日期弹层 */
  position: relative;
}

.field__input--datetime {
  display: block;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  margin: 0;
  position: relative;
  z-index: 0;
  text-align: start;
  direction: ltr;
  padding-left: var(--fuel-datetime-pad-x);
  padding-right: var(--fuel-datetime-pad-right-icon);
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

.field__body--capture :deep(.panel) {
  margin: 0;
}

/* 拍照主按钮改为描边样式，避免与下方「保存记录」实心主按钮视觉混淆 */
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

  .fuel-records {
    --fuel-control-h: 48px;
    --fuel-control-fs: 16px;
    --fuel-datetime-pad-x: 8px;
    --fuel-datetime-pad-right-icon: 2.15rem;
    max-width: 100%;
  }

  .field__datetime-shell {
    max-width: min(100%, calc(100vw - 2rem - env(safe-area-inset-left, 0px) - env(safe-area-inset-right, 0px)));
  }

  .field__input--datetime {
    max-width: 100%;
    /* 略收紧字距，部分机型仍会在 16px 下顶破宽度 */
    letter-spacing: -0.015em;
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

/* 超窄屏再收一档（折叠外屏、部分老年机浏览器） */
@media (max-width: 380px) {
  .fuel-records {
    --fuel-datetime-pad-x: 6px;
    --fuel-datetime-pad-right-icon: 2rem;
    --fuel-control-fs: 15px;
  }

  .field__input--datetime {
    font-size: 15px;
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
