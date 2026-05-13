<template>
  <section class="invoice-panel" aria-labelledby="invoice-panel-title">
    <div class="invoice-panel__hd">
      <h2 id="invoice-panel-title" class="invoice-panel__title">AI 发票识别</h2>
      <p class="invoice-panel__hint muted">
        当前为<strong>前端演示</strong>：识别结果为模拟数据。后续接入服务后将替换为真实 OCR / 验真接口。
      </p>
    </div>

    <div
      class="drop-zone"
      :class="{ 'drop-zone--active': dragOver }"
      role="button"
      tabindex="0"
      @dragenter.prevent="onDragEnterZone"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="onDragLeaveZone"
      @drop.prevent="onDrop"
      @keydown.enter.prevent="triggerPick('multi')"
      @keydown.space.prevent="triggerPick('multi')"
    >
      <p class="drop-zone__lead">将发票图片或 PDF 拖入此区域，或使用下方方式添加</p>
      <p class="drop-zone__sub muted">支持 JPG / PNG / WebP / PDF；ZIP 内嵌套文件夹会自动遍历</p>
      <div class="actions">
        <button type="button" class="btn btn--primary" @click="triggerPick('single')">单张上传</button>
        <button type="button" class="btn" @click="triggerPick('multi')">多选文件</button>
        <button type="button" class="btn" @click="triggerPick('folder')">选择文件夹</button>
        <button type="button" class="btn" @click="triggerPick('zip')">ZIP 打包</button>
      </div>
    </div>

    <input
      ref="inputSingleRef"
      type="file"
      class="sr-only"
      :accept="acceptAttr"
      @change="onInputChange($event, false)"
    />
    <input
      ref="inputMultiRef"
      type="file"
      class="sr-only"
      multiple
      :accept="acceptAttr"
      @change="onInputChange($event, false)"
    />
    <input
      ref="inputFolderRef"
      type="file"
      class="sr-only"
      webkitdirectory
      multiple
      @change="onInputChange($event, true)"
    />
    <input ref="inputZipRef" type="file" class="sr-only" accept=".zip,application/zip" @change="onZipSelected" />

    <div v-if="rows.length" class="toolbar">
      <div class="summary" role="status" aria-live="polite">
        <span>共 <strong>{{ rows.length }}</strong> 条</span>
        <span class="sep">·</span>
        <span>已完成 <strong>{{ doneCount }}</strong></span>
        <span class="sep">·</span>
        <span>价税合计（演示）<strong>￥{{ totalAmountDisplay }}</strong></span>
      </div>
      <div class="toolbar__btns">
        <button type="button" class="btn btn--ghost" :disabled="processing" @click="runRecognitionAll">
          {{ processing ? '识别中…' : '开始识别' }}
        </button>
        <button type="button" class="btn btn--ghost" :disabled="processing" @click="clearAll">清空列表</button>
      </div>
    </div>

    <div v-if="rows.length" class="table-wrap">
      <table class="result-table">
        <thead>
          <tr>
            <th class="col-thumb" scope="col">预览</th>
            <th scope="col">来源</th>
            <th scope="col">状态</th>
            <th scope="col">发票代码</th>
            <th scope="col">发票号码</th>
            <th scope="col">开票日期</th>
            <th scope="col">价税合计</th>
            <th scope="col">销售方</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td class="col-thumb">
              <img v-if="r.thumbUrl" :src="r.thumbUrl" alt="" class="thumb" />
              <span v-else class="thumb-fallback" aria-hidden="true">PDF</span>
            </td>
            <td>
              <div class="cell-name" :title="r.displayPath">{{ r.displayPath }}</div>
              <div class="cell-src muted">{{ r.sourceLabel }}</div>
            </td>
            <td>
              <span class="badge" :class="`badge--${r.status}`">{{ statusText(r.status) }}</span>
              <div v-if="r.errorMessage" class="err-msg">{{ r.errorMessage }}</div>
            </td>
            <td>{{ r.result?.invoiceCode ?? '—' }}</td>
            <td>{{ r.result?.invoiceNo ?? '—' }}</td>
            <td>{{ r.result?.issueDate ?? '—' }}</td>
            <td>{{ r.result ? `￥${r.result.totalAmount}` : '—' }}</td>
            <td class="cell-ellipsis" :title="r.result?.sellerName">{{ r.result?.sellerName ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-else class="empty muted">暂无文件，请上传或拖入发票。</p>
  </section>
</template>

<script setup lang="ts">
import JSZip from 'jszip'
import { computed, onBeforeUnmount, ref } from 'vue'

const acceptAttr = 'image/jpeg,image/png,image/webp,image/gif,.pdf,application/pdf'

type RowStatus = 'queued' | 'processing' | 'done' | 'error'

interface InvoiceResult {
  invoiceCode: string
  invoiceNo: string
  issueDate: string
  totalAmount: string
  taxAmount: string
  amountWithoutTax: string
  sellerName: string
  buyerName: string
}

interface Row {
  id: string
  file: File
  displayPath: string
  sourceLabel: string
  status: RowStatus
  errorMessage?: string
  result?: InvoiceResult
  thumbUrl: string | null
}

const inputSingleRef = ref<HTMLInputElement | null>(null)
const inputMultiRef = ref<HTMLInputElement | null>(null)
const inputFolderRef = ref<HTMLInputElement | null>(null)
const inputZipRef = ref<HTMLInputElement | null>(null)

const rows = ref<Row[]>([])
const dragOver = ref(false)
const processing = ref(false)

let dragDepth = 0

function onDragEnterZone() {
  dragDepth += 1
  dragOver.value = true
}

function onDragLeaveZone() {
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) dragOver.value = false
}

function isAllowedMime(file: File): boolean {
  if (file.type.startsWith('image/')) return true
  if (file.type === 'application/pdf') return true
  if (/\.pdf$/i.test(file.name)) return true
  return false
}

function hashish(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h << 5) - h + s.charCodeAt(i)
  return Math.abs(h) || 1
}

/** 模拟识别延迟与字段，接入服务后删除 */
async function mockRecognize(file: File): Promise<InvoiceResult> {
  const delay = 380 + (hashish(file.name + String(file.size)) % 900)
  await new Promise((r) => setTimeout(r, delay))
  const h = hashish(file.name + String(file.size))
  const total = (80 + (h % 12000) / 100).toFixed(2)
  const tax = (Number(total) * 0.06).toFixed(2)
  const pre = (Number(total) - Number(tax)).toFixed(2)
  const y = 2024 + (h % 2)
  const m = 1 + (h % 12)
  const d = 1 + (h % 28)
  const pad = (n: number) => String(n).padStart(2, '0')
  return {
    invoiceCode: `044${String(1e9 + (h % 1e9)).slice(1, 10)}`,
    invoiceNo: String(10000000 + (h % 89999999)),
    issueDate: `${y}-${pad(m)}-${pad(d)}`,
    totalAmount: total,
    taxAmount: tax,
    amountWithoutTax: pre,
    sellerName: ['某某加油站有限公司', '某某高速服务区', '某某维修厂', '哈尔滨工务段后勤服务中心'][h % 4],
    buyerName: '哈尔滨工务段',
  }
}

function makeThumbUrl(file: File): string | null {
  if (file.type.startsWith('image/')) {
    return URL.createObjectURL(file)
  }
  return null
}

function revokeRowUrls(list: Row[]) {
  for (const r of list) {
    if (r.thumbUrl) URL.revokeObjectURL(r.thumbUrl)
  }
}

function addFiles(
  files: File[],
  sourceLabel: string,
  pathFn: (f: File) => string,
) {
  const next: Row[] = []
  for (const file of files) {
    if (!isAllowedMime(file)) continue
    const displayPath = pathFn(file)
    next.push({
      id: `${Date.now()}-${hashish(displayPath + file.size)}-${Math.random().toString(36).slice(2, 8)}`,
      file,
      displayPath,
      sourceLabel,
      status: 'queued',
      thumbUrl: makeThumbUrl(file),
    })
  }
  if (!next.length) return
  rows.value = [...rows.value, ...next]
}

function triggerPick(kind: 'single' | 'multi' | 'folder' | 'zip') {
  const map = {
    single: inputSingleRef,
    multi: inputMultiRef,
    folder: inputFolderRef,
    zip: inputZipRef,
  } as const
  const el = map[kind].value
  if (el) {
    el.value = ''
    el.click()
  }
}

function onInputChange(ev: Event, fromFolder: boolean) {
  const input = ev.target as HTMLInputElement
  const list = input.files ? Array.from(input.files) : []
  if (!list.length) return
  if (fromFolder) {
    addFiles(list, '文件夹', (f) => (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name)
  } else if (list.length === 1) {
    addFiles(list, '单张上传', (f) => f.name)
  } else {
    addFiles(list, '多选文件', (f) => f.name)
  }
}

async function onZipSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const zipFile = input.files?.[0]
  if (!zipFile) return
  try {
    const zip = await JSZip.loadAsync(zipFile)
    const pairs: { path: string; file: File }[] = []
    const tasks: Promise<void>[] = []
    zip.forEach((relPath, entry) => {
      if (entry.dir) return
      if (!/\.(jpe?g|png|gif|webp|bmp|pdf)$/i.test(relPath)) return
      tasks.push(
        entry.async('blob').then((blob) => {
          const name = relPath.split('/').pop() || 'file'
          const type = /\.pdf$/i.test(relPath) ? 'application/pdf' : blob.type || 'application/octet-stream'
          pairs.push({ path: relPath.replace(/\\/g, '/'), file: new File([blob], name, { type }) })
        }),
      )
    })
    await Promise.all(tasks)
    if (!pairs.length) {
      rows.value.push({
        id: `zip-empty-${Date.now()}`,
        file: new File([], zipFile.name),
        displayPath: zipFile.name,
        sourceLabel: 'ZIP',
        status: 'error',
        errorMessage: '压缩包内没有可用的图片或 PDF',
        thumbUrl: null,
      })
      return
    }
    const pathByFile = new WeakMap<File, string>()
    for (const { path, file } of pairs) pathByFile.set(file, path)
    addFiles(
      pairs.map((p) => p.file),
      `ZIP：${zipFile.name}`,
      (f) => pathByFile.get(f) ?? f.name,
    )
  } catch {
    rows.value.push({
      id: `err-${Date.now()}`,
      file: new File([], zipFile.name),
      displayPath: zipFile.name,
      sourceLabel: 'ZIP 解析失败',
      status: 'error',
      errorMessage: '无法读取 ZIP，请确认文件未损坏',
      thumbUrl: null,
    })
  }
}

function onDrop(e: DragEvent) {
  dragDepth = 0
  dragOver.value = false
  const dt = e.dataTransfer
  if (!dt?.files?.length) return
  const list = Array.from(dt.files)
  addFiles(list, '拖放添加', (f) => f.name)
}

async function runRecognitionAll() {
  if (processing.value) return
  processing.value = true
  try {
    for (const r of rows.value) {
      if (r.file.size === 0) continue
      if (r.status !== 'queued' && r.status !== 'error') continue
      r.status = 'processing'
      r.errorMessage = undefined
      try {
        r.result = await mockRecognize(r.file)
        r.status = 'done'
      } catch {
        r.status = 'error'
        r.errorMessage = '识别失败（演示）'
      }
    }
  } finally {
    processing.value = false
  }
}

function clearAll() {
  revokeRowUrls(rows.value)
  rows.value = []
}

const doneCount = computed(() => rows.value.filter((r) => r.status === 'done').length)

const totalAmountDisplay = computed(() => {
  let s = 0
  for (const r of rows.value) {
    if (r.status === 'done' && r.result) s += Number(r.result.totalAmount)
  }
  return s.toFixed(2)
})

function statusText(s: RowStatus) {
  const m: Record<RowStatus, string> = {
    queued: '待识别',
    processing: '识别中',
    done: '已完成',
    error: '失败',
  }
  return m[s]
}

onBeforeUnmount(() => {
  revokeRowUrls(rows.value)
})
</script>

<style scoped>
.invoice-panel {
  margin-top: 1.5rem;
  padding: 1.25rem 1.35rem;
  border-radius: 14px;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
  background: rgba(253, 252, 247, 0.92);
  box-shadow: 0 4px 22px rgba(20, 20, 19, 0.06);
}

.invoice-panel__hd {
  margin-bottom: 1rem;
}

.invoice-panel__title {
  margin: 0 0 0.35rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--cl-charcoal, #2c2b28);
}

.invoice-panel__hint {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.muted {
  color: var(--cl-olive, #6b6558);
}

.drop-zone {
  padding: 1.25rem 1rem;
  border-radius: 12px;
  border: 2px dashed rgba(142, 132, 109, 0.35);
  background: rgba(255, 255, 255, 0.65);
  text-align: center;
  transition:
    border-color 0.2s ease,
    background 0.2s ease;
}

.drop-zone:focus {
  outline: 2px solid var(--cl-terracotta, #c96442);
  outline-offset: 2px;
}

.drop-zone--active {
  border-color: var(--cl-terracotta, #c96442);
  background: rgba(201, 100, 66, 0.06);
}

.drop-zone__lead {
  margin: 0 0 0.35rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--cl-charcoal, #2c2b28);
}

.drop-zone__sub {
  margin: 0 0 1rem;
  font-size: 0.8125rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
}

.btn {
  cursor: pointer;
  border: 1px solid var(--cl-border-warm, rgba(142, 132, 109, 0.35));
  background: var(--cl-white, #fff);
  color: var(--cl-charcoal, #2c2b28);
  border-radius: 10px;
  padding: 0.5rem 0.9rem;
  font-size: 0.8125rem;
  font-weight: 500;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.btn:hover:not(:disabled) {
  background: var(--cl-warm-sand, #f5e5da);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn--primary {
  border-color: rgba(201, 100, 66, 0.45);
  background: var(--cl-terracotta, #c96442);
  color: #fff;
}

.btn--primary:hover:not(:disabled) {
  filter: brightness(1.05);
}

.btn--ghost {
  background: transparent;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.2));
}

.summary {
  font-size: 0.875rem;
  color: var(--cl-charcoal, #2c2b28);
}

.summary .sep {
  margin: 0 0.35rem;
  opacity: 0.45;
}

.toolbar__btns {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.table-wrap {
  margin-top: 0.85rem;
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.22));
  background: rgba(255, 255, 255, 0.85);
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.result-table th,
.result-table td {
  padding: 0.55rem 0.65rem;
  text-align: left;
  border-bottom: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.18));
  vertical-align: top;
}

.result-table th {
  font-weight: 600;
  color: var(--cl-olive, #6b6558);
  background: rgba(245, 229, 218, 0.35);
  white-space: nowrap;
}

.result-table tbody tr:last-child td {
  border-bottom: none;
}

.col-thumb {
  width: 56px;
}

.thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--cl-border-cream, rgba(142, 132, 109, 0.25));
}

.thumb-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 6px;
  font-size: 0.65rem;
  font-weight: 600;
  color: var(--cl-olive, #6b6558);
  background: rgba(142, 132, 109, 0.12);
}

.cell-name {
  font-weight: 500;
  word-break: break-all;
}

.cell-src {
  font-size: 0.75rem;
  margin-top: 0.15rem;
}

.cell-ellipsis {
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 0.12rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 500;
}

.badge--queued {
  background: rgba(142, 132, 109, 0.15);
  color: var(--cl-charcoal, #2c2b28);
}

.badge--processing {
  background: rgba(201, 100, 66, 0.18);
  color: var(--cl-terracotta, #c96442);
}

.badge--done {
  background: rgba(60, 120, 80, 0.18);
  color: #2d6a45;
}

.badge--error {
  background: rgba(180, 60, 50, 0.15);
  color: #a33;
}

.err-msg {
  margin-top: 0.25rem;
  font-size: 0.72rem;
  color: #a33;
}

.empty {
  margin: 1rem 0 0;
  font-size: 0.875rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 720px) {
  .result-table {
    font-size: 0.75rem;
  }

  .result-table th,
  .result-table td {
    padding: 0.45rem 0.4rem;
  }
}
</style>
