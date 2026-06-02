<template>
  <div class="maint-terms">
    <header class="maint-terms__head">
      <div>
        <h1 class="maint-terms__title">维修词条管理</h1>
        <p class="maint-terms__desc muted">
          三级分类：一级大类 → 二级子类 → 三级词条（含别名/关键词，供结算单自动归类）。
        </p>
      </div>
      <div v-if="stats" class="maint-terms__stats">
        <span>大类 {{ stats.level1 }}</span>
        <span>子类 {{ stats.level2 }}</span>
        <span>词条 {{ stats.level3 }}</span>
        <span>启用 {{ stats.active_terms }}</span>
      </div>
    </header>

    <div v-if="!canEdit" class="perm-hint">当前账号仅可浏览，修改需段级/车间管理员权限。</div>
    <div v-if="msg" class="msg">{{ msg }}</div>

    <div class="toolbar">
      <input
        v-model="searchQ"
        type="search"
        class="search-input"
        placeholder="搜索词条名称、别名、关键词…"
        @keyup.enter="runSearch"
      />
      <button type="button" class="ghost" @click="runSearch">搜索</button>
      <button type="button" class="ghost" :disabled="loading" @click="reloadAll">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
      <template v-if="canEdit">
        <button type="button" class="ghost" :disabled="seeding" @click="importPreset(false)">
          {{ seeding ? '导入中…' : '导入预置分类' }}
        </button>
        <button type="button" class="ghost danger-text" :disabled="seeding" @click="importPreset(true)">
          强制重导
        </button>
        <button type="button" class="primary" @click="openCreate(1)">+ 新增大类</button>
      </template>
    </div>

    <div v-if="searchMode" class="search-panel panel">
      <div class="panel-hd">
        <h2>搜索结果</h2>
        <button type="button" class="link" @click="clearSearch">返回分类树</button>
      </div>
      <p v-if="searchLoading" class="hint">搜索中…</p>
      <p v-else-if="!searchResults.length" class="hint">未找到匹配词条。</p>
      <table v-else class="tbl tbl--desktop">
        <thead>
          <tr>
            <th>词条</th>
            <th>路径</th>
            <th>别名</th>
            <th>状态</th>
            <th v-if="canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in searchResults" :key="row.id">
            <td>{{ row.name }}</td>
            <td>{{ termPath(row) }}</td>
            <td>{{ row.aliases.join('、') || '—' }}</td>
            <td>{{ row.is_active ? '启用' : '停用' }}</td>
            <td v-if="canEdit">
              <button type="button" class="link" @click="openEdit(row)">编辑</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="split">
      <aside class="tree-panel panel">
        <div class="panel-hd">
          <h2>分类树</h2>
        </div>
        <p v-if="loading" class="hint">加载中…</p>
        <p v-else-if="!tree.length" class="hint">
          暂无分类。{{ canEdit ? '请点击「导入预置分类」一键初始化。' : '' }}
        </p>
        <ul v-else class="tree">
          <li v-for="l1 in tree" :key="l1.id" class="tree-l1">
            <div class="tree-row" :class="{ 'is-active': selectedL1Id === l1.id && !selectedL2Id }">
              <button type="button" class="tree-toggle" @click="toggleL1(l1.id)">
                {{ expandedL1.has(l1.id) ? '▼' : '▶' }}
              </button>
              <button type="button" class="tree-label" @click="selectL1(l1)">
                <span class="tree-code">{{ l1.code }}</span>{{ l1.name }}
              </button>
              <button v-if="canEdit" type="button" class="tree-add" title="新增子类" @click.stop="openCreate(2, l1)">+</button>
            </div>
            <ul v-show="expandedL1.has(l1.id)" class="tree-l2-list">
              <li v-for="l2 in l1.children" :key="l2.id">
                <div class="tree-row tree-row--l2" :class="{ 'is-active': selectedL2Id === l2.id }">
                  <button type="button" class="tree-label" @click="selectL2(l1, l2)">{{ l2.name }}</button>
                  <button v-if="canEdit" type="button" class="tree-add" title="新增词条" @click.stop="openCreate(3, l2)">+</button>
                </div>
              </li>
            </ul>
          </li>
        </ul>
      </aside>

      <section class="detail-panel panel">
        <div class="panel-hd">
          <h2>{{ detailTitle }}</h2>
          <div v-if="canEdit && selectedL2" class="panel-actions">
            <button type="button" class="primary" @click="openCreate(3, selectedL2)">+ 新增词条</button>
          </div>
        </div>

        <p v-if="!selectedL1 && !selectedL2" class="hint">请在左侧选择大类或子类。</p>

        <template v-else-if="selectedL2">
          <p v-if="termsLoading" class="hint">词条加载中…</p>
          <p v-else-if="!terms.length" class="hint">该子类下暂无词条。</p>
          <template v-else>
            <table class="tbl tbl--desktop">
              <thead>
                <tr>
                  <th>词条名称</th>
                  <th>别名</th>
                  <th>关键词</th>
                  <th>参考工时</th>
                  <th>参考费用</th>
                  <th>状态</th>
                  <th v-if="canEdit">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in terms" :key="t.id">
                  <td>{{ t.name }}</td>
                  <td class="col-wrap">{{ t.aliases.join('、') || '—' }}</td>
                  <td class="col-wrap">{{ t.keywords.join('、') || '—' }}</td>
                  <td>{{ t.standard_hours ?? '—' }}</td>
                  <td>{{ t.reference_cost ?? '—' }}</td>
                  <td>
                    <span :class="t.is_active ? 'badge badge--on' : 'badge badge--off'">
                      {{ t.is_active ? '启用' : '停用' }}
                    </span>
                  </td>
                  <td v-if="canEdit" class="actions">
                    <button type="button" class="link" @click="openEdit(t)">编辑</button>
                    <button type="button" class="link danger-text" @click="removeTerm(t)">删除</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <ul class="term-cards" aria-label="词条列表">
              <li v-for="t in terms" :key="`m-${t.id}`" class="term-card">
                <div class="term-card__top">
                  <strong>{{ t.name }}</strong>
                  <span :class="t.is_active ? 'badge badge--on' : 'badge badge--off'">
                    {{ t.is_active ? '启用' : '停用' }}
                  </span>
                </div>
                <p v-if="t.aliases.length"><span class="k">别名</span>{{ t.aliases.join('、') }}</p>
                <p v-if="t.keywords.length"><span class="k">关键词</span>{{ t.keywords.join('、') }}</p>
                <div v-if="canEdit" class="term-card__actions">
                  <button type="button" class="link" @click="openEdit(t)">编辑</button>
                  <button type="button" class="link danger-text" @click="removeTerm(t)">删除</button>
                </div>
              </li>
            </ul>
          </template>
        </template>

        <template v-else-if="selectedL1">
          <p class="sub-hint">「{{ selectedL1.name }}」下共 {{ selectedL1.children.length }} 个子类，请点击子类查看词条。</p>
          <ul class="sub-list">
            <li v-for="l2 in selectedL1.children" :key="l2.id">
              <button type="button" class="sub-pill" @click="selectL2(selectedL1, l2)">{{ l2.name }}</button>
            </li>
          </ul>
          <div v-if="canEdit" class="l1-actions">
            <button type="button" class="ghost" @click="openEdit(selectedL1)">编辑大类</button>
            <button type="button" class="ghost danger-text" @click="removeTerm(selectedL1)">删除大类</button>
          </div>
        </template>
      </section>
    </div>

    <AppModal :open="modalOpen" :title="modalTitle" @close="closeModal">
      <div class="form">
        <label class="field">
          <span class="field__label">名称</span>
          <input v-model="form.name" type="text" class="field__input" maxlength="128" />
        </label>
        <label v-if="form.level <= 2" class="field">
          <span class="field__label">编码</span>
          <input v-model="form.code" type="text" class="field__input" maxlength="32" placeholder="如 A、G01" />
        </label>
        <template v-if="form.level === 3">
          <label class="field">
            <span class="field__label">别名（逗号或换行分隔）</span>
            <textarea v-model="form.aliasesText" class="field__textarea" rows="3" placeholder="结算单可能出现的写法" />
          </label>
          <label class="field">
            <span class="field__label">关键词（逗号或换行分隔）</span>
            <textarea v-model="form.keywordsText" class="field__textarea" rows="2" placeholder="自动匹配用" />
          </label>
          <label class="field">
            <span class="field__label">参考工时（小时）</span>
            <input v-model="form.standard_hours" type="number" min="0" step="0.1" class="field__input" />
          </label>
          <label class="field">
            <span class="field__label">参考费用（元）</span>
            <input v-model="form.reference_cost" type="number" min="0" step="0.01" class="field__input" />
          </label>
        </template>
        <label class="field">
          <span class="field__label">排序</span>
          <input v-model.number="form.sort_order" type="number" min="0" class="field__input" />
        </label>
        <label class="field field--row-inline">
          <input v-model="form.is_active" type="checkbox" />
          <span>启用</span>
        </label>
        <label class="field">
          <span class="field__label">备注</span>
          <textarea v-model="form.remarks" class="field__textarea" rows="2" />
        </label>
        <p v-if="formError" class="form-error">{{ formError }}</p>
      </div>
      <template #footer>
        <button type="button" class="ghost" @click="closeModal">取消</button>
        <button type="button" class="primary" :disabled="saving" @click="saveForm">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import * as termsApi from '@/api/maintenanceTerms'
import type { MaintenanceTerm, MaintenanceTermStats, MaintenanceTermTreeNode } from '@/api/maintenanceTerms'
import AppModal from '@/components/AppModal.vue'
import { usePermissions } from '@/composables/usePermissions'

const perm = usePermissions()
const canEdit = computed(() => perm.canExportReports.value)

const tree = ref<MaintenanceTermTreeNode[]>([])
const stats = ref<MaintenanceTermStats | null>(null)
const terms = ref<MaintenanceTerm[]>([])
const searchResults = ref<MaintenanceTerm[]>([])
const loading = ref(false)
const termsLoading = ref(false)
const searchLoading = ref(false)
const seeding = ref(false)
const searchMode = ref(false)
const searchQ = ref('')
const msg = ref('')

const expandedL1 = ref<Set<number>>(new Set())
const selectedL1Id = ref<number | null>(null)
const selectedL2Id = ref<number | null>(null)

const selectedL1 = computed(() => tree.value.find((x) => x.id === selectedL1Id.value) ?? null)
const selectedL2 = computed(() => {
  const l1 = selectedL1.value
  if (!l1 || !selectedL2Id.value) return null
  return l1.children.find((x) => x.id === selectedL2Id.value) ?? null
})

const detailTitle = computed(() => {
  if (selectedL2.value) return `${selectedL1.value?.name ?? ''} / ${selectedL2.value.name}`
  if (selectedL1.value) return selectedL1.value.name
  return '词条详情'
})

const modalOpen = ref(false)
const saving = ref(false)
const formError = ref('')
const editingId = ref<number | null>(null)
const form = reactive({
  level: 3 as 1 | 2 | 3,
  parent_id: null as number | null,
  name: '',
  code: '',
  aliasesText: '',
  keywordsText: '',
  standard_hours: '' as string | number,
  reference_cost: '' as string | number,
  sort_order: 0,
  is_active: true,
  remarks: '',
})

const modalTitle = computed(() => {
  if (editingId.value) return '编辑'
  if (form.level === 1) return '新增一级大类'
  if (form.level === 2) return '新增二级子类'
  return '新增三级词条'
})

function splitLines(text: string): string[] {
  return text
    .split(/[\n,，;；]+/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function termPath(row: MaintenanceTerm): string {
  for (const l1 of tree.value) {
    if (l1.id === row.id) return l1.name
    for (const l2 of l1.children) {
      if (l2.id === row.id) return `${l1.name} / ${l2.name}`
      if (row.parent_id === l2.id) return `${l1.name} / ${l2.name}`
    }
  }
  return '—'
}

async function reloadAll() {
  loading.value = true
  msg.value = ''
  try {
    const res = await termsApi.getMaintenanceTermTree()
    tree.value = res.items
    stats.value = res.stats
    if (selectedL2Id.value) await loadTerms(selectedL2Id.value)
  } catch {
    msg.value = '加载分类树失败'
  } finally {
    loading.value = false
  }
}

async function loadTerms(parentId: number) {
  termsLoading.value = true
  try {
    const res = await termsApi.listMaintenanceTerms({ parent_id: parentId, level: 3, limit: 500 })
    terms.value = res.items
  } catch {
    msg.value = '加载词条失败'
  } finally {
    termsLoading.value = false
  }
}

function toggleL1(id: number) {
  const s = new Set(expandedL1.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  expandedL1.value = s
}

function selectL1(l1: MaintenanceTermTreeNode) {
  selectedL1Id.value = l1.id
  selectedL2Id.value = null
  terms.value = []
  expandedL1.value = new Set([...expandedL1.value, l1.id])
}

async function selectL2(l1: MaintenanceTermTreeNode, l2: MaintenanceTermTreeNode) {
  selectedL1Id.value = l1.id
  selectedL2Id.value = l2.id
  expandedL1.value = new Set([...expandedL1.value, l1.id])
  await loadTerms(l2.id)
}

async function runSearch() {
  const q = searchQ.value.trim()
  if (!q) {
    clearSearch()
    return
  }
  searchMode.value = true
  searchLoading.value = true
  try {
    const res = await termsApi.listMaintenanceTerms({ q, level: 3, limit: 200 })
    searchResults.value = res.items
  } catch {
    msg.value = '搜索失败'
  } finally {
    searchLoading.value = false
  }
}

function clearSearch() {
  searchMode.value = false
  searchResults.value = []
}

async function importPreset(force: boolean) {
  if (force && !window.confirm('将清空现有分类并重新导入预置数据，确定继续？')) return
  seeding.value = true
  msg.value = ''
  try {
    const res = await termsApi.seedMaintenanceTermsPreset(force)
    msg.value = res.message
    await reloadAll()
  } catch {
    msg.value = '导入预置分类失败'
  } finally {
    seeding.value = false
  }
}

function resetForm() {
  form.level = 3
  form.parent_id = null
  form.name = ''
  form.code = ''
  form.aliasesText = ''
  form.keywordsText = ''
  form.standard_hours = ''
  form.reference_cost = ''
  form.sort_order = 0
  form.is_active = true
  form.remarks = ''
  formError.value = ''
  editingId.value = null
}

function openCreate(level: 1 | 2 | 3, parent?: MaintenanceTermTreeNode) {
  resetForm()
  form.level = level
  if (level === 2 && parent) form.parent_id = parent.id
  if (level === 3 && parent) form.parent_id = parent.id
  modalOpen.value = true
}

function openEdit(row: MaintenanceTerm | MaintenanceTermTreeNode) {
  resetForm()
  editingId.value = row.id
  form.level = row.level
  form.parent_id = row.parent_id
  form.name = row.name
  form.code = row.code
  form.aliasesText = row.aliases.join('\n')
  form.keywordsText = row.keywords.join('\n')
  form.standard_hours = row.standard_hours ?? ''
  form.reference_cost = row.reference_cost ?? ''
  form.sort_order = row.sort_order
  form.is_active = row.is_active
  form.remarks = row.remarks ?? ''
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
  resetForm()
}

async function saveForm() {
  if (!form.name.trim()) {
    formError.value = '请填写名称'
    return
  }
  saving.value = true
  formError.value = ''
  const payload: termsApi.MaintenanceTermPayload = {
    level: form.level,
    name: form.name.trim(),
    code: form.code.trim(),
    sort_order: form.sort_order,
    is_active: form.is_active,
    remarks: form.remarks.trim() || null,
  }
  if (form.level >= 2) payload.parent_id = form.parent_id
  if (form.level === 3) {
    payload.aliases = splitLines(form.aliasesText)
    payload.keywords = splitLines(form.keywordsText)
    payload.standard_hours = form.standard_hours === '' ? null : Number(form.standard_hours)
    payload.reference_cost = form.reference_cost === '' ? null : Number(form.reference_cost)
  }
  try {
    if (editingId.value) {
      await termsApi.updateMaintenanceTerm(editingId.value, payload)
    } else {
      await termsApi.createMaintenanceTerm(payload)
    }
    closeModal()
    await reloadAll()
    if (selectedL2Id.value) await loadTerms(selectedL2Id.value)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    formError.value = err.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

async function removeTerm(row: MaintenanceTerm | MaintenanceTermTreeNode) {
  const label = row.level === 1 ? '大类' : row.level === 2 ? '子类' : '词条'
  if (!window.confirm(`确定删除该${label}「${row.name}」？`)) return
  try {
    await termsApi.deleteMaintenanceTerm(row.id)
    if (row.id === selectedL2Id.value) {
      selectedL2Id.value = null
      terms.value = []
    }
    if (row.id === selectedL1Id.value) selectedL1Id.value = null
    await reloadAll()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    msg.value = err.response?.data?.detail || '删除失败，请先删除下级内容'
  }
}

onMounted(() => {
  void reloadAll()
})
</script>

<style scoped>
.maint-terms {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.maint-terms__head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.maint-terms__title {
  margin: 0;
  font-size: 1.15rem;
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
}

.maint-terms__desc {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.maint-terms__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: var(--cl-olive);
  align-items: center;
}

.maint-terms__stats span {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--cl-warm-sand);
  border: 1px solid var(--cl-border-cream);
}

.perm-hint {
  padding: 8px 12px;
  border-radius: 10px;
  background: rgba(201, 100, 66, 0.08);
  color: #8a4b22;
  font-size: 13px;
}

.msg {
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(181, 51, 51, 0.35);
  background: rgba(181, 51, 51, 0.08);
  color: var(--cl-error);
  font-size: 13px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.search-input {
  flex: 1;
  min-width: 180px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  font-size: 13px;
}

.panel {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-ivory);
  border-radius: 16px;
  padding: 14px;
  box-shadow: rgba(0, 0, 0, 0.05) 0 4px 24px;
  min-width: 0;
}

.panel-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.panel-hd h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.split {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.tree-panel {
  max-height: calc(100vh - 220px);
  overflow: auto;
}

.tree {
  list-style: none;
  margin: 0;
  padding: 0;
}

.tree-l1 {
  margin-bottom: 4px;
}

.tree-l2-list {
  list-style: none;
  margin: 0 0 6px 18px;
  padding: 0;
}

.tree-row {
  display: flex;
  align-items: center;
  gap: 4px;
  border-radius: 10px;
  padding: 2px 4px;
}

.tree-row.is-active {
  background: rgba(201, 100, 66, 0.12);
}

.tree-row--l2 {
  padding-left: 8px;
}

.tree-toggle,
.tree-label,
.tree-add {
  border: 0;
  background: transparent;
  font: inherit;
  cursor: pointer;
  color: var(--cl-charcoal);
}

.tree-toggle {
  width: 22px;
  font-size: 10px;
  color: var(--cl-olive);
}

.tree-label {
  flex: 1;
  text-align: left;
  padding: 6px 4px;
  font-size: 13px;
}

.tree-code {
  display: inline-block;
  min-width: 1.2em;
  margin-right: 6px;
  font-weight: 700;
  color: var(--cl-olive);
}

.tree-add {
  padding: 2px 8px;
  border-radius: 8px;
  color: var(--cl-coral);
  font-weight: 700;
}

.detail-panel {
  min-height: 280px;
}

.sub-hint {
  color: var(--cl-olive);
  font-size: 13px;
}

.sub-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sub-pill {
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
}

.l1-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--cl-border-cream);
  text-align: left;
}

th {
  color: var(--cl-olive);
  background: var(--cl-warm-sand);
}

.col-wrap {
  max-width: 200px;
  word-break: break-word;
}

.actions {
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.badge--on {
  background: rgba(39, 143, 80, 0.14);
  color: #1d5e36;
}

.badge--off {
  background: rgba(142, 132, 109, 0.16);
  color: var(--cl-olive);
}

.term-cards {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 10px;
  flex-direction: column;
}

.term-card {
  border: 1px solid var(--cl-border-cream);
  border-radius: 12px;
  padding: 12px;
  background: var(--cl-white);
}

.term-card__top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.term-card p {
  margin: 4px 0;
  font-size: 13px;
  line-height: 1.45;
}

.term-card .k {
  color: var(--cl-olive);
  margin-right: 6px;
  font-weight: 700;
}

.term-card__actions {
  margin-top: 8px;
  display: flex;
  gap: 10px;
}

.hint {
  padding: 16px 8px;
  text-align: center;
  color: var(--cl-olive);
  font-size: 13px;
}

.primary {
  cursor: pointer;
  border: 0;
  border-radius: 10px;
  padding: 8px 14px;
  background: var(--cl-brand);
  color: var(--cl-ivory);
  font-weight: 600;
  font-size: 13px;
}

.ghost {
  cursor: pointer;
  border: 1px solid var(--cl-border-warm);
  background: transparent;
  color: var(--cl-charcoal);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 12px;
}

.link {
  border: 0;
  background: transparent;
  color: var(--cl-coral);
  cursor: pointer;
  padding: 0;
  font-size: 13px;
}

.danger-text {
  color: var(--cl-error);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field--row-inline {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.field__label {
  font-size: 12px;
  color: var(--cl-olive);
  font-weight: 600;
}

.field__input,
.field__textarea {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--cl-border-cream);
  background: var(--cl-white);
  font-size: 13px;
  font-family: inherit;
}

.form-error {
  color: var(--cl-error);
  font-size: 13px;
  margin: 0;
}

.muted {
  color: var(--cl-olive);
}

@media (max-width: 900px) {
  .split {
    grid-template-columns: 1fr;
  }

  .tree-panel {
    max-height: none;
  }

  .tbl--desktop {
    display: none;
  }

  .term-cards {
    display: flex;
  }
}
</style>
