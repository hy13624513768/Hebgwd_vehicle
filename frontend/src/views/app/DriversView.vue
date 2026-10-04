<template>
  <div class="drivers-view">
    <div class="toolbar">
      <div class="toolbar__search-wrap">
        <span class="toolbar__search-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2" />
            <path d="M20 20l-4.2-4.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </span>
        <input
          v-model.trim="q"
          class="toolbar__search"
          type="search"
          enterkeyhint="search"
          autocomplete="off"
          placeholder="姓名 / 电话 / 身份证号"
          aria-label="搜索驾驶员：姓名、电话或身份证号"
          @keydown.enter.prevent="loadList"
        />
      </div>
      <div class="toolbar__filters">
        <div class="toolbar__field">
          <span class="toolbar-label">车间</span>
          <SearchableSelect
            v-model="filterWorkshopId"
            class="toolbar-select"
            :options="workshopFilterOptions"
            allow-empty
            empty-label="全部车间"
            search-placeholder="输入车间关键字…"
          />
        </div>
        <div class="toolbar__field">
          <span class="toolbar-label">准驾</span>
          <SearchableSelect
            v-model="filterLicenseId"
            class="toolbar-select"
            :options="licenseTypeOptions"
            allow-empty
            empty-label="全部驾驶员"
            search-placeholder="输入准驾关键字…"
          />
        </div>
      </div>
      <div class="toolbar__actions">
        <button type="button" class="primary toolbar__btn-query" :disabled="loading" @click="loadList">查询</button>
        <button
          type="button"
          class="ghost toolbar__btn-analysis"
          @click="openManagementAnalysis"
        >
          数据分析
          <span aria-hidden="true">→</span>
        </button>
        <button
          v-if="canEditDriverRecords"
          type="button"
          class="primary toolbar__btn-new"
          :disabled="loading"
          @click="openCreate"
        >
          新增驾驶员
        </button>
        <button type="button" class="ghost toolbar__btn-refresh" :disabled="loading" @click="loadAll">刷新</button>
      </div>
    </div>

    <div v-if="msg" class="msg">{{ msg }}</div>
    <div v-if="loading" class="muted">加载中…</div>

    <div v-else class="list-stack">
    <div class="list-wrap">
      <table class="tbl tbl--desktop">
        <thead>
          <tr>
            <th>姓名</th>
            <th>电话</th>
            <th>准驾</th>
            <th>车间</th>
            <th>状态</th>
            <th>年龄</th>
            <th>身份证号</th>
            <th>健康体检报告</th>
            <th>外包人员入职手续</th>
            <th class="w">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rows.length === 0">
            <td colspan="10" class="empty-hint">暂无数据，可调整筛选后点击查询。</td>
          </tr>
          <template v-for="group in driverGroups" :key="`desktop-${group.workshop}`">
          <tr class="driver-workshop-row">
            <td colspan="10"><strong>{{ group.workshop }}</strong><span>{{ group.items.length }} 人</span></td>
          </tr>
          <tr v-for="item in group.items" :key="item.driver.id" :class="{ 'is-restricted': item.driver.is_restricted }">
            <template v-if="!item.driver.is_restricted">
            <td class="strong">{{ item.driver.name }}</td>
            <td>{{ item.driver.phone }}</td>
            <td>{{ item.driver.license_type || '—' }}</td>
            <td>{{ driverWorkshopLabel(item.driver) }}</td>
            <td>{{ driverEmploymentStatusLabel(item.driver) }}</td>
            <td>{{ formatAgeFromIdCard(item.driver.id_card) }}</td>
            <td class="mono">{{ item.driver.id_card || '—' }}</td>
            <td class="col-long">
              <button v-if="item.driver.has_health_check_report" type="button" class="link" @click="viewDocument(item.driver, 'health_check_report')">查看图片</button>
              <span v-else>未上传</span>
            </td>
            <td class="col-long">
              <button v-if="item.driver.has_outsourcing_onboarding" type="button" class="link" @click="viewDocument(item.driver, 'outsourcing_onboarding')">查看图片</button>
              <span v-else>未上传</span>
            </td>
            </template>
            <template v-else>
            <td class="strong">{{ item.driver.name }}</td>
            <td>{{ item.driver.phone }}</td>
            <td colspan="7" class="restricted-copy">跨车间档案 · 仅联系电话可见</td>
            </template>
            <td class="w">
              <button type="button" class="link" @click="openDetails(item.driver)">查看</button>
              <button v-if="canEditDriver(item.driver)" type="button" class="link" @click="openEdit(item.driver)">编辑</button>
              <button v-if="canEditDriver(item.driver)" type="button" class="link danger" @click="onDelete(item.driver)">删除</button>
            </td>
          </tr>
          </template>
          <tr v-if="hasMoreDrivers" ref="driverDesktopLoadMoreRef" class="scroll-loader-row">
            <td colspan="10">
              {{ loadingMore ? '正在加载更多驾驶员…' : `向下滑动继续加载 · 已显示 ${rows.length} / ${totalCount} 人` }}
            </td>
          </tr>
          <tr v-else-if="rows.length > 0" class="scroll-loader-row scroll-loader-row--done">
            <td colspan="10">已加载全部 {{ totalCount }} 名驾驶员</td>
          </tr>
        </tbody>
      </table>

      <div class="driver-cards-mobile" aria-label="驾驶员列表">
        <p v-if="rows.length === 0" class="empty-hint driver-cards-mobile__empty">暂无数据，可调整筛选后点击查询。</p>
        <ul v-else class="driver-cards">
          <template v-for="group in driverGroups" :key="`mobile-${group.workshop}`">
          <li class="driver-workshop-heading"><strong>{{ group.workshop }}</strong><span>{{ group.items.length }} 人</span></li>
          <li v-for="item in group.items" :key="`m-${item.driver.id}`" class="driver-card">
            <div class="driver-card__top">
              <span class="driver-card__name">{{ item.driver.name }}</span>
              <span v-if="!item.driver.is_restricted" class="driver-card__status">{{ driverEmploymentStatusLabel(item.driver) }}</span>
              <span v-else class="driver-card__status driver-card__status--restricted">电话可见</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">电话</span>
              <span class="driver-card__v">{{ item.driver.phone }}</span>
            </div>
            <template v-if="!item.driver.is_restricted">
            <div class="driver-card__row">
              <span class="driver-card__k">准驾</span>
              <span class="driver-card__v">{{ item.driver.license_type || '—' }}</span>
            </div>
            <div class="driver-card__row">
              <span class="driver-card__k">年龄</span>
              <span class="driver-card__v">{{ formatAgeFromIdCard(item.driver.id_card) }}</span>
            </div>
            <div class="driver-card__row driver-card__row--detail">
              <span class="driver-card__k">身份证</span>
              <span class="driver-card__v driver-card__mono">{{ item.driver.id_card || '—' }}</span>
            </div>
            <div class="driver-card__row driver-card__row--detail">
              <span class="driver-card__k">健康体检</span>
              <button v-if="item.driver.has_health_check_report" type="button" class="link driver-card__doc-link" @click="viewDocument(item.driver, 'health_check_report')">查看图片</button>
              <span v-else class="driver-card__v">未上传</span>
            </div>
            <div class="driver-card__row driver-card__row--detail">
              <span class="driver-card__k">外包手续</span>
              <button v-if="item.driver.has_outsourcing_onboarding" type="button" class="link driver-card__doc-link" @click="viewDocument(item.driver, 'outsourcing_onboarding')">查看图片</button>
              <span v-else class="driver-card__v">未上传</span>
            </div>
            </template>
            <p v-else class="driver-card__restricted">跨车间档案，其余信息已隐藏</p>
            <div class="driver-card__actions">
              <button type="button" class="driver-card__btn" @click="openDetails(item.driver)">查看</button>
              <button v-if="canEditDriver(item.driver)" type="button" class="driver-card__btn" @click="openEdit(item.driver)">编辑</button>
              <button v-if="canEditDriver(item.driver)" type="button" class="driver-card__btn driver-card__btn--danger" @click="onDelete(item.driver)">删除</button>
            </div>
          </li>
          </template>
          <li v-if="hasMoreDrivers" ref="driverMobileLoadMoreRef" class="scroll-loader">
            {{ loadingMore ? '正在加载更多驾驶员…' : `向下滑动继续加载 · 已显示 ${rows.length} / ${totalCount} 人` }}
          </li>
          <li v-else class="scroll-loader scroll-loader--done">已加载全部 {{ totalCount }} 名驾驶员</li>
        </ul>
      </div>
    </div>
    </div>

    <AppModal :open="detailOpen" title="驾驶员详情" @close="detailOpen = false">
      <div v-if="detailDriver" class="driver-detail">
        <div class="driver-detail__hero">
          <div>
            <span>所属车间</span>
            <strong>{{ driverWorkshopLabel(detailDriver) }}</strong>
          </div>
          <div>
            <span>驾驶员</span>
            <strong>{{ detailDriver.name }}</strong>
          </div>
        </div>
        <dl class="driver-detail__grid">
          <div><dt>联系电话</dt><dd class="driver-detail__phone">{{ detailDriver.phone }}</dd></div>
          <template v-if="!detailDriver.is_restricted">
            <div><dt>准驾类型</dt><dd>{{ detailDriver.license_type || '—' }}</dd></div>
            <div><dt>人员状态</dt><dd>{{ driverEmploymentStatusLabel(detailDriver) }}</dd></div>
            <div><dt>年龄</dt><dd>{{ formatAgeFromIdCard(detailDriver.id_card) }}</dd></div>
            <div class="driver-detail__wide"><dt>身份证号</dt><dd class="mono">{{ detailDriver.id_card || '—' }}</dd></div>
            <div class="driver-detail__wide"><dt>健康体检报告</dt><dd><button v-if="detailDriver.has_health_check_report" type="button" class="link" @click="viewDocument(detailDriver, 'health_check_report')">查看图片</button><span v-else>未上传</span></dd></div>
            <div class="driver-detail__wide"><dt>外包人员入职手续</dt><dd><button v-if="detailDriver.has_outsourcing_onboarding" type="button" class="link" @click="viewDocument(detailDriver, 'outsourcing_onboarding')">查看图片</button><span v-else>未上传</span></dd></div>
          </template>
        </dl>
        <p v-if="detailDriver.is_restricted" class="driver-detail__notice">跨车间档案仅开放姓名与联系电话，其余信息已按权限隐藏。</p>
      </div>
      <template #footer>
        <button type="button" class="ghost" @click="detailOpen = false">关闭</button>
        <button v-if="detailDriver && canEditDriver(detailDriver)" type="button" class="primary" @click="editFromDetails">编辑驾驶员</button>
      </template>
    </AppModal>

    <AppModal :open="documentPreviewOpen" :title="documentPreviewTitle" @close="closeDocumentPreview">
      <div class="driver-document-preview">
        <img v-if="documentPreviewUrl" :src="documentPreviewUrl" :alt="documentPreviewTitle" />
      </div>
      <template #footer>
        <button type="button" class="ghost" @click="closeDocumentPreview">关闭</button>
      </template>
    </AppModal>

    <AppModal :open="modalOpen" :title="modalTitle" @close="modalOpen = false">
      <div class="form form--drivers">
        <label>姓名</label>
        <input
          v-model.trim="form.name"
          :readonly="!canEditDriverRecords"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>电话</label>
        <input
          v-model.trim="form.phone"
          type="tel"
          inputmode="numeric"
          maxlength="11"
          pattern="\d{11}"
          placeholder="11 位手机号"
          :readonly="!canEditDriverRecords"
          @input="onPhoneInput"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>准驾</label>
        <SearchableSelect
          v-model="formLicenseId"
          :options="licenseFormOptions"
          allow-empty
          empty-label="请选择准驾类型"
          search-placeholder="输入准驾关键字…"
          :disabled="!canEditDriverRecords"
          @denied="denyEdit"
        />

        <label>车间</label>
        <SearchableSelect
          v-model="formWorkshopId"
          :options="workshopFormOptions"
          allow-empty
          empty-label="请选择车间"
          search-placeholder="输入车间关键字…"
          :disabled="!canEditDriverRecords"
          @denied="denyEdit"
        />

        <label>状态</label>
        <SearchableSelect
          v-model="formEmploymentStatusId"
          :options="employmentStatusFormOptions"
          allow-empty
          empty-label="请选择状态"
          search-placeholder="本单位 / 外包…"
          :disabled="!canEditDriverRecords"
          @denied="denyEdit"
        />

        <label>身份证号</label>
        <input
          v-model.trim="form.id_card"
          class="mono"
          maxlength="18"
          placeholder="18 位身份证号"
          :readonly="!canEditDriverRecords"
          @input="onIdCardInput"
          @focus="onFieldFocus"
          @click="onFieldClick"
        />

        <label>年龄</label>
        <div class="form-readonly" aria-live="polite">{{ formAgeDisplay }}</div>

        <label>健康体检报告</label>
        <div class="driver-document-field">
          <div v-if="editingId && existingHealthReport" class="driver-document-field__existing">
            <span>已上传图片</span>
            <button type="button" class="link" @click="viewDocumentById(editingId, 'health_check_report')">查看</button>
            <button type="button" class="link danger" :disabled="saving" @click="removeDocument('health_check_report')">删除</button>
          </div>
          <MobileMediaCapture
            ref="healthCaptureRef"
            panel-aria-label="健康体检报告图片"
            photo-heading=""
            photo-hint="拍照或选择 JPG、PNG、WebP 图片；保存驾驶员后自动上传。"
            photo-file-base="health_check_report"
            single-photo
            compact
            :max-file-mb="20"
            :show-photo-download="false"
          />
        </div>

        <label>外包人员入职手续</label>
        <div class="driver-document-field">
          <div v-if="editingId && existingOnboarding" class="driver-document-field__existing">
            <span>已上传图片</span>
            <button type="button" class="link" @click="viewDocumentById(editingId, 'outsourcing_onboarding')">查看</button>
            <button type="button" class="link danger" :disabled="saving" @click="removeDocument('outsourcing_onboarding')">删除</button>
          </div>
          <MobileMediaCapture
            ref="onboardingCaptureRef"
            panel-aria-label="外包人员入职手续图片"
            photo-heading=""
            photo-hint="拍照或选择 JPG、PNG、WebP 图片；保存驾驶员后自动上传。"
            photo-file-base="outsourcing_onboarding"
            single-photo
            compact
            :max-file-mb="20"
            :show-photo-download="false"
          />
        </div>
      </div>

      <template #footer>
        <button type="button" class="ghost" @click="modalOpen = false">取消</button>
        <button
          v-if="canEditDriverRecords"
          type="button"
          class="primary"
          :disabled="saving"
          @click="save"
        >
          保存
        </button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import * as api from '@/api/drivers'
import type { DriverDocumentKind } from '@/api/drivers'
import { fetchWorkshops, type Workshop } from '@/api/workshops'
import type { Driver } from '@/api/types'
import AppModal from '@/components/AppModal.vue'
import MobileMediaCapture from '@/components/MobileMediaCapture.vue'
import SearchableSelect, { type SearchableOption } from '@/components/SearchableSelect.vue'
import { usePermissions } from '@/composables/usePermissions'
import { ageFromIdCard, formatAgeFromIdCard } from '@/utils/idCard'

type MediaCaptureHandle = {
  getPhotoFile: () => File | null
  clearPhoto: () => void
}

const EDIT_DENIED_MSG = '当前账号无权修改驾驶员档案，请联系段级或超级管理员。'

/** 人员状态：仅本单位 / 外包 */
const EMPLOYMENT_STATUS_OPTIONS: SearchableOption[] = [
  { id: 1, label: '本单位', keywords: '本单位 在岗 在职' },
  { id: 2, label: '外包', keywords: '外包 外包人员' },
]

const COMMON_LICENSE_TYPES = ['A1', 'A2', 'A3', 'B1', 'B2', 'C1'] as const

/** 编辑框准驾下拉中不展示的机型（大小写不敏感） */
const EXCLUDED_LICENSE_TYPES = new Set([
  'C2',
  'C3',
  'C4',
  'C5',
  'C6',
  'D',
  'E',
  'F',
  'M',
  'N',
  'P',
])

const PHONE_PATTERN = /^\d{11}$/
const ID_CARD_PATTERN = /^\d{17}[\dX]$/

const { canEditDriverRecords } = usePermissions()
const router = useRouter()

function openManagementAnalysis() {
  void router.push({ name: 'managementAnalysis', query: { scope: 'drivers' } })
}

const loading = ref(true)
const saving = ref(false)
const rows = ref<Driver[]>([])
const q = ref('')
const msg = ref('')
const totalCount = ref(0)
const loadingMore = ref(false)
const DRIVER_BATCH_SIZE = 30
const driverDesktopLoadMoreRef = ref<HTMLElement | null>(null)
const driverMobileLoadMoreRef = ref<HTMLElement | null>(null)
let driverLoadObserver: IntersectionObserver | null = null
let listRequestId = 0
const driverWorkshops = ref<string[]>([])
const driverLicenseTypes = ref<string[]>([])
const workshopsMaster = ref<Workshop[]>([])
const filterWorkshopId = ref(0)
const filterLicenseId = ref(0)
const formWorkshopId = ref(0)
const formLicenseId = ref(0)
const formEmploymentStatusId = ref(0)
const employmentStatusFormOptions = EMPLOYMENT_STATUS_OPTIONS

const modalOpen = ref(false)
const detailOpen = ref(false)
const detailDriver = ref<Driver | null>(null)
const modalTitle = ref('新增驾驶员')
const editingId = ref<number | null>(null)
const healthCaptureRef = ref<MediaCaptureHandle | null>(null)
const onboardingCaptureRef = ref<MediaCaptureHandle | null>(null)
const existingHealthReport = ref(false)
const existingOnboarding = ref(false)
const documentPreviewOpen = ref(false)
const documentPreviewUrl = ref('')
const documentPreviewTitle = ref('档案图片')

const form = reactive({
  name: '',
  phone: '',
  id_card: '',
})

const formAgeDisplay = computed(() => {
  const age = ageFromIdCard(form.id_card)
  if (age === null) {
    const raw = form.id_card.trim()
    return raw ? '无法识别（请检查身份证号）' : '填写身份证号后自动计算'
  }
  return `${age} 岁`
})

function driverWorkshopLabel(d: Driver) {
  return (d.workshop_name || '').trim() || '未分配'
}

function driverEmploymentStatusLabel(d: Driver) {
  const raw = (d.status || '').trim()
  if (!raw) return '—'
  if (raw === '本单位' || raw === '外包') return raw
  if (raw.includes('外包')) return '外包'
  if (raw === '在岗' || raw === '在职') return '本单位'
  return raw
}

function canEditDriver(d: Driver) {
  return canEditDriverRecords.value && !d.is_restricted
}

function employmentStatusIdFromLabel(label: string): number {
  const t = label.trim()
  if (!t || t === '—') return 0
  if (t === '外包' || t.includes('外包')) return 2
  if (t === '本单位') return 1
  return 1
}

function denyEdit() {
  window.alert(EDIT_DENIED_MSG)
}

function onPhoneInput(e: Event) {
  const el = e.target as HTMLInputElement
  const digits = el.value.replace(/\D/g, '').slice(0, 11)
  if (el.value !== digits) el.value = digits
  form.phone = digits
}

function onIdCardInput(e: Event) {
  const el = e.target as HTMLInputElement
  const normalized = el.value
    .toUpperCase()
    .replace(/[^0-9X]/g, '')
    .slice(0, 18)
  if (el.value !== normalized) el.value = normalized
  form.id_card = normalized
}

function validateDriverForm(): string | null {
  const phone = form.phone.trim()
  if (!PHONE_PATTERN.test(phone)) return '电话须为 11 位数字'
  const idCard = form.id_card.trim()
  if (idCard && !ID_CARD_PATTERN.test(idCard)) return '身份证号须为 18 位（末位可为 X）'
  return null
}

function onFieldFocus() {
  if (!canEditDriverRecords.value) denyEdit()
}

function onFieldClick() {
  if (!canEditDriverRecords.value) denyEdit()
}

const workshopFilterOptions = computed<SearchableOption[]>(() => {
  const sorted = [...new Set(driverWorkshops.value)].sort((a, b) => a.localeCompare(b, 'zh-CN'))
  const out: SearchableOption[] = []
  let nid = 1
  for (const label of sorted) {
    out.push({ id: nid, label, keywords: label })
    nid += 1
  }
  return out
})

const workshopFormOptions = computed<SearchableOption[]>(() =>
  workshopsMaster.value.map((w) => ({
    id: w.id,
    label: w.name,
    keywords: w.name,
  })),
)

const licenseTypeOptions = computed<SearchableOption[]>(() => {
  const out: SearchableOption[] = [{ id: 1, label: '(未填)', keywords: '(未填) 未填' }]
  let nid = 2
  for (const s of driverLicenseTypes.value) {
    out.push({ id: nid, label: s, keywords: s })
    nid += 1
  }
  return out
})

function isSelectableLicenseType(label: string): boolean {
  const t = label.trim()
  if (!t) return false
  return !EXCLUDED_LICENSE_TYPES.has(t.toUpperCase())
}

const licenseFormOptions = computed<SearchableOption[]>(() => {
  const labels = new Set<string>()
  for (const t of COMMON_LICENSE_TYPES) labels.add(t)
  for (const s of driverLicenseTypes.value) {
    if (s && isSelectableLicenseType(s)) labels.add(s)
  }
  return [...labels].sort().map((label, idx) => ({
    id: idx + 1,
    label,
    keywords: label,
  }))
})

const hasMoreDrivers = computed(() => rows.value.length < totalCount.value)

const driverGroups = computed(() => {
  const grouped = new Map<string, Array<{ driver: Driver; index: number }>>()
  rows.value.forEach((driver, index) => {
    const workshop = driverWorkshopLabel(driver)
    const items = grouped.get(workshop) ?? []
    items.push({ driver, index })
    grouped.set(workshop, items)
  })
  return [...grouped.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'zh-CN', { sensitivity: 'accent' }))
    .map(([workshop, items]) => ({ workshop, items }))
})

function selectedWorkshopQuery(): string | undefined {
  if (!filterWorkshopId.value) return undefined
  return workshopFilterOptions.value.find((x) => x.id === filterWorkshopId.value)?.label
}

function selectedLicenseQuery(): string | undefined {
  if (!filterLicenseId.value) return undefined
  return licenseTypeOptions.value.find((x) => x.id === filterLicenseId.value)?.label
}

function buildDriverListParams(skip: number) {
  return {
    q: q.value || undefined,
    skip,
    limit: DRIVER_BATCH_SIZE,
    workshop: selectedWorkshopQuery(),
    license_type: selectedLicenseQuery(),
  }
}

async function fetchListData(append: boolean, requestId: number) {
  const skip = append ? rows.value.length : 0
  const res = await api.listDrivers(buildDriverListParams(skip))
  if (requestId !== listRequestId) return
  if (append) {
    const existingIds = new Set(rows.value.map((driver) => driver.id))
    rows.value = [...rows.value, ...res.items.filter((driver) => !existingIds.has(driver.id))]
  } else {
    rows.value = res.items
  }
  totalCount.value = res.total
}

async function loadList() {
  const requestId = ++listRequestId
  loading.value = true
  loadingMore.value = false
  msg.value = ''
  try {
    await fetchListData(false, requestId)
  } catch {
    if (requestId === listRequestId) msg.value = '加载驾驶员列表失败'
  } finally {
    if (requestId === listRequestId) loading.value = false
  }
}

async function loadMoreDrivers() {
  if (loading.value || loadingMore.value || !hasMoreDrivers.value) return
  const requestId = listRequestId
  loadingMore.value = true
  try {
    await fetchListData(true, requestId)
  } catch {
    if (requestId === listRequestId) msg.value = '加载更多驾驶员失败，请继续下滑重试'
  } finally {
    if (requestId === listRequestId) loadingMore.value = false
  }
}

function observeDriverLoadTargets() {
  driverLoadObserver?.disconnect()
  driverLoadObserver = null
  if (typeof IntersectionObserver === 'undefined') return
  driverLoadObserver = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) void loadMoreDrivers()
    },
    { rootMargin: '320px 0px' },
  )
  if (driverDesktopLoadMoreRef.value) driverLoadObserver.observe(driverDesktopLoadMoreRef.value)
  if (driverMobileLoadMoreRef.value) driverLoadObserver.observe(driverMobileLoadMoreRef.value)
}

watch([driverDesktopLoadMoreRef, driverMobileLoadMoreRef], observeDriverLoadTargets, { flush: 'post' })

async function loadAll() {
  const requestId = ++listRequestId
  loading.value = true
  loadingMore.value = false
  msg.value = ''
  try {
    const [f, ws] = await Promise.all([api.getDriverFilters(), fetchWorkshops()])
    if (requestId !== listRequestId) return
    driverWorkshops.value = f.workshops
    driverLicenseTypes.value = f.license_types
    workshopsMaster.value = ws
    await fetchListData(false, requestId)
  } catch {
    if (requestId === listRequestId) msg.value = '加载筛选项或驾驶员列表失败'
  } finally {
    if (requestId === listRequestId) loading.value = false
  }
}

function resetForm() {
  form.name = ''
  form.phone = ''
  form.id_card = ''
  existingHealthReport.value = false
  existingOnboarding.value = false
  healthCaptureRef.value?.clearPhoto()
  onboardingCaptureRef.value?.clearPhoto()
  formWorkshopId.value = 0
  formLicenseId.value = 0
  formEmploymentStatusId.value = 0
}

function syncFormEmploymentStatusFromId(): string {
  return employmentStatusFormOptions.find((x) => x.id === formEmploymentStatusId.value)?.label ?? ''
}

function syncFormLicenseFromId() {
  const label = licenseFormOptions.value.find((x) => x.id === formLicenseId.value)?.label
  return label || ''
}

function syncFormWorkshopFromId(): number | null {
  if (!formWorkshopId.value) return null
  const hit = workshopsMaster.value.find((w) => w.id === formWorkshopId.value)
  return hit?.id ?? null
}

function openCreate() {
  if (!canEditDriverRecords.value) {
    denyEdit()
    return
  }
  editingId.value = null
  modalTitle.value = '新增驾驶员'
  resetForm()
  modalOpen.value = true
}

function openEdit(d: Driver) {
  if (!canEditDriver(d)) {
    denyEdit()
    return
  }
  editingId.value = d.id
  modalTitle.value = '编辑驾驶员'
  form.name = d.name
  form.phone = d.phone
  form.id_card = d.id_card || ''
  existingHealthReport.value = d.has_health_check_report
  existingOnboarding.value = d.has_outsourcing_onboarding
  healthCaptureRef.value?.clearPhoto()
  onboardingCaptureRef.value?.clearPhoto()
  formWorkshopId.value = d.workshop_id ?? 0
  const licOpt = licenseFormOptions.value.find((x) => x.label === (d.license_type || '').trim())
  formLicenseId.value = licOpt?.id ?? 0
  formEmploymentStatusId.value = employmentStatusIdFromLabel(driverEmploymentStatusLabel(d))
  modalOpen.value = true
}

function openDetails(d: Driver) {
  detailDriver.value = d
  detailOpen.value = true
}

function editFromDetails() {
  if (!detailDriver.value || !canEditDriver(detailDriver.value)) return
  const driver = detailDriver.value
  detailOpen.value = false
  openEdit(driver)
}

function closeDocumentPreview() {
  documentPreviewOpen.value = false
  if (documentPreviewUrl.value) URL.revokeObjectURL(documentPreviewUrl.value)
  documentPreviewUrl.value = ''
}

async function viewDocumentById(driverId: number, kind: DriverDocumentKind) {
  msg.value = ''
  try {
    const blob = await api.downloadDriverDocument(driverId, kind)
    closeDocumentPreview()
    documentPreviewUrl.value = URL.createObjectURL(blob)
    documentPreviewTitle.value = kind === 'health_check_report' ? '健康体检报告' : '外包人员入职手续'
    documentPreviewOpen.value = true
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '加载档案图片失败') : '加载档案图片失败'
  }
}

function viewDocument(driver: Driver, kind: DriverDocumentKind) {
  void viewDocumentById(driver.id, kind)
}

async function removeDocument(kind: DriverDocumentKind) {
  if (!editingId.value || saving.value) return
  const label = kind === 'health_check_report' ? '健康体检报告' : '外包人员入职手续'
  if (!confirm(`确定删除已上传的${label}图片？`)) return
  saving.value = true
  msg.value = ''
  try {
    await api.deleteDriverDocument(editingId.value, kind)
    if (kind === 'health_check_report') existingHealthReport.value = false
    else existingOnboarding.value = false
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '删除图片失败') : '删除图片失败'
  } finally {
    saving.value = false
  }
}

async function save() {
  if (!canEditDriverRecords.value) {
    denyEdit()
    return
  }
  const formErr = validateDriverForm()
  if (formErr) {
    msg.value = formErr
    return
  }
  saving.value = true
  msg.value = ''
  let savedDriverId: number | null = null
  try {
    const payload: Record<string, unknown> = {
      name: form.name,
      phone: form.phone,
      license_type: syncFormLicenseFromId(),
      workshop_id: syncFormWorkshopFromId(),
      status: syncFormEmploymentStatusFromId(),
      id_card: form.id_card || null,
    }
    const saved = editingId.value
      ? await api.updateDriver(editingId.value, payload)
      : await api.createDriver(payload)
    savedDriverId = saved.id
    editingId.value = saved.id

    const healthFile = healthCaptureRef.value?.getPhotoFile()
    if (healthFile) {
      await api.uploadDriverDocument(saved.id, 'health_check_report', healthFile)
      existingHealthReport.value = true
    }
    const onboardingFile = onboardingCaptureRef.value?.getPhotoFile()
    if (onboardingFile) {
      await api.uploadDriverDocument(saved.id, 'outsourcing_onboarding', onboardingFile)
      existingOnboarding.value = true
    }
    modalOpen.value = false
    await loadAll()
  } catch (e) {
    const detail = axios.isAxiosError(e) ? String(e.response?.data?.detail || '') : ''
    msg.value = savedDriverId
      ? `驾驶员资料已保存，但图片上传失败${detail ? `：${detail}` : '，请重新选择图片后保存'}。`
      : detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function onDelete(d: Driver) {
  if (!canEditDriver(d)) {
    denyEdit()
    return
  }
  if (!confirm(`确定删除驾驶员 ${d.name} ？`)) return
  msg.value = ''
  try {
    await api.deleteDriver(d.id)
    await loadAll()
  } catch (e) {
    msg.value = axios.isAxiosError(e) ? String(e.response?.data?.detail || '删除失败') : '删除失败'
  }
}

onMounted(loadAll)
onBeforeUnmount(() => {
  driverLoadObserver?.disconnect()
  closeDocumentPreview()
})
</script>

<style scoped>
.drivers-view {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.toolbar {
  display: grid;
  grid-template-columns: minmax(200px, 1fr) minmax(128px, 200px) minmax(128px, 200px) auto;
  grid-template-rows: auto;
  align-items: end;
  gap: 14px 12px;
  margin-bottom: 12px;
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(201, 100, 66, 0.16);
  border-radius: 16px;
  background:
    radial-gradient(circle at 8% 0%, rgba(201, 100, 66, 0.16), transparent 34%),
    linear-gradient(120deg, rgba(255, 255, 255, 0.96), rgba(239, 232, 215, 0.58));
}

/* 四个格子：关键字 | 状态 | 准驾 | 按钮组（避免 flex+子组件 flex:1 把整块撑到数百像素高） */
.toolbar__filters {
  display: contents;
}

.toolbar__search-wrap {
  position: relative;
  min-width: 0;
  width: 100%;
  align-self: end;
}

.toolbar__search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  color: var(--cl-olive);
  opacity: 0.72;
}

.toolbar__search {
  display: block;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  margin: 0;
  padding: 10px 12px 10px 40px;
  min-height: 42px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  color: var(--cl-near-black);
  font-family: inherit;
  font-size: 13px;
  line-height: 1.35;
  box-shadow: 0 1px 2px rgba(20, 20, 19, 0.05);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
  -webkit-appearance: none;
  appearance: none;
}

.toolbar__search::placeholder {
  color: var(--cl-olive);
  opacity: 0.75;
}

.toolbar__search:hover {
  border-color: var(--cl-border-warm);
}

.toolbar__search:focus {
  outline: none;
  border-color: var(--cl-border-warm);
  box-shadow:
    0 1px 2px rgba(20, 20, 19, 0.06),
    0 0 0 3px rgba(158, 107, 74, 0.18);
}

.toolbar__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  width: 100%;
  max-width: 200px;
}

.toolbar :deep(.searchable-select) {
  flex: 0 1 auto;
  min-width: 0;
  width: 100%;
  max-width: 200px;
  min-height: 0;
}

.toolbar__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-self: end;
  margin-left: 0;
}

.toolbar__btn-analysis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.toolbar__btn-analysis.is-active {
  border-color: var(--cl-brand);
  color: var(--cl-brand);
  background: rgba(201, 100, 66, 0.07);
}

.driver-analysis {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  margin: 0 0 12px;
  padding: 12px;
  border: 1px solid rgba(201, 100, 66, 0.2);
  border-radius: 16px;
  background:
    radial-gradient(circle at 96% 0%, rgba(201, 100, 66, 0.12), transparent 32%),
    rgba(255, 253, 249, 0.94);
}

.driver-analysis__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.driver-analysis__heading > div {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.driver-analysis__heading strong {
  color: var(--cl-near-black);
  font-size: 15px;
}

.driver-analysis__heading span,
.driver-analysis__loading,
.driver-analysis__empty {
  color: var(--cl-olive);
  font-size: 12px;
}

.driver-analysis__kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.driver-kpi {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  background: var(--cl-white);
}

.driver-kpi span {
  display: block;
  color: var(--cl-olive);
  font-size: 12px;
}

.driver-kpi strong {
  display: block;
  margin-top: 3px;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-size: 1.1rem;
}

.driver-analysis__charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.driver-chart {
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  background: var(--cl-white);
}

.driver-chart h3 {
  margin: 0 0 9px;
  color: var(--cl-olive);
  font-size: 12px;
}

.driver-bars {
  display: flex;
  flex-direction: column;
  gap: 7px;
  max-height: 180px;
  overflow-y: auto;
  overflow-x: hidden;
}

.driver-bar {
  display: grid;
  grid-template-columns: minmax(64px, 96px) minmax(0, 1fr) 50px;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.driver-bar__label {
  min-width: 0;
  overflow: hidden;
  color: var(--cl-near-black);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.driver-bar__track {
  height: 8px;
  min-width: 0;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(107, 93, 75, 0.1);
}

.driver-bar__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
}

.driver-bar__value {
  color: var(--cl-olive);
  font-size: 11px;
  text-align: right;
  white-space: nowrap;
}

.driver-analysis__empty {
  margin: 0;
  padding: 18px 8px;
  text-align: center;
}

.toolbar-label {
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 700;
  white-space: nowrap;
}

.toolbar-select {
  min-width: 0;
  max-width: 200px;
}

/* 中等宽度：关键字单行占满，状态+准驾一行，按钮单独一行，避免四列挤成一团 */
@media (max-width: 900px) and (min-width: 769px) {
  .toolbar {
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto auto;
  }

  .toolbar__search-wrap {
    grid-column: 1 / -1;
  }

  .toolbar > .toolbar__field:first-of-type {
    grid-column: 1;
    grid-row: 2;
  }

  .toolbar > .toolbar__field:last-of-type {
    grid-column: 2;
    grid-row: 2;
  }

  .toolbar__actions {
    grid-column: 1 / -1;
    grid-row: 3;
    justify-self: stretch;
    justify-content: flex-start;
  }
}

.q {
  padding: 10px 12px;
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

.list-stack {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
}

.list-wrap {
  min-width: 0;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.scroll-loader-row td,
.scroll-loader {
  padding: 14px 12px;
  color: var(--cl-olive);
  background: var(--cl-ivory);
  font-size: 12px;
  line-height: 1.4;
  text-align: center;
  list-style: none;
}

.scroll-loader-row--done td,
.scroll-loader--done {
  color: var(--cl-stone);
  background: transparent;
}

.driver-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-warm-sand);
  box-sizing: border-box;
}

.driver-pager__summary {
  flex: 1 1 200px;
  min-width: 0;
}

.driver-pager__size-row {
  display: inline-flex;
  align-items: center;
  gap: 6px 8px;
  flex-wrap: nowrap;
  flex-shrink: 0;
}

.driver-pager__size-row > .driver-pager__meta {
  flex-shrink: 0;
}

.driver-pager__meta {
  font-size: 13px;
  color: var(--cl-olive);
}

.driver-pager__page {
  font-size: 13px;
  color: var(--cl-charcoal);
  font-weight: 700;
}

.driver-pager__nav {
  display: flex;
  gap: 8px;
  margin-left: auto;
  flex-wrap: wrap;
}

.driver-pager__label {
  display: inline-block;
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
  margin: 0;
  cursor: default;
}

.driver-pager__size {
  width: auto;
  min-width: 5.5rem;
  max-width: 7.5rem;
  flex: 0 0 auto;
  padding: 8px 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  font-size: 13px;
  font-family: inherit;
  color: var(--cl-near-black);
  min-height: 36px;
  box-sizing: border-box;
  line-height: 1.2;
}

.driver-pager__btn {
  min-height: 36px;
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
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
  min-width: 1080px;
}

.col-narrow {
  width: 64px;
  white-space: nowrap;
}

.col-long {
  max-width: 160px;
  word-break: break-word;
  line-height: 1.35;
}

.mono {
  font-family: ui-monospace, 'Cascadia Mono', 'Segoe UI Mono', monospace;
  font-size: 12px;
}

.empty-hint {
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
  padding: 28px 16px !important;
}

.driver-cards-mobile {
  display: none;
}

.driver-cards {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.driver-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 14px;
  background: var(--cl-ivory);
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.04) 0 4px 16px;
}

.driver-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.driver-card__name {
  font-size: 1.05rem;
  font-weight: 900;
  color: var(--cl-near-black);
  line-height: 1.3;
  word-break: break-word;
}

.driver-card__status {
  flex-shrink: 0;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  font-size: 12px;
  font-weight: 700;
  color: var(--cl-olive);
}

.driver-card__row {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 8px 12px;
  align-items: start;
  font-size: 13px;
  margin-bottom: 8px;
}

.driver-card__k {
  font-size: 11px;
  font-weight: 700;
  color: var(--cl-olive);
}

.driver-card__v {
  color: var(--cl-near-black);
  word-break: break-word;
  line-height: 1.4;
}

.driver-card__mono {
  font-family: ui-monospace, 'Cascadia Mono', 'Segoe UI Mono', monospace;
  font-size: 12px;
}

.driver-card__actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(82px, 1fr));
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--cl-border-cream);
}

.driver-card__btn {
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

.driver-card__btn--danger {
  color: var(--cl-error);
  border-color: rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.06);
}

.driver-cards-mobile__empty {
  margin: 0;
  padding: 24px 12px !important;
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
  grid-template-columns: 140px 1fr;
  gap: 10px 12px;
  align-items: center;
}

.form label {
  color: var(--cl-charcoal);
  font-size: 12px;
}

.form input,
.form select,
.form textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 10px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  color: var(--cl-near-black);
}

.form textarea {
  resize: vertical;
}

.driver-document-field {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  background: var(--cl-ivory);
}

.driver-document-field__existing {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--cl-charcoal);
  font-size: 12px;
}

.driver-document-field :deep(.mobile-capture) {
  margin: 0;
}

.driver-document-preview {
  display: grid;
  min-height: 180px;
  place-items: center;
  overflow: hidden;
  border-radius: 12px;
  background: #181a18;
}

.driver-document-preview img {
  display: block;
  max-width: 100%;
  max-height: min(70vh, 760px);
  object-fit: contain;
}

.driver-card__doc-link {
  justify-self: start;
}

@media (max-width: 768px) {
  .drivers-view {
    padding-bottom: env(safe-area-inset-bottom, 0);
  }

  .toolbar {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    margin-bottom: 14px;
  }

  .toolbar__search-wrap {
    min-width: 0;
    width: 100%;
    flex: none;
  }

  .toolbar__search {
    min-height: 48px;
    font-size: 16px;
    padding: 12px 14px 12px 44px;
    border-radius: 12px;
  }

  .toolbar__search-icon {
    left: 14px;
  }

  .toolbar__search-icon svg {
    width: 20px;
    height: 20px;
  }

  .toolbar__filters {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .toolbar__field {
    min-width: 0;
    width: 100%;
    max-width: none;
    gap: 6px;
  }

  .toolbar-label {
    margin-top: 0;
  }

  .toolbar-select {
    max-width: 100% !important;
    width: 100%;
  }

  .toolbar :deep(.searchable-select) {
    flex: 0 1 auto;
    min-height: 0;
    max-width: 100% !important;
    width: 100%;
  }

  .toolbar :deep(.searchable-select__trigger) {
    min-height: 48px;
    font-size: 16px;
    border-radius: 12px;
  }

  .toolbar :deep(.searchable-select__search) {
    font-size: 16px;
  }

  .toolbar :deep(.searchable-select__item) {
    padding: 12px 14px;
    font-size: 15px;
  }

  .toolbar__actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-left: 0;
    width: 100%;
    justify-self: stretch;
  }

  .toolbar__btn-query {
    grid-column: 1 / -1;
    min-height: 48px;
    font-size: 15px;
    font-weight: 800;
    border-radius: 12px;
    touch-action: manipulation;
  }

  .toolbar__btn-new,
  .toolbar__btn-refresh {
    min-height: 48px;
    font-size: 15px;
    font-weight: 700;
    border-radius: 12px;
    touch-action: manipulation;
  }

  .toolbar__actions:not(:has(.toolbar__btn-new)) .toolbar__btn-refresh {
    grid-column: 1 / -1;
  }

  .msg {
    font-size: 14px;
    padding: 12px 14px;
    line-height: 1.45;
  }

  .muted {
    font-size: 14px;
    padding: 4px 0 8px;
  }

  .list-wrap {
    overflow-x: visible;
    -webkit-overflow-scrolling: auto;
  }

  .driver-pager {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    margin-top: 12px;
    padding: 14px 12px;
  }

  .driver-pager__summary {
    flex: none;
    text-align: center;
    font-size: 14px;
    line-height: 1.4;
  }

  .driver-pager__size-row {
    justify-content: center;
    width: 100%;
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 2px;
  }

  .driver-pager__size {
    min-height: 44px;
    font-size: 16px;
    flex: 0 0 auto;
    min-width: 5.5rem;
    max-width: 8rem;
  }

  .driver-pager__page {
    text-align: center;
    width: 100%;
    font-size: 14px;
  }

  .driver-pager__nav {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    width: 100%;
    margin-left: 0;
  }

  .driver-pager__btn {
    min-height: 48px;
    font-size: 15px;
    touch-action: manipulation;
  }

  .tbl--desktop {
    display: none;
  }

  .driver-cards-mobile {
    display: block;
  }

  .driver-cards {
    gap: 14px;
  }

  .driver-card {
    padding: 16px;
    border-radius: 16px;
  }

  .driver-card__top {
    margin-bottom: 14px;
    gap: 8px;
  }

  .driver-card__name {
    font-size: 1.08rem;
  }

  .driver-card__status {
    font-size: 13px;
    padding: 4px 12px;
  }

  .driver-card__row {
    grid-template-columns: minmax(76px, 32%) 1fr;
    gap: 8px 10px;
    font-size: 14px;
    margin-bottom: 10px;
  }

  .driver-card__k {
    font-size: 12px;
  }

  .driver-card__v {
    line-height: 1.45;
  }

  .driver-card__mono {
    font-size: 13px;
    word-break: break-all;
  }

  .driver-card__actions {
    gap: 12px;
    margin-top: 16px;
    padding-top: 14px;
  }

  .driver-card__btn {
    min-height: 48px;
    border-radius: 12px;
  }

  .empty-hint {
    font-size: 14px;
    line-height: 1.5;
    padding: 32px 16px !important;
  }

  .driver-cards-mobile__empty {
    padding: 28px 14px !important;
    font-size: 14px;
    line-height: 1.5;
  }

  .form--drivers {
    grid-template-columns: 1fr;
    gap: 8px 0;
  }

  .form--drivers label {
    margin-top: 4px;
    font-weight: 700;
    font-size: 13px;
  }

  .form--drivers input,
  .form--drivers select,
  .form--drivers textarea {
    font-size: 16px;
    min-height: 48px;
    border-radius: 12px;
    padding: 12px 12px;
  }

  .form--drivers textarea {
    min-height: 88px;
    resize: vertical;
  }
}

.form-readonly {
  min-height: 42px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream, #e8e0d4);
  background: var(--cl-warm-sand, #f5efe6);
  color: var(--cl-near-black, #1a1a1a);
  font-size: 14px;
  line-height: 1.45;
  display: flex;
  align-items: center;
}

.driver-workshop-row td {
  padding: 9px 12px;
  background: linear-gradient(90deg, rgba(201, 100, 66, 0.15), rgba(239, 232, 215, 0.5) 64%, transparent);
  border-bottom-color: rgba(201, 100, 66, 0.2);
}

.driver-workshop-row strong,
.driver-workshop-heading strong {
  color: var(--cl-near-black);
  font-size: 14px;
}

.driver-workshop-row span,
.driver-workshop-heading span {
  margin-left: 10px;
  color: var(--cl-olive);
  font-size: 12px;
  font-weight: 700;
}

.driver-workshop-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(201, 100, 66, 0.18);
  background: linear-gradient(100deg, #f4e8de, #f5f1e8 68%, #fff);
}

.restricted-copy,
.driver-card__restricted {
  color: var(--cl-olive);
  font-size: 12px;
  font-style: italic;
}

.driver-card__restricted {
  margin: 7px 0 0;
  padding: 8px 10px;
  border-radius: 9px;
  background: var(--cl-warm-sand);
}

.driver-card__status--restricted {
  background: rgba(181, 138, 90, 0.14);
}

.driver-detail__hero {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}

.driver-detail__hero > div,
.driver-detail__grid > div {
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  background: linear-gradient(145deg, var(--cl-white), rgba(239, 232, 215, 0.42));
}

.driver-detail__hero span,
.driver-detail__grid dt {
  display: block;
  margin-bottom: 5px;
  color: var(--cl-olive);
  font-size: 11px;
  font-weight: 700;
}

.driver-detail__hero strong {
  display: block;
  font-size: 17px;
  overflow-wrap: anywhere;
}

.driver-detail__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.driver-detail__grid dd {
  margin: 0;
  color: var(--cl-near-black);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.driver-detail__phone {
  color: var(--cl-coral) !important;
  font-size: 17px;
  font-weight: 900;
}

.driver-detail__wide {
  grid-column: 1 / -1;
}

.driver-detail__notice {
  margin: 10px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--cl-warm-sand);
  color: var(--cl-olive);
  font-size: 13px;
}

/* 手机端采用紧凑控制区和独立滚动列表，保持与油卡余额页一致的浏览节奏。 */
@media (max-width: 768px) {
  .driver-detail__hero,
  .driver-detail__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 7px;
  }

  .driver-detail__wide {
    grid-column: 1 / -1;
  }

  .driver-detail__hero > div,
  .driver-detail__grid > div {
    padding: 10px;
  }

  .drivers-view {
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .toolbar {
    flex: 0 0 auto;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
    margin-bottom: 6px;
  }

  .toolbar__search-wrap {
    grid-column: 1 / -1;
  }

  .toolbar__search {
    min-height: 38px;
    padding: 7px 9px 7px 34px;
    border-radius: 9px;
    font-size: 13px;
  }

  .toolbar__search-icon {
    left: 10px;
  }

  .toolbar__search-icon svg {
    width: 16px;
    height: 16px;
  }

  .toolbar__filters {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .toolbar__field {
    gap: 0;
  }

  .toolbar-label {
    display: none;
  }

  .toolbar :deep(.searchable-select__trigger) {
    min-height: 38px;
    height: 38px;
    padding: 7px 9px;
    border-radius: 9px;
    font-size: 13px;
  }

  .toolbar__actions {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .toolbar__btn-query,
  .toolbar__btn-analysis,
  .toolbar__btn-new,
  .toolbar__btn-refresh {
    grid-column: auto;
    min-height: 36px;
    padding: 6px 7px;
    border-radius: 9px;
    font-size: 12px;
  }

  .toolbar__actions:not(:has(.toolbar__btn-new)) .toolbar__btn-refresh {
    grid-column: 1 / -1;
  }

  .driver-analysis {
    flex: 0 1 auto;
    max-height: min(58vh, 540px);
    margin-bottom: 6px;
    padding: 8px;
    border-radius: 12px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .driver-analysis__heading {
    align-items: flex-start;
    margin-bottom: 8px;
  }

  .driver-analysis__heading > div {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }

  .driver-analysis__kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
    margin-bottom: 8px;
  }

  .driver-kpi {
    padding: 8px 9px;
  }

  .driver-analysis__charts {
    grid-template-columns: minmax(0, 1fr);
    gap: 7px;
  }

  .driver-chart {
    padding: 9px;
  }

  .driver-bars {
    max-height: 150px;
  }

  .driver-bar {
    grid-template-columns: minmax(68px, 92px) minmax(0, 1fr) 46px;
    gap: 6px;
  }

  .list-stack {
    flex: 1 1 auto;
    min-height: 0;
    overflow: hidden;
  }

  .list-wrap {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    overflow: hidden;
  }

  .driver-cards-mobile {
    display: flex;
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    overflow: hidden;
  }

  .driver-cards {
    width: 100%;
    min-height: 0;
    gap: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    border: 1px solid var(--cl-border-cream);
    border-radius: 12px;
    background: var(--cl-white);
  }

  .driver-workshop-heading {
    position: sticky;
    top: 0;
    z-index: 2;
    flex: 0 0 auto;
  }

  .driver-card {
    padding: 10px 12px;
    border: 0;
    border-bottom: 1px solid var(--cl-border-cream);
    border-radius: 0;
    box-shadow: none;
    background: var(--cl-white);
  }

  .driver-card:last-child {
    border-bottom: 0;
  }

  .driver-card__top {
    margin-bottom: 6px;
  }

  .driver-card__name {
    font-size: 16px;
  }

  .driver-card__status {
    padding: 2px 8px;
    font-size: 11px;
  }

  .driver-card__row {
    grid-template-columns: 58px minmax(0, 1fr);
    gap: 5px;
    margin-bottom: 3px;
    font-size: 12px;
  }

  .driver-card__k {
    font-size: 11px;
  }

  .driver-card__row--detail {
    display: none;
  }

  .driver-card__actions {
    display: flex;
    justify-content: flex-end;
    gap: 6px;
    margin-top: 7px;
    padding-top: 7px;
  }

  .driver-card__btn {
    min-height: 32px;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 12px;
  }

  .driver-pager {
    flex: 0 0 auto;
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    padding: 6px;
    border-radius: 10px;
  }

  .driver-pager__summary,
  .driver-pager__size-row {
    display: none;
  }

  .driver-pager__page {
    width: auto;
    flex: 1 1 auto;
    font-size: 11px;
  }

  .driver-pager__nav {
    display: flex;
    width: auto;
    gap: 5px;
  }

  .driver-pager__btn {
    width: auto;
    min-height: 32px;
    padding: 5px 10px;
    font-size: 12px;
  }
}

@media (max-width: 390px) {
  .driver-detail__hero,
  .driver-detail__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .driver-detail__wide {
    grid-column: auto;
  }
}

@media (min-width: 901px) {
  .toolbar {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
  }

  .toolbar__search-wrap {
    flex: 1 1 260px;
    min-width: 220px;
  }

  .toolbar__filters {
    display: flex;
    flex: 0 1 auto;
    gap: 8px;
  }

  .toolbar__field {
    width: 150px;
  }

  .toolbar__actions {
    flex: 0 0 auto;
  }
}
</style>
