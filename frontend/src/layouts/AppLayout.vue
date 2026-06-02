<template>
  <div
    class="shell"
    :class="{
      'shell--collapsed': !sidebarExpanded && !isMobileShell,
      'shell--mobile': isMobileShell,
      'shell--flyout-open': Boolean(flyoutOpenId) && navIconsOnly,
    }"
  >
    <div
      v-if="isMobileShell && mobileNavOpen"
      class="nav-backdrop"
      aria-hidden="true"
      @click="mobileNavOpen = false"
    />
    <!-- 收起态分组浮层：点击空白关闭 -->
    <div
      v-if="flyoutOpenId && navIconsOnly"
      class="nav-flyout-backdrop"
      aria-hidden="true"
      @click="closeGroupFlyout"
    />
    <aside
      id="app-sidebar"
      class="aside"
      :class="{
        'aside--collapsed': !sidebarExpanded && !isMobileShell,
        'aside--mobile-open': isMobileShell && mobileNavOpen,
      }"
      @mouseenter="onAsideEnter"
      @mouseleave="onAsideLeave"
      @focusin="onAsideFocusIn"
      @focusout="onAsideFocusOut"
    >
      <div class="brand">
        <div class="brand-accent" aria-hidden="true" />
        <div class="brand-title">哈尔滨工务段汽车管理信息系统</div>
        <div class="brand-sub">公务车业务台</div>
      </div>

      <p class="nav-label">功能导航</p>
      <nav class="nav" aria-label="功能导航">
        <template v-for="piece in navItems" :key="isGroup(piece) ? piece.id : piece.to">
          <div
            v-if="isGroup(piece)"
            class="nav-group"
            :class="{
              'nav-group--open': groupOpen[piece.id],
              'nav-group--rail': navIconsOnly,
            }"
          >
            <!-- 收起态：每组仅一个图标，子菜单在侧向浮层中展示 -->
            <template v-if="navIconsOnly">
              <div class="nav-group-rail">
                <button
                  type="button"
                  class="nav-item nav-item--rail"
                  :class="{
                    'nav-item--rail-active': flyoutOpenId === piece.id,
                    'nav-item--rail-current': isGroupChildActive(piece),
                  }"
                  :data-rail-flyout="piece.id"
                  :aria-expanded="flyoutOpenId === piece.id ? 'true' : 'false'"
                  :aria-controls="`nav-flyout-${piece.id}`"
                  :title="piece.label"
                  @click.stop="toggleGroupFlyout(piece.id, $event)"
                >
                  <NavIcon :name="piece.icon" class="nav-ico" />
                </button>
              </div>
            </template>
            <template v-else>
              <button
                type="button"
                class="nav-group__trigger"
                :aria-expanded="groupOpen[piece.id] ? 'true' : 'false'"
                :aria-controls="`nav-group-${piece.id}-panel`"
                @click="toggleGroup(piece.id)"
              >
                <NavIcon :name="piece.icon" class="nav-ico" />
                <span class="nav-text">{{ piece.label }}</span>
                <span class="nav-group__chevron" aria-hidden="true">▼</span>
              </button>
              <div
                v-show="groupOpen[piece.id]"
                :id="`nav-group-${piece.id}-panel`"
                class="nav-group__children"
                role="group"
                :aria-label="piece.label"
              >
                <RouterLink
                  v-for="child in piece.children"
                  :key="child.to"
                  class="nav-item nav-item--child"
                  :to="child.to"
                  :title="child.label"
                >
                  <NavIcon :name="child.icon" class="nav-ico" />
                  <span class="nav-text">{{ child.label }}</span>
                </RouterLink>
              </div>
            </template>
          </div>
          <RouterLink
            v-else
            class="nav-item nav-item--root"
            :to="piece.to"
            :title="piece.label"
          >
            <NavIcon :name="piece.icon" class="nav-ico" />
            <span class="nav-text">{{ piece.label }}</span>
          </RouterLink>
        </template>
      </nav>
    </aside>

    <section class="main">
      <header class="top">
        <button
          v-if="isMobileShell"
          type="button"
          class="nav-toggle"
          aria-label="打开导航菜单"
          :aria-expanded="mobileNavOpen"
          aria-controls="app-sidebar"
          @click="mobileNavOpen = !mobileNavOpen"
        >
          <span class="nav-toggle__bar" aria-hidden="true" />
          <span class="nav-toggle__bar" aria-hidden="true" />
          <span class="nav-toggle__bar" aria-hidden="true" />
        </button>
        <div class="crumb">{{ title }}</div>
        <div class="user">
          <span v-if="user.profile" class="who">
            {{ user.profile.display_name }}（{{ user.profile.username }}）
            <span class="role">{{ roleLabel(user.profile.role) }}</span>
          </span>
          <button type="button" class="btn" @click="onLogout">退出</button>
        </div>
      </header>

      <div class="content">
        <RouterView />
      </div>
    </section>

    <Teleport to="body">
      <div
        v-if="activeFlyoutGroup && flyoutRect && navIconsOnly"
        :id="`nav-flyout-${activeFlyoutGroup.id}`"
        class="nav-flyout nav-flyout--fixed"
        role="menu"
        :aria-label="activeFlyoutGroup.label"
        :style="{ top: `${flyoutRect.top}px`, left: `${flyoutRect.left}px` }"
        @click.stop
      >
        <div class="nav-flyout__caption">{{ activeFlyoutGroup.label }}</div>
        <RouterLink
          v-for="child in activeFlyoutGroup.children"
          :key="child.to"
          class="nav-flyout__link"
          role="menuitem"
          :to="child.to"
          @click="closeGroupFlyout"
        >
          <NavIcon :name="child.icon" class="nav-ico" />
          <span>{{ child.label }}</span>
        </RouterLink>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import NavIcon, { type NavIconName } from '@/components/NavIcon.vue'
import { usePermissions } from '@/composables/usePermissions'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const perm = usePermissions()

type NavNeed = 'fleet' | 'reports' | 'accounts'

interface NavLeaf {
  to: string
  label: string
  icon: NavIconName
  need?: NavNeed
}

interface NavGroupDef {
  id: string
  label: string
  icon: NavIconName
  children: NavLeaf[]
}

type NavPiece = NavLeaf | NavGroupDef

function isGroup(p: NavPiece): p is NavGroupDef {
  return 'children' in p
}

const navSource: NavPiece[] = [
  { to: '/app/dashboard', label: '工作台', icon: 'dashboard' },
  { to: '/app/location-navigation', label: '段内导航', icon: 'location' },
  { to: '/app/fuel', label: '油卡余额', icon: 'fuel' },
  { to: '/app/occupancy-query', label: '车辆调度', icon: 'reports' },
  { to: '/app/ai-data-analysis', label: 'AI数据分析', icon: 'aiAnalysis', need: 'reports' },
  { to: '/app/ai-data-learning', label: 'AI数据学习', icon: 'aiLearning', need: 'reports' },
  {
    id: 'basic',
    label: '基础管理',
    icon: 'basics',
    children: [
      { to: '/app/vehicles', label: '车辆管理', icon: 'vehicles' },
      { to: '/app/drivers', label: '驾驶员管理', icon: 'drivers', need: 'fleet' },
      { to: '/app/accounts', label: '账户管理', icon: 'accounts', need: 'accounts' },
    ],
  },
  {
    id: 'usage',
    label: '使用管理',
    icon: 'usage',
    children: [
      { to: '/app/trips', label: '用车申请', icon: 'trips' },
      { to: '/app/tracking', label: '定位管理', icon: 'location' },
      { to: '/app/approvals', label: '审批流转', icon: 'approval' },
      { to: '/app/fuel-records', label: '加油记录', icon: 'fuel' },
      { to: '/app/repair-records', label: '维修记录', icon: 'maintenance' },
    ],
  },
  {
    id: 'expense',
    label: '费用管理',
    icon: 'expenses',
    children: [
      { to: '/app/fuel-bills', label: '油卡账单', icon: 'fuel' },
      { to: '/app/maintenance', label: '维修保养', icon: 'maintenance' },
      { to: '/app/insurance', label: '保险动态', icon: 'insurance' },
      { to: '/app/inspection', label: '检车动态', icon: 'inspection' },
      { to: '/app/access', label: '通行动态', icon: 'access' },
    ],
  },
  {
    id: 'data',
    label: '数据管理',
    icon: 'reports',
    children: [
      { to: '/app/data-vehicle-export', label: '车辆档案导出', icon: 'vehicles', need: 'reports' },
      { to: '/app/data-driver-export', label: '驾驶员档案导出', icon: 'drivers', need: 'reports' },
      { to: '/app/data-maintenance-terms', label: '维修词条管理', icon: 'maintenance', need: 'reports' },
      { to: '/app/data-vehicle-usage-analysis', label: '车辆使用分析', icon: 'usage', need: 'reports' },
      { to: '/app/data-fuel-consumption-analysis', label: '燃油消耗分析', icon: 'fuel', need: 'reports' },
      { to: '/app/data-maintenance-analysis', label: '维修数据分析', icon: 'maintenance', need: 'reports' },
    ],
  },
]

function leafVisible(leaf: NavLeaf): boolean {
  if (leaf.need === 'fleet') return perm.canManageFleet.value
  if (leaf.need === 'reports') return perm.canExportReports.value
  if (leaf.need === 'accounts') return perm.canManageAccounts.value
  return true
}

const navItems = computed(() => {
  const out: NavPiece[] = []
  for (const piece of navSource) {
    if (isGroup(piece)) {
      const children = piece.children.filter(leafVisible)
      if (children.length) out.push({ ...piece, children })
    } else if (leafVisible(piece)) {
      out.push(piece)
    }
  }
  return out
})

/** 分组展开：路由落在子项时自动展开 */
const groupOpen = reactive<Record<string, boolean>>({})

function toggleGroup(id: string) {
  groupOpen[id] = !groupOpen[id]
}

function syncGroupsFromPath(path: string) {
  for (const piece of navSource) {
    if (!isGroup(piece)) continue
    const hit = piece.children.some((c) => path === c.to || path.startsWith(`${c.to}/`))
    if (hit) groupOpen[piece.id] = true
  }
}

const title = computed(() => (route.meta.title as string) || '业务')

/** 窄屏：侧栏改为抽屉，不占主区域宽度 */
const MOBILE_SHELL_MQ = '(max-width: 768px)'
/** 粗指针 + 足够宽：侧栏类名仍含 collapsed，但 UI 上展示完整文字（与样式块一致） */
const COARSE_WIDE_MQ = '(hover: none) and (min-width: 769px)'
const isMobileShell = ref(false)
const coarsePointerWide = ref(false)
const mobileNavOpen = ref(false)

/** 默认收起；鼠标移入侧栏或焦点在侧栏内时展开（仅桌面） */
const sidebarExpanded = ref(true)

/** 收起态窄轨：仅显示图标；分组用单图标 + 侧向浮层展示子菜单 */
const navIconsOnly = computed(
  () => !sidebarExpanded.value && !isMobileShell.value && !coarsePointerWide.value,
)

const flyoutOpenId = ref<string | null>(null)
const flyoutRect = ref<{ top: number; left: number } | null>(null)

const activeFlyoutGroup = computed<NavGroupDef | null>(() => {
  const id = flyoutOpenId.value
  if (!id) return null
  for (const p of navItems.value) {
    if (isGroup(p) && p.id === id) return p
  }
  return null
})

function isGroupChildActive(piece: NavGroupDef) {
  return piece.children.some((c) => route.path === c.to || route.path.startsWith(`${c.to}/`))
}

function toggleGroupFlyout(id: string, e: MouseEvent) {
  if (flyoutOpenId.value === id) {
    flyoutOpenId.value = null
    flyoutRect.value = null
    return
  }
  flyoutOpenId.value = id
  const btn = e.currentTarget as HTMLElement
  const r = btn.getBoundingClientRect()
  const gap = 8
  const panelW = 232
  let left = r.right + gap
  if (left + panelW > window.innerWidth - 10) {
    left = Math.max(10, r.left - panelW - gap)
  }
  flyoutRect.value = {
    top: Math.max(8, r.top),
    left,
  }
}

function closeGroupFlyout() {
  flyoutOpenId.value = null
  flyoutRect.value = null
}

function onFlyoutEscape(e: KeyboardEvent) {
  if (e.key !== 'Escape' || !flyoutOpenId.value) return
  closeGroupFlyout()
}

function onFlyoutViewportChange() {
  if (flyoutOpenId.value) closeGroupFlyout()
}

watch(
  () => route.path,
  () => {
    closeGroupFlyout()
  },
)

watch(navIconsOnly, () => {
  closeGroupFlyout()
})

let asideLeaveTimer: ReturnType<typeof setTimeout> | null = null

function syncMobileShell() {
  if (typeof window === 'undefined') return
  isMobileShell.value = window.matchMedia(MOBILE_SHELL_MQ).matches
  coarsePointerWide.value = window.matchMedia(COARSE_WIDE_MQ).matches
  if (isMobileShell.value) {
    sidebarExpanded.value = true
    mobileNavOpen.value = false
  }
}

function onAsideEnter() {
  if (isMobileShell.value) return
  if (asideLeaveTimer) {
    clearTimeout(asideLeaveTimer)
    asideLeaveTimer = null
  }
  sidebarExpanded.value = true
}

function onAsideLeave() {
  if (isMobileShell.value) return
  if (asideLeaveTimer) clearTimeout(asideLeaveTimer)
  asideLeaveTimer = setTimeout(() => {
    sidebarExpanded.value = false
    asideLeaveTimer = null
  }, 140)
}

function onAsideFocusIn() {
  onAsideEnter()
}

function onAsideFocusOut(e: FocusEvent) {
  const aside = e.currentTarget as HTMLElement
  const next = e.relatedTarget as Node | null
  if (!next || !aside.contains(next)) {
    if (aside.matches(':hover')) return
    onAsideLeave()
  }
}

function roleLabel(role: string) {
  const m: Record<string, string> = {
    super_admin: '超级管理员',
    section_admin: '段级管理员',
    workshop_director: '车间主任',
    workshop_admin: '车间管理员',
    vehicle_driver: '车辆驾驶员',
    admin: '超级管理员',
    fleet_manager: '段级管理员',
    driver: '车辆驾驶员',
    staff: '普通用户',
  }
  return m[role] || role
}

let mobileMq: MediaQueryList | null = null
let coarseWideMq: MediaQueryList | null = null
function onLayoutMqChange() {
  syncMobileShell()
}

onMounted(async () => {
  syncMobileShell()
  mobileMq = window.matchMedia(MOBILE_SHELL_MQ)
  mobileMq.addEventListener('change', onLayoutMqChange)
  coarseWideMq = window.matchMedia(COARSE_WIDE_MQ)
  coarseWideMq.addEventListener('change', onLayoutMqChange)
  window.addEventListener('keydown', onFlyoutEscape)
  window.addEventListener('resize', onFlyoutViewportChange)
  window.addEventListener('scroll', onFlyoutViewportChange, true)

  if (!user.profile) {
    try {
      await user.fetchMe()
    } catch {
      user.logout()
      await router.replace('/login')
    }
  }
})

watch(
  () => route.fullPath,
  () => {
    mobileNavOpen.value = false
    syncGroupsFromPath(route.path)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (asideLeaveTimer) clearTimeout(asideLeaveTimer)
  mobileMq?.removeEventListener('change', onLayoutMqChange)
  coarseWideMq?.removeEventListener('change', onLayoutMqChange)
  window.removeEventListener('keydown', onFlyoutEscape)
  window.removeEventListener('resize', onFlyoutViewportChange)
  window.removeEventListener('scroll', onFlyoutViewportChange, true)
})

async function onLogout() {
  user.logout()
  await router.replace('/login')
}
</script>

<style scoped>
.shell {
  height: 100%;
  max-height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: 272px 1fr;
  grid-template-rows: minmax(0, 1fr);
  background: var(--cl-parchment);
  color: var(--cl-near-black);
  transition: grid-template-columns 0.24s ease;
  overflow: hidden;
}

.shell--collapsed {
  /* 略增宽度：为细滚动条 + 图标槽位留余量，避免与纵向滚动条抢横向空间 */
  grid-template-columns: 80px 1fr;
}

.aside {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  min-height: 0;
  align-self: stretch;
  box-sizing: border-box;
  border-right: 1px solid var(--cl-border-warm);
  background: linear-gradient(165deg, #fdfcf7 0%, var(--cl-ivory) 48%, #f3f1e8 100%);
  padding: 24px 16px 20px;
  box-shadow:
    rgba(0, 0, 0, 0.04) 0px 4px 24px,
    inset -1px 0 0 rgba(255, 255, 255, 0.45);
  overflow-x: hidden;
  overflow-y: auto;
}

/* 仅展开态预留滚动条槽位；收起态过窄，stable 会与粗滚动条叠加导致排版挤压 */
.aside:not(.aside--collapsed) {
  scrollbar-gutter: stable;
}

.aside--collapsed {
  padding: 12px 5px 10px;
  overflow-x: clip;
  scrollbar-width: thin;
  scrollbar-color: rgba(142, 132, 109, 0.42) transparent;
}

.aside--collapsed::-webkit-scrollbar {
  width: 5px;
}

.aside--collapsed::-webkit-scrollbar-track {
  background: transparent;
}

.aside--collapsed::-webkit-scrollbar-thumb {
  background: rgba(142, 132, 109, 0.38);
  border-radius: 999px;
}

.brand {
  padding-bottom: 20px;
  margin-bottom: 6px;
  border-bottom: 1px solid var(--cl-border-cream);
}

.brand-accent {
  width: 40px;
  height: 3px;
  border-radius: 2px;
  margin-bottom: 14px;
  background: linear-gradient(90deg, var(--cl-terracotta), rgba(201, 100, 66, 0.45));
}

.brand-title {
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-weight: 500;
  font-size: 1.05rem;
  line-height: 1.35;
  letter-spacing: -0.02em;
  color: var(--cl-near-black);
  word-break: break-word;
}

.brand-sub {
  margin-top: 10px;
  font-size: 0.8125rem;
  font-weight: 400;
  letter-spacing: 0.06em;
  color: var(--cl-olive);
  line-height: 1.55;
}

.nav-label {
  margin: 18px 0 10px 4px;
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.28em;
  color: var(--cl-olive);
  opacity: 0.9;
}

.aside--collapsed .brand-title,
.aside--collapsed .brand-sub,
.aside--collapsed .nav-label {
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

.aside--collapsed .brand {
  padding-bottom: 10px;
  margin-bottom: 2px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.aside--collapsed .brand-accent {
  width: 26px;
  margin-bottom: 0;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-height: 0;
  padding-right: 2px;
}

.aside--collapsed .nav {
  padding-right: 0;
  align-items: center;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-group__trigger {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px 11px 16px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 0.92rem;
  line-height: 1.3;
  letter-spacing: 0.03em;
  color: var(--cl-charcoal);
  text-align: left;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.nav-group__trigger:hover {
  color: var(--cl-near-black);
  background: var(--cl-warm-sand);
  box-shadow: var(--cl-warm-sand) 0px 0px 0px 0px, var(--cl-ring-warm) 0px 0px 0px 1px;
  transform: translateX(1px);
}

.nav-group__trigger:hover .nav-ico {
  color: var(--cl-terracotta);
  opacity: 1;
}

.nav-group__trigger:focus-visible {
  outline: 2px solid var(--cl-terracotta);
  outline-offset: 2px;
}

.nav-group__chevron {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 8px;
  line-height: 1;
  opacity: 0.55;
  transition: transform 0.2s ease;
}

.nav-group--open .nav-group__chevron {
  transform: rotate(-180deg);
}

.nav-group__children {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-left: 8px;
  margin-left: 18px;
  border-left: 2px solid var(--cl-border-cream);
}

/* 收起窄轨：每组一条图标 + 侧向浮层（不再平铺所有子项图标） */
.nav-group-rail {
  position: relative;
  z-index: 0;
}

.nav-group--rail + .nav-group--rail,
.nav-item--root + .nav-group--rail {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed rgba(142, 132, 109, 0.28);
}

.nav-item--rail {
  cursor: pointer;
  border: none;
  font: inherit;
}

.nav-item--rail-current:not(.nav-item--rail-active) {
  border-color: rgba(201, 100, 66, 0.28);
  background: rgba(201, 100, 66, 0.08);
}

.nav-flyout {
  min-width: 208px;
  max-width: min(280px, calc(100vw - 96px));
  max-height: min(420px, calc(100vh - 32px));
  overflow-x: hidden;
  overflow-y: auto;
  padding: 8px 6px;
  border-radius: 12px;
  border: 1px solid var(--cl-border-warm);
  background: linear-gradient(165deg, #fdfcf7 0%, var(--cl-ivory) 100%);
  box-shadow:
    0 10px 34px rgba(20, 20, 19, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.75);
  scrollbar-width: thin;
  scrollbar-color: rgba(142, 132, 109, 0.42) transparent;
}

.nav-flyout--fixed {
  position: fixed;
  z-index: 140;
  margin: 0;
}

.nav-flyout::-webkit-scrollbar {
  width: 5px;
}

.nav-flyout::-webkit-scrollbar-thumb {
  background: rgba(142, 132, 109, 0.35);
  border-radius: 999px;
}

.nav-flyout__caption {
  padding: 6px 10px 8px;
  margin-bottom: 4px;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: var(--cl-olive);
  border-bottom: 1px solid var(--cl-border-cream);
}

.nav-flyout__link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  text-decoration: none;
  color: var(--cl-charcoal);
  font-size: 0.875rem;
  line-height: 1.3;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.nav-flyout__link:hover {
  background: var(--cl-warm-sand);
  color: var(--cl-near-black);
}

.nav-flyout__link.router-link-active {
  background: rgba(201, 100, 66, 0.12);
  color: var(--cl-near-black);
  font-weight: 500;
}

.nav-flyout__link .nav-ico {
  flex-shrink: 0;
}

.nav-flyout-backdrop {
  position: fixed;
  inset: 0;
  z-index: 125;
  background: rgba(20, 20, 19, 0.08);
  backdrop-filter: blur(1px);
}

.shell--flyout-open .aside {
  z-index: 130;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: var(--cl-charcoal);
  padding: 11px 14px 11px 16px;
  border-radius: 12px;
  border: 1px solid transparent;
  font-size: 0.92rem;
  line-height: 1.3;
  letter-spacing: 0.03em;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.nav-ico {
  color: var(--cl-stone);
  opacity: 0.88;
  transition:
    color 0.18s ease,
    opacity 0.18s ease;
}

.nav-text {
  flex: 1;
  min-width: 0;
}

.aside--collapsed .nav-text {
  display: none;
}

.aside--collapsed .nav-item {
  justify-content: center;
  width: 38px;
  height: 38px;
  margin: 0 auto;
  padding: 0;
  gap: 0;
  border-radius: 11px;
  border-color: rgba(146, 137, 119, 0.22);
  background: rgba(255, 255, 255, 0.38);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82);
}

.aside--collapsed .nav-item.router-link-active::before {
  left: 3px;
  width: 2px;
  height: 16px;
  max-height: 16px;
}

.aside--collapsed .nav-item:hover {
  transform: translateY(-1px);
  border-color: rgba(201, 100, 66, 0.35);
  background: rgba(245, 229, 218, 0.65);
}

.aside--collapsed .nav-item .nav-ico {
  opacity: 0.92;
}

.aside--collapsed .nav-item.router-link-active {
  border-color: rgba(201, 100, 66, 0.42);
  background: rgba(201, 100, 66, 0.14);
  box-shadow:
    rgba(201, 100, 66, 0.18) 0 6px 14px -8px,
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.nav-item:hover {
  color: var(--cl-near-black);
  background: var(--cl-warm-sand);
  box-shadow: var(--cl-warm-sand) 0px 0px 0px 0px, var(--cl-ring-warm) 0px 0px 0px 1px;
  transform: translateX(1px);
}

.nav-item:hover .nav-ico {
  color: var(--cl-terracotta);
  opacity: 1;
}

.nav-item.router-link-active {
  background: rgba(201, 100, 66, 0.11);
  border-color: rgba(201, 100, 66, 0.32);
  color: var(--cl-near-black);
  font-weight: 500;
  box-shadow: rgba(201, 100, 66, 0.08) 0px 2px 12px;
}

.nav-item.router-link-active::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 56%;
  max-height: 28px;
  border-radius: 2px;
  background: var(--cl-terracotta);
}

.nav-item.router-link-active .nav-ico {
  color: var(--cl-terracotta);
  opacity: 1;
}

.nav-item--child {
  padding-left: 14px;
}

.nav-item--child.router-link-active::before {
  left: 4px;
}

.nav-item--root {
  font-weight: 500;
}

.nav-item--root + .nav-group:not(.nav-group--rail) {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed rgba(142, 132, 109, 0.32);
}

/* 无精确悬停且宽度足够：完整侧栏（排除手机窄屏，窄屏用抽屉） */
@media (hover: none) and (min-width: 769px) {
  .shell--collapsed {
    grid-template-columns: 272px 1fr;
  }

  .aside--collapsed {
    padding: 24px 16px 20px;
  }

  .aside--collapsed .brand-title,
  .aside--collapsed .brand-sub,
  .aside--collapsed .nav-label {
    position: static;
    width: auto;
    height: auto;
    margin: revert;
    padding: revert;
    overflow: visible;
    clip: auto;
    white-space: normal;
    border: 0;
  }

  .aside--collapsed .brand {
    display: block;
    align-items: stretch;
    padding-bottom: 20px;
    margin-bottom: 6px;
  }

  .aside--collapsed .brand-accent {
    width: 40px;
    margin-bottom: 14px;
  }

  .aside--collapsed .nav-text {
    display: block;
  }

  .aside--collapsed .nav-item {
    justify-content: flex-start;
    width: auto;
    height: auto;
    margin: 0;
    padding: 11px 14px 11px 16px;
    gap: 12px;
    border-radius: 12px;
    border-color: transparent;
    background: transparent;
    box-shadow: none;
  }

  .aside--collapsed .nav-item.router-link-active::before {
    left: 6px;
    width: 3px;
    height: 56%;
    max-height: 28px;
  }

  .aside--collapsed .nav-item:hover {
    transform: translateX(1px);
    border-color: transparent;
    background: var(--cl-warm-sand);
  }

  .aside--collapsed .nav-item .nav-ico {
    opacity: 0.88;
  }

  .aside--collapsed .nav-item.router-link-active {
    border-color: rgba(201, 100, 66, 0.32);
    background: rgba(201, 100, 66, 0.11);
    box-shadow: rgba(201, 100, 66, 0.08) 0px 2px 12px;
  }

  .aside--collapsed .nav-group__trigger {
    display: flex;
    justify-content: flex-start;
    padding: 11px 14px 11px 16px;
    gap: 12px;
  }

  .aside--collapsed .nav-group__chevron {
    display: block;
  }

  .aside--collapsed .nav-group__children {
    padding-left: 8px;
    margin-left: 18px;
    border-left: 2px solid var(--cl-border-cream);
  }

  .aside--collapsed .nav-group + .nav-group {
    margin-top: 0;
    padding-top: 0;
    border-top: none;
  }

  .aside--collapsed .nav-item--child {
    justify-content: flex-start;
    padding: 11px 14px 11px 14px;
    gap: 12px;
  }

  .aside--collapsed .nav-item--child.router-link-active::before {
    left: 6px;
  }
}

.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 22px;
  border-bottom: 1px solid var(--cl-border-cream);
  background: rgba(250, 249, 245, 0.92);
  backdrop-filter: blur(10px);
}

.crumb {
  font-family: Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif;
  font-weight: 500;
  font-size: 1.15rem;
  line-height: 1.2;
}

.user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.who {
  font-size: 0.75rem;
  color: var(--cl-olive);
}

.role {
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--cl-border-warm);
  color: var(--cl-charcoal);
  font-size: 11px;
  letter-spacing: 0.12px;
}

.btn {
  cursor: pointer;
  border: 1px solid var(--cl-border-warm);
  background: var(--cl-warm-sand);
  color: var(--cl-charcoal);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 500;
  box-shadow: var(--cl-warm-sand) 0px 0px 0px 0px, var(--cl-ring-warm) 0px 0px 0px 1px;
}

.btn:hover {
  background: var(--cl-border-warm);
}

.content {
  padding: 20px 22px 32px;
  padding-left: max(22px, env(safe-area-inset-left, 0px));
  padding-right: max(22px, env(safe-area-inset-right, 0px));
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.nav-backdrop {
  position: fixed;
  inset: 0;
  z-index: 110;
  background: rgba(20, 20, 19, 0.38);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
}

.nav-toggle {
  display: none;
  position: relative;
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  margin: 0;
  padding: 0;
  border: 1px solid var(--cl-border-warm);
  border-radius: 12px;
  background: var(--cl-white);
  box-shadow: var(--cl-ring-warm) 0 0 0 1px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.nav-toggle__bar {
  position: absolute;
  left: 11px;
  right: 11px;
  height: 2px;
  border-radius: 1px;
  background: var(--cl-charcoal);
  pointer-events: none;
}

.nav-toggle__bar:nth-child(1) {
  top: 14px;
}

.nav-toggle__bar:nth-child(2) {
  top: 21px;
}

.nav-toggle__bar:nth-child(3) {
  top: 28px;
}

/* 手机 / 小平板：单栏主区域 + 侧栏抽屉 */
.shell--mobile {
  grid-template-columns: 1fr !important;
}

.shell--mobile .aside {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: min(292px, 88vw);
  max-width: 100%;
  z-index: 120;
  transform: translateX(-102%);
  transition: transform 0.28s cubic-bezier(0.33, 1, 0.68, 1);
  box-shadow: 12px 0 40px rgba(20, 20, 19, 0.14);
  align-self: stretch;
  /* 抽屉内更紧凑，单列入口（工作台、段内导航等）间距更易扫读 */
  padding: 14px 12px 16px;
  padding-top: max(14px, env(safe-area-inset-top, 0px));
}

.shell--mobile .aside.aside--mobile-open {
  transform: translateX(0);
}

.shell--mobile .top {
  padding: 12px 14px;
  padding-top: max(12px, env(safe-area-inset-top));
  padding-left: max(10px, env(safe-area-inset-left));
  padding-right: max(12px, env(safe-area-inset-right));
  gap: 10px;
}

.shell--mobile .nav-toggle {
  display: block;
}

.shell--mobile .crumb {
  flex: 1;
  min-width: 0;
  font-size: 1.05rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shell--mobile .user {
  flex-shrink: 0;
  gap: 6px;
}

.shell--mobile .who {
  display: none;
}

.shell--mobile .btn {
  min-height: 44px;
  padding: 10px 14px;
  font-size: 13px;
  touch-action: manipulation;
}

.shell--mobile .content {
  padding: 14px 14px 28px;
  padding-left: max(14px, env(safe-area-inset-left, 0px));
  padding-right: max(14px, env(safe-area-inset-right, 0px));
  padding-bottom: max(28px, env(safe-area-inset-bottom, 0px));
}

.shell--mobile .brand {
  padding-bottom: 12px;
  margin-bottom: 4px;
}

.shell--mobile .brand-accent {
  margin-bottom: 8px;
}

.shell--mobile .brand-title {
  font-size: 0.95rem;
  line-height: 1.3;
}

.shell--mobile .brand-sub {
  margin-top: 6px;
  font-size: 0.75rem;
  line-height: 1.45;
}

.shell--mobile .nav-label {
  margin: 10px 0 6px 2px;
}

.shell--mobile .nav {
  gap: 2px;
}

.shell--mobile .nav-group {
  gap: 2px;
}

.shell--mobile .nav-group__children {
  gap: 2px;
  padding-left: 6px;
  margin-left: 14px;
}

.shell--mobile .nav-item--root + .nav-group:not(.nav-group--rail) {
  margin-top: 4px;
  padding-top: 6px;
}

.shell--mobile .nav-group--rail + .nav-group--rail,
.shell--mobile .nav-item--root + .nav-group--rail {
  margin-top: 4px;
  padding-top: 6px;
}

.shell--mobile .nav-item {
  min-height: 40px;
  padding: 8px 12px 8px 14px;
  font-size: 0.875rem;
  gap: 10px;
  touch-action: manipulation;
}

.shell--mobile .nav-group__trigger {
  min-height: 40px;
  padding: 8px 12px 8px 14px;
  font-size: 0.875rem;
  gap: 10px;
  touch-action: manipulation;
}

.shell--mobile .nav-item--child {
  min-height: 38px;
  padding: 7px 10px 7px 12px;
  font-size: 0.8125rem;
  gap: 8px;
}

.shell--mobile .nav-item.router-link-active::before {
  max-height: 22px;
}

@media (min-width: 480px) {
  .shell--mobile .who {
    display: inline-block;
    max-width: min(200px, 36vw);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: middle;
  }
}

</style>
