<template>
  <div class="accounts-view">
    <template v-if="!perm.canManageAccounts">
      <p class="muted">当前账号无账户管理权限，请联系段级或超级管理员。</p>
    </template>
    <template v-else>
      <section class="role-intro" aria-label="账号分级说明">
        <h2 class="role-intro__title">账号分级（预留扩展）</h2>
        <p class="role-intro__hint">
          系统按五级管理登录账号。内置用户 <strong>admin</strong> 为超级管理员，角色不可降级、不可删除。
        </p>
        <ul v-if="roleDefs.length" class="role-intro__list">
          <li v-for="r in roleDefs" :key="r.code" class="role-intro__item">
            <span class="role-intro__badge">{{ r.label }}</span>
            <code class="role-intro__code">{{ r.code }}</code>
            <span v-if="r.description" class="role-intro__desc">{{ r.description }}</span>
          </li>
        </ul>
        <p v-else-if="!roleDefsLoading" class="muted">暂无分级说明数据</p>
      </section>

      <div class="toolbar">
        <div class="toolbar__search-wrap">
          <input
            v-model.trim="q"
            class="toolbar__search"
            type="search"
            placeholder="搜索用户名 / 显示名"
            aria-label="搜索账号"
            @keydown.enter.prevent="loadUsers"
          />
          <button type="button" class="btn btn--ghost" @click="loadUsers">搜索</button>
        </div>
        <button type="button" class="btn btn--primary" @click="openCreate">新建账号</button>
      </div>

      <p v-if="msg" class="msg" :class="{ 'msg--err': msgIsErr }">{{ msg }}</p>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>显示名</th>
              <th>分级</th>
              <th>状态</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in items" :key="row.id" class="data-table__row">
              <td data-label="用户名">
                <span class="mono">{{ row.username }}</span>
                <span v-if="row.username.toLowerCase() === 'admin'" class="tag tag--sys">内置</span>
              </td>
              <td data-label="显示名">{{ row.display_name }}</td>
              <td data-label="分级">{{ roleLabel(row.role) }}</td>
              <td data-label="状态">
                <span :class="row.is_active ? 'status status--on' : 'status status--off'">
                  {{ row.is_active ? '启用' : '停用' }}
                </span>
              </td>
              <td class="col-actions" data-label="操作">
                <div class="row-actions">
                  <button type="button" class="link-btn" :disabled="!canEditRow(row)" @click="openEdit(row)">
                    编辑
                  </button>
                  <button
                    type="button"
                    class="link-btn link-btn--danger"
                    :disabled="!canDeleteRow(row)"
                    @click="confirmDelete(row)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!items.length && !loading" class="muted empty">暂无账号数据</p>
      </div>

      <div v-if="total > limit" class="pager">
        <button type="button" class="btn btn--ghost pager__btn" :disabled="skip <= 0 || loading" @click="pagePrev">
          上一页
        </button>
        <span class="pager__info">第 {{ pageNum }} 页 · 共 {{ total }} 条</span>
        <button
          type="button"
          class="btn btn--ghost pager__btn"
          :disabled="skip + limit >= total || loading"
          @click="pageNext"
        >
          下一页
        </button>
      </div>

      <AppModal :open="modalOpen" :title="modalTitle" @close="closeModal">
        <div class="form-grid">
          <label class="field" v-if="modalMode === 'create'">
            <span>用户名</span>
            <input v-model.trim="form.username" class="inp" autocomplete="off" :disabled="saving" />
          </label>
          <label class="field">
            <span>显示名</span>
            <input v-model.trim="form.display_name" class="inp" autocomplete="off" :disabled="saving" />
          </label>
          <label class="field">
            <span>分级</span>
            <select v-model="form.role" class="inp" :disabled="saving || lockRole">
              <option
                v-for="opt in modalRoleOptions"
                :key="opt"
                :value="opt"
                :disabled="isRoleOptionDisabled(opt)"
              >
                {{ roleLabel(opt) }}{{ roleOptionSuffix(opt) }}
              </option>
            </select>
          </label>
          <label class="field field--row">
            <span>启用</span>
            <input v-model="form.is_active" type="checkbox" :disabled="saving || lockActive" />
          </label>
          <label class="field field--full">
            <span>{{ modalMode === 'create' ? '初始密码' : '新密码（留空则不修改）' }}</span>
            <input
              v-model="form.password"
              class="inp"
              type="password"
              autocomplete="new-password"
              :disabled="saving"
              placeholder="8-16 位，含大小写、数字与特殊字符"
            />
          </label>
        </div>
        <template #footer>
          <div class="modal-actions">
            <button type="button" class="btn btn--ghost" :disabled="saving" @click="closeModal">取消</button>
            <button type="button" class="btn btn--primary" :disabled="saving" @click="submitModal">
              {{ saving ? '保存中…' : '保存' }}
            </button>
          </div>
        </template>
      </AppModal>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import * as usersApi from '@/api/users'
import type { RoleDefinition, UserAdmin } from '@/api/users'
import AppModal from '@/components/AppModal.vue'
import { usePermissions } from '@/composables/usePermissions'
import { useUserStore } from '@/stores/user'

const perm = usePermissions()
const me = useUserStore()

/** 与后端 `/users/role-definitions` 顺序一致：由低到高五级，供新建/编辑下拉完整展示 */
const CANONICAL_ROLE_ORDER = [
  'vehicle_driver',
  'workshop_admin',
  'workshop_director',
  'section_admin',
  'super_admin',
] as const

const roleDefs = ref<RoleDefinition[]>([])
const roleDefsLoading = ref(false)
const assignable = ref<string[]>([])

const items = ref<UserAdmin[]>([])
const total = ref(0)
const skip = ref(0)
const limit = ref(50)
const q = ref('')
const loading = ref(false)

const msg = ref('')
const msgIsErr = ref(false)

const modalOpen = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingId = ref<number | null>(null)
const saving = ref(false)

const form = ref({
  username: '',
  display_name: '',
  role: 'vehicle_driver',
  is_active: true,
  password: '',
})

const modalTitle = computed(() => (modalMode.value === 'create' ? '新建账号' : '编辑账号'))

const pageNum = computed(() => Math.floor(skip.value / limit.value) + 1)

const assignableSet = computed(() => new Set(assignable.value))

const modalRoleOptions = computed(() => {
  const canonical = new Set<string>(CANONICAL_ROLE_ORDER as unknown as string[])
  const extra = new Set<string>()
  if (modalMode.value === 'edit' && editingId.value != null) {
    const row = items.value.find((x) => x.id === editingId.value)
    if (row && !canonical.has(row.role)) extra.add(row.role)
  }
  const ordered: string[] = []
  for (const code of CANONICAL_ROLE_ORDER) ordered.push(code)
  ordered.push(...[...extra].sort())
  return ordered
})

function defaultAssignableRole(): string {
  for (const code of CANONICAL_ROLE_ORDER) {
    if (assignableSet.value.has(code)) return code
  }
  return assignable.value[0] || 'vehicle_driver'
}

function isRoleOptionDisabled(opt: string): boolean {
  if (lockRole.value) return true
  if (assignableSet.value.has(opt)) return false
  if (modalMode.value === 'edit' && editingId.value != null) {
    const row = items.value.find((x) => x.id === editingId.value)
    if (row?.role === opt) return false
  }
  return true
}

function roleOptionSuffix(opt: string): string {
  if (assignableSet.value.has(opt) || lockRole.value) return ''
  if (modalMode.value === 'edit' && editingId.value != null) {
    const row = items.value.find((x) => x.id === editingId.value)
    if (row?.role === opt) return ''
  }
  return '（当前账号不可分配）'
}

const lockRole = computed(() => {
  if (modalMode.value !== 'edit' || !editingId.value) return false
  const row = items.value.find((x) => x.id === editingId.value)
  return row?.username.toLowerCase() === 'admin'
})

const lockActive = computed(() => {
  if (modalMode.value !== 'edit' || !editingId.value) return false
  const row = items.value.find((x) => x.id === editingId.value)
  return row?.username.toLowerCase() === 'admin'
})

function isSuperActor() {
  const r = me.profile?.role || ''
  return r === 'super_admin' || r === 'admin'
}

function canEditRow(row: UserAdmin) {
  if (row.username.toLowerCase() === 'admin') return isSuperActor()
  if ((row.role === 'super_admin' || row.role === 'admin') && !isSuperActor()) return false
  return true
}

function canDeleteRow(row: UserAdmin) {
  if (row.username.toLowerCase() === 'admin') return false
  if ((row.role === 'super_admin' || row.role === 'admin') && !isSuperActor()) return false
  return true
}

function roleLabel(role: string) {
  const m: Record<string, string> = {
    super_admin: '超级管理员',
    section_admin: '段级管理员',
    workshop_director: '车间主任',
    workshop_admin: '车间管理员',
    vehicle_driver: '车辆驾驶员',
    admin: '管理员(旧)',
    fleet_manager: '车管(旧)',
    driver: '驾驶员(旧)',
    staff: '普通用户(旧)',
  }
  return m[role] || role
}

async function loadMeta() {
  roleDefsLoading.value = true
  try {
    const [defs, roles] = await Promise.all([
      usersApi.fetchRoleDefinitions(),
      usersApi.fetchAssignableRoles(),
    ])
    roleDefs.value = defs
    assignable.value = roles
    if (roles.length && !roles.includes(form.value.role)) {
      form.value.role = defaultAssignableRole()
    }
  } catch {
    roleDefs.value = []
  } finally {
    roleDefsLoading.value = false
  }
}

async function loadUsers() {
  loading.value = true
  msg.value = ''
  try {
    const res = await usersApi.listUsers({ skip: skip.value, limit: limit.value, q: q.value || undefined })
    items.value = res.items
    total.value = res.total
  } catch (e: unknown) {
    msg.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '加载账号列表失败'
    msgIsErr.value = true
  } finally {
    loading.value = false
  }
}

function pagePrev() {
  skip.value = Math.max(0, skip.value - limit.value)
  loadUsers()
}

function pageNext() {
  skip.value = skip.value + limit.value
  loadUsers()
}

function openCreate() {
  modalMode.value = 'create'
  editingId.value = null
  form.value = {
    username: '',
    display_name: '',
    role: defaultAssignableRole(),
    is_active: true,
    password: '',
  }
  modalOpen.value = true
}

function openEdit(row: UserAdmin) {
  modalMode.value = 'edit'
  editingId.value = row.id
  form.value = {
    username: row.username,
    display_name: row.display_name,
    role: row.role,
    is_active: row.is_active,
    password: '',
  }
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
}

async function submitModal() {
  saving.value = true
  msg.value = ''
  msgIsErr.value = false
  try {
    if (modalMode.value === 'create') {
      if (!form.value.username || !form.value.display_name) {
        msg.value = '请填写用户名与显示名'
        msgIsErr.value = true
        return
      }
      if (!form.value.password) {
        msg.value = '请设置初始密码'
        msgIsErr.value = true
        return
      }
      await usersApi.createUser({
        username: form.value.username,
        display_name: form.value.display_name,
        role: form.value.role,
        is_active: form.value.is_active,
        password: form.value.password,
      })
    } else if (editingId.value != null) {
      const body: { display_name?: string; password?: string; role?: string; is_active?: boolean } = {
        display_name: form.value.display_name,
        role: form.value.role,
        is_active: form.value.is_active,
      }
      if (form.value.password.trim()) {
        body.password = form.value.password
      }
      const updated = await usersApi.updateUser(editingId.value, body)
      if (me.profile?.id === updated.id) {
        await me.fetchMe()
      }
    }
    modalOpen.value = false
    await loadUsers()
  } catch (e: unknown) {
    const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    msg.value = typeof d === 'string' ? d : '保存失败'
    msgIsErr.value = true
  } finally {
    saving.value = false
  }
}

async function confirmDelete(row: UserAdmin) {
  if (row.username.toLowerCase() === 'admin') return
  if (!window.confirm(`确定删除用户「${row.username}」？`)) return
  msg.value = ''
  msgIsErr.value = false
  try {
    await usersApi.deleteUser(row.id)
    if (me.profile?.id === row.id) {
      me.logout()
      return
    }
    await loadUsers()
  } catch (e: unknown) {
    const d = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    msg.value = typeof d === 'string' ? d : '删除失败'
    msgIsErr.value = true
  }
}

onMounted(async () => {
  if (!perm.canManageAccounts.value) return
  await loadMeta()
  await loadUsers()
})
</script>

<style scoped>
.accounts-view {
  width: 100%;
  max-width: min(1160px, 100%);
  margin: 0 auto;
  box-sizing: border-box;
  padding-inline: 0;
}

.role-intro {
  margin-bottom: 1.25rem;
  padding: 1rem 1.15rem;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: rgba(255, 255, 255, 0.55);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.role-intro__title {
  margin: 0 0 0.5rem;
  font-size: clamp(1rem, 2.5vw, 1.12rem);
  font-weight: 600;
}

.role-intro__hint {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  color: var(--cl-olive);
  line-height: 1.55;
}

.role-intro__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.65rem;
}

.role-intro__item {
  display: grid;
  grid-template-columns: minmax(0, 7.5rem) 1fr;
  gap: 0.35rem 0.75rem;
  align-items: baseline;
  font-size: 0.875rem;
  padding: 0.55rem 0.65rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.45);
  border: 1px solid rgba(142, 132, 109, 0.18);
}

.role-intro__badge {
  font-weight: 600;
  color: var(--cl-charcoal);
}

.role-intro__code {
  grid-column: 1 / -1;
  font-size: 0.72rem;
  color: var(--cl-stone);
  word-break: break-all;
}

.role-intro__desc {
  grid-column: 1 / -1;
  color: var(--cl-olive);
  line-height: 1.45;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.toolbar__search-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1 1 220px;
  min-width: 0;
}

.toolbar__search {
  flex: 1;
  min-width: 0;
  min-height: 44px;
  padding: 0.5rem 0.7rem;
  border-radius: 10px;
  border: 1px solid var(--cl-border-warm);
  font: inherit;
  box-sizing: border-box;
}

.btn {
  cursor: pointer;
  border-radius: 10px;
  padding: 0.5rem 1rem;
  min-height: 44px;
  font-size: 0.875rem;
  font-weight: 500;
  border: 1px solid var(--cl-border-warm);
  background: var(--cl-warm-sand);
  color: var(--cl-charcoal);
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  box-sizing: border-box;
}

.btn--primary {
  background: var(--cl-terracotta);
  border-color: rgba(201, 100, 66, 0.5);
  color: #fff;
}

.btn--ghost {
  background: transparent;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.msg {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  color: var(--cl-olive);
  line-height: 1.45;
}

.msg--err {
  color: #a33;
}

.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-inline: 0;
  border-radius: 12px;
  border: 1px solid var(--cl-border-cream);
  background: rgba(255, 255, 255, 0.35);
}

.data-table {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th,
.data-table td {
  padding: 0.65rem 0.65rem;
  text-align: left;
  border-bottom: 1px solid var(--cl-border-cream);
  vertical-align: middle;
}

.data-table th {
  font-weight: 600;
  color: var(--cl-olive);
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: none;
  background: rgba(250, 249, 245, 0.85);
}

.data-table tbody tr:last-child td {
  border-bottom: none;
}

.data-table__row:hover td {
  background: rgba(245, 229, 218, 0.22);
}

.mono {
  font-family: ui-monospace, 'Cascadia Mono', monospace;
  font-size: 0.82em;
}

.tag {
  margin-left: 0.35rem;
  font-size: 0.65rem;
  padding: 0.12rem 0.38rem;
  border-radius: 4px;
  vertical-align: middle;
}

.tag--sys {
  background: rgba(201, 100, 66, 0.15);
  color: var(--cl-terracotta);
}

.status--on {
  color: #2a6;
  font-weight: 500;
}

.status--off {
  color: #a55;
  font-weight: 500;
}

.col-actions {
  white-space: nowrap;
  width: 8.5rem;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
}

.link-btn {
  cursor: pointer;
  border: none;
  background: none;
  color: var(--cl-terracotta);
  font-size: inherit;
  padding: 0.35rem 0.25rem;
  min-height: 40px;
  text-decoration: underline;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.link-btn--danger {
  color: #a33;
}

.link-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  text-decoration: none;
}

.empty {
  padding: 1.25rem 0.75rem;
  text-align: center;
}

.pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-start;
  gap: 0.65rem;
  margin-top: 1.1rem;
  font-size: 0.875rem;
}

.pager__info {
  flex: 1 1 auto;
  color: var(--cl-olive);
  min-width: 10rem;
}

.pager__btn {
  flex: 0 0 auto;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem 1.1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.875rem;
}

.field--full {
  grid-column: 1 / -1;
}

.field--row {
  flex-direction: row;
  align-items: center;
  gap: 0.55rem;
}

.inp {
  min-height: 44px;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  border: 1px solid var(--cl-border-warm);
  font: inherit;
  box-sizing: border-box;
  width: 100%;
}

select.inp {
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.modal-actions .btn {
  min-width: 6.5rem;
}

.muted {
  color: var(--cl-olive);
  font-size: 0.875rem;
  line-height: 1.65;
}

/* 宽屏：分级说明多列 */
@media (min-width: 900px) {
  .role-intro__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.75rem 1rem;
  }
}

@media (min-width: 1200px) {
  .role-intro__list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

/* 移动端：表格改为卡片行 */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar__search-wrap {
    flex: none;
    width: 100%;
  }

  .toolbar .btn--primary {
    width: 100%;
  }

  .table-wrap {
    border: none;
    background: transparent;
    overflow: visible;
  }

  .data-table {
    min-width: 0;
  }

  .data-table thead {
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

  .data-table tbody {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .data-table tr.data-table__row {
    display: block;
    border: 1px solid var(--cl-border-cream);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.55);
    box-shadow: 0 2px 12px rgba(20, 20, 19, 0.06);
  }

  .data-table tr.data-table__row:hover td {
    background: transparent;
  }

  .data-table td {
    display: grid;
    grid-template-columns: 5.2rem 1fr;
    gap: 0.35rem 0.65rem;
    align-items: start;
    padding: 0.55rem 0.75rem;
    border-bottom: 1px solid var(--cl-border-cream);
    text-align: left;
  }

  .data-table td:last-child {
    border-bottom: none;
  }

  .data-table td::before {
    content: attr(data-label);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--cl-olive);
    letter-spacing: 0.04em;
  }

  .col-actions {
    width: auto;
    white-space: normal;
  }

  .row-actions {
    justify-content: flex-start;
  }

  .pager {
    flex-direction: column;
    align-items: stretch;
  }

  .pager__info {
    text-align: center;
    order: -1;
  }

  .pager__btn {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .role-intro__item {
    grid-template-columns: 1fr;
  }

  .role-intro__badge {
    font-size: 0.92rem;
  }
}
</style>
