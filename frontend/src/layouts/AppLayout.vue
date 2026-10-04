<template>
  <div
    class="shell"
    :class="{
      'shell--collapsed': !sidebarExpanded && !isMobileShell,
      'shell--mobile': isMobileShell,
      'shell--flyout-open': Boolean(flyoutOpenId) && navIconsOnly,
    }"
  >
    <Transition name="nav-backdrop">
      <div
        v-if="isMobileShell && mobileNavOpen"
        class="nav-backdrop"
        aria-hidden="true"
        @click="mobileNavOpen = false"
      />
    </Transition>
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
        <div class="brand-mark">
          <img src="@/assets/harbin-railway-logo.jpg" alt="哈尔滨工务段标志" />
        </div>
        <div class="brand-copy">
          <div class="brand-title">汽车管理信息系统</div>
          <div class="brand-sub">哈尔滨工务段 · 业务工作台</div>
        </div>
        <button
          v-if="isMobileShell"
          type="button"
          class="aside-close"
          aria-label="关闭导航菜单"
          @click="mobileNavOpen = false"
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>

      <p class="nav-label">功能导航</p>
      <nav
        ref="navElement"
        class="nav"
        aria-label="功能导航"
        @pointerover="prefetchRouteFromEvent"
        @focusin="prefetchRouteFromEvent"
      >
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
                :class="{ 'nav-group__trigger--current': isGroupChildActive(piece) }"
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

      <div v-if="user.profile" class="aside-profile">
        <div class="aside-profile__avatar" aria-hidden="true">
          {{ user.profile.display_name.trim().slice(0, 1) || '用' }}
        </div>
        <div class="aside-profile__copy">
          <strong>{{ user.profile.display_name }}</strong>
          <span>{{ roleLabel(user.profile.role) }}</span>
        </div>
        <span class="aside-profile__status" title="已登录" aria-label="已登录" />
      </div>
    </aside>

    <section class="main">
      <header class="top">
        <button
          v-if="isMobileShell"
          type="button"
          class="nav-toggle"
          :aria-label="mobileNavOpen ? '关闭导航菜单' : '打开导航菜单'"
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
        @pointerover="prefetchRouteFromEvent"
        @focusin="prefetchRouteFromEvent"
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { loadRouteLocation, useRoute, useRouter } from 'vue-router'

import NavIcon, { type NavIconName } from '@/components/NavIcon.vue'
import { usePermissions } from '@/composables/usePermissions'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const perm = usePermissions()
const prefetchedRoutes = new Set<string>()

function prefetchRouteFromEvent(event: PointerEvent | FocusEvent) {
  const target = event.target
  if (!(target instanceof Element)) return
  const link = target.closest<HTMLAnchorElement>('a[href]')
  if (!link) return

  const targetRoute = router.resolve(link.getAttribute('href') || '')
  if (targetRoute.matched.length === 0 || targetRoute.fullPath === route.fullPath) return
  if (prefetchedRoutes.has(targetRoute.fullPath)) return

  prefetchedRoutes.add(targetRoute.fullPath)
  void loadRouteLocation(targetRoute).catch(() => {
    prefetchedRoutes.delete(targetRoute.fullPath)
  })
}

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
  { to: '/app/ai-analysis', label: 'AI分析', icon: 'aiAnalysis', need: 'reports' },
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

const navElement = ref<HTMLElement | null>(null)

async function toggleGroup(id: string) {
  const nav = navElement.value
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const blocks = nav ? Array.from(nav.children) as HTMLElement[] : []
  const before = new Map(blocks.map((element) => [element, element.getBoundingClientRect()]))
  const willOpen = !groupOpen[id]

  groupOpen[id] = willOpen
  await nextTick()

  if (!nav || reduceMotion) return

  // FLIP：菜单项只在合成层移动，避免 max-height 动画在每一帧重排整条侧栏。
  for (const element of blocks) {
    const previous = before.get(element)
    if (!previous) continue
    const current = element.getBoundingClientRect()
    const deltaY = previous.top - current.top
    if (Math.abs(deltaY) < 0.5) continue
    element.getAnimations().forEach((animation) => animation.cancel())
    element.animate(
      [
        { transform: `translate3d(0, ${deltaY}px, 0)` },
        { transform: 'translate3d(0, 0, 0)' },
      ],
      { duration: 220, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' },
    )
  }

  if (willOpen) {
    const panel = document.getElementById(`nav-group-${id}-panel`)
    panel?.animate(
      [
        { opacity: 0, transform: 'translate3d(0, -6px, 0)' },
        { opacity: 1, transform: 'translate3d(0, 0, 0)' },
      ],
      { duration: 180, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' },
    )
  }
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

/* 侧栏视觉重构：深色导航面板，强化品牌、分组和当前项层级。 */
.aside {
  --aside-text: #eee9de;
  --aside-muted: #aaa99f;
  --aside-line: rgba(255, 255, 255, 0.09);
  --aside-hover: rgba(255, 255, 255, 0.07);
  --aside-active: #f4eadf;
  --aside-accent: #de7552;

  border-right-color: rgba(22, 25, 22, 0.72);
  background:
    radial-gradient(circle at 12% 4%, rgba(222, 117, 82, 0.14), transparent 25%),
    linear-gradient(180deg, #292d29 0%, #222521 58%, #1d201d 100%);
  box-shadow:
    12px 0 32px rgba(24, 27, 23, 0.09),
    inset -1px 0 rgba(255, 255, 255, 0.035);
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.aside::-webkit-scrollbar-thumb,
.aside--collapsed::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.18);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding-bottom: 18px;
  border-bottom-color: var(--aside-line);
}

.brand-mark {
  display: grid;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  place-items: center;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 13px;
  background: #fff;
  box-shadow:
    0 8px 20px rgba(0, 0, 0, 0.22),
    inset 0 1px rgba(255, 255, 255, 0.28);
}

.brand-mark img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.brand-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  opacity: 1;
  transition: opacity 0.12s ease 0.1s;
}

.brand-title {
  overflow: hidden;
  color: #fffaf1;
  font-family: inherit;
  font-size: 0.96rem;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: 0.01em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.brand-sub {
  overflow: hidden;
  margin-top: 4px;
  color: var(--aside-muted);
  font-size: 0.7rem;
  line-height: 1.4;
  letter-spacing: 0.04em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-label {
  margin: 14px 0 7px 6px;
  color: #8f9189;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.2em;
}

.nav-group__trigger,
.nav-item {
  min-height: 41px;
  padding-top: 9px;
  padding-bottom: 9px;
  border-radius: 11px;
  color: var(--aside-text);
  font-size: 0.9rem;
  font-weight: 520;
  line-height: 1.35;
  letter-spacing: 0;
}

.nav {
  flex: 0 0 auto;
  min-height: auto;
  gap: 2px;
  margin-bottom: 14px;
}

.nav-group {
  gap: 2px;
}

.nav-text {
  overflow: hidden;
  opacity: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: opacity 0.12s ease 0.1s;
}

.nav-group__trigger:hover,
.nav-item:hover {
  border-color: rgba(255, 255, 255, 0.08);
  background: var(--aside-hover);
  color: #fff;
  box-shadow: none;
  transform: translateX(2px);
}

.nav-group__trigger--current {
  color: #fff;
  background: rgba(222, 117, 82, 0.08);
}

.nav-ico,
.nav-group__trigger .nav-ico {
  color: #aeb0a8;
  opacity: 0.88;
}

.nav-group__trigger:hover .nav-ico,
.nav-group__trigger--current .nav-ico,
.nav-item:hover .nav-ico {
  color: #f19a76;
}

.nav-group__chevron {
  color: #a4a69e;
  opacity: 0.8;
}

.nav-group__children {
  gap: 1px;
  margin: 2px 0 4px 20px;
  padding-left: 9px;
  border-left: 1px solid rgba(255, 255, 255, 0.12);
}

.nav-item--child {
  min-height: 40px;
  padding: 9px 11px;
  color: #c8c8c0;
  font-size: 0.85rem;
  font-weight: 480;
  line-height: 1.35;
}

.nav-item.router-link-active {
  border-color: rgba(255, 255, 255, 0.12);
  background: var(--aside-active);
  color: #292722;
  font-weight: 700;
  box-shadow: 0 8px 22px rgba(8, 10, 8, 0.2);
}

.nav-item.router-link-active::before {
  left: 5px;
  width: 3px;
  background: var(--aside-accent);
}

.nav-item.router-link-active .nav-ico {
  color: #bb5638;
}

.nav-item--root + .nav-group:not(.nav-group--rail),
.nav-group--rail + .nav-group--rail,
.nav-item--root + .nav-group--rail {
  margin-top: 4px;
  padding-top: 5px;
  border-top-color: var(--aside-line);
}

.aside-profile {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
  margin-top: auto;
  padding: 12px 10px 2px;
  border-top: 1px solid var(--aside-line);
  color: var(--aside-text);
}

.aside-profile__avatar {
  display: grid;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  color: #f4c3af;
  font-size: 0.8rem;
  font-weight: 700;
}

.aside-profile__copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
  opacity: 1;
  transition: opacity 0.12s ease 0.1s;
}

.aside-profile__copy strong {
  overflow: hidden;
  color: #f5f0e7;
  font-size: 0.75rem;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aside-profile__copy span {
  color: #969990;
  font-size: 0.65rem;
}

.aside-profile__status {
  width: 7px;
  height: 7px;
  border: 2px solid #2b302b;
  border-radius: 50%;
  background: #77b887;
  box-shadow: 0 0 0 2px rgba(119, 184, 135, 0.12);
}

.aside--collapsed .brand {
  padding-bottom: 12px;
}

.aside--collapsed .aside-profile__status {
  display: none;
}

.aside--collapsed .brand-copy,
.aside--collapsed .aside-profile__copy {
  display: flex;
  flex: 0 0 0;
  max-width: 0;
  opacity: 0;
  pointer-events: none;
  transition-delay: 0s;
}

.aside--collapsed .nav-text {
  display: block;
  flex: 0 0 0;
  max-width: 0;
  opacity: 0;
  pointer-events: none;
  transition-delay: 0s;
}

.aside--collapsed .brand-mark {
  flex-basis: 38px;
  width: 38px;
  height: 38px;
  border-radius: 11px;
}

.aside--collapsed .nav-item {
  border-color: rgba(255, 255, 255, 0.09);
  background: rgba(255, 255, 255, 0.035);
  box-shadow: none;
}

.aside--collapsed .nav-item:hover {
  border-color: rgba(222, 117, 82, 0.35);
  background: rgba(222, 117, 82, 0.12);
}

.aside--collapsed .nav-item.router-link-active {
  border-color: rgba(244, 234, 223, 0.7);
  background: var(--aside-active);
  box-shadow: 0 7px 18px rgba(8, 10, 8, 0.24);
}

.aside--collapsed .aside-profile {
  justify-content: center;
  padding: 12px 0 0;
}

.nav-flyout {
  border-color: rgba(58, 54, 47, 0.16);
  background: #fffdf8;
  box-shadow: 0 18px 46px rgba(20, 20, 19, 0.18);
}

@media (hover: none) and (min-width: 769px) {
  .aside--collapsed .brand-copy,
  .aside--collapsed .aside-profile__copy {
    display: flex;
    flex: 1;
    max-width: none;
    opacity: 1;
    pointer-events: auto;
  }

  .aside--collapsed .aside-profile__status {
    display: block;
  }

  .aside--collapsed .nav-text {
    display: block;
    flex: 1;
    max-width: none;
    opacity: 1;
    pointer-events: auto;
  }

  .aside--collapsed .brand {
    display: flex;
    flex-direction: row;
    align-items: center;
  }

  .aside--collapsed .nav-item {
    border-color: transparent;
    background: transparent;
  }

  .aside--collapsed .nav-item.router-link-active {
    border-color: rgba(255, 255, 255, 0.12);
    background: var(--aside-active);
  }

  .aside--collapsed .aside-profile {
    justify-content: flex-start;
    padding: 12px 10px 2px;
  }
}

.shell--mobile .aside {
  width: min(304px, 88vw);
  box-shadow: 18px 0 48px rgba(8, 10, 8, 0.28);
}

.shell--mobile .brand {
  padding: 2px 2px 14px;
}

.shell--mobile .brand-mark {
  flex-basis: 40px;
  width: 40px;
  height: 40px;
}

.shell--mobile .brand-title {
  color: #fffaf1;
  font-size: 0.9rem;
}

.shell--mobile .brand-sub {
  margin-top: 3px;
  color: var(--aside-muted);
  font-size: 0.67rem;
}

.shell--mobile .nav-item,
.shell--mobile .nav-group__trigger {
  min-height: 42px;
}

.shell--mobile .nav-item--child {
  min-height: 38px;
}

/* Mobile application shell: floating drawer, tactile controls and compact rhythm. */
.aside-close {
  display: none;
}

.nav-backdrop-enter-active,
.nav-backdrop-leave-active {
  transition: opacity 0.22s linear;
}

.nav-backdrop-enter-from,
.nav-backdrop-leave-to {
  opacity: 0;
}

.nav-group__children {
  contain: layout paint;
}

.shell--mobile {
  background:
    radial-gradient(circle at 100% 0, rgba(205, 103, 68, 0.08), transparent 38%),
    var(--cl-parchment);
}

.shell--mobile .nav-backdrop {
  background: rgba(13, 16, 14, 0.56);
  will-change: opacity;
}

.shell--mobile .aside {
  top: max(10px, env(safe-area-inset-top, 0px));
  right: auto;
  bottom: max(10px, env(safe-area-inset-bottom, 0px));
  left: 10px;
  width: min(318px, calc(100vw - 24px));
  height: auto;
  overflow: hidden;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 26px;
  opacity: 0;
  transform: perspective(1100px) translate3d(calc(-100% - 24px), 0, 0) rotateY(-17deg)
    scale(0.985);
  transform-origin: left center;
  backface-visibility: hidden;
  will-change: transform, opacity;
  contain: layout paint style;
  box-shadow:
    0 24px 64px rgba(7, 10, 8, 0.32),
    inset 7px 0 0 rgba(10, 13, 11, 0.34),
    inset 9px 0 0 rgba(255, 255, 255, 0.035),
    inset 0 1px rgba(255, 255, 255, 0.06);
  transition:
    transform 0.34s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.16s linear;
}

.shell--mobile .aside.aside--mobile-open {
  opacity: 1;
  transform: perspective(1100px) translate3d(0, 0, 0) rotateY(0deg) scale(1);
  box-shadow:
    0 30px 78px rgba(7, 10, 8, 0.44),
    inset 7px 0 0 rgba(10, 13, 11, 0.34),
    inset 9px 0 0 rgba(255, 255, 255, 0.035),
    inset 0 1px rgba(255, 255, 255, 0.08);
}

/* 书页掀开的光带：只改变透明度，避免动画阴影和滤镜造成重绘。 */
.shell--mobile .aside::after {
  position: absolute;
  inset: 0;
  z-index: 4;
  border-radius: inherit;
  background: linear-gradient(
    96deg,
    rgba(255, 255, 255, 0.16) 0%,
    rgba(255, 255, 255, 0.04) 13%,
    transparent 36%
  );
  content: '';
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease 0.08s;
}

.shell--mobile .aside.aside--mobile-open::after {
  opacity: 0.42;
}

.shell--mobile .brand {
  flex: 0 0 auto;
  gap: 9px;
  margin-bottom: 2px;
  padding: 1px 2px 9px;
  border-bottom-color: rgba(255, 255, 255, 0.09);
}

.shell--mobile .brand-mark {
  flex-basis: 38px;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  box-shadow: 0 7px 20px rgba(7, 10, 8, 0.2);
}

.shell--mobile .brand-title {
  font-size: 0.86rem;
  letter-spacing: 0.01em;
}

.shell--mobile .brand-sub {
  margin-top: 2px;
  font-size: 0.64rem;
}

.shell--mobile .aside-close {
  display: grid;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  margin-left: auto;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 11px;
  color: rgba(255, 255, 255, 0.78);
  background: rgba(255, 255, 255, 0.065);
  font: inherit;
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease;
}

.shell--mobile .aside-close:active {
  background: rgba(255, 255, 255, 0.12);
  transform: scale(0.92);
}

.shell--mobile .nav {
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  gap: 1px;
  margin: 0 0 5px;
  padding: 2px 2px 3px 0;
  overscroll-behavior: contain;
  scrollbar-width: thin;
}

.shell--mobile .nav-label {
  margin: 0;
  padding: 5px 10px 3px;
  font-size: 0.61rem;
  letter-spacing: 0.12em;
}

.shell--mobile .nav-item,
.shell--mobile .nav-group__trigger {
  min-height: 39px;
  padding: 7px 10px;
  border-radius: 12px;
  font-size: 0.82rem;
  gap: 9px;
  transition:
    color 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.shell--mobile .nav-item--child {
  min-height: 36px;
  margin: 1px 3px;
  padding: 6px 9px;
  border-radius: 10px;
  font-size: 0.77rem;
}

.shell--mobile .nav-item:active,
.shell--mobile .nav-group__trigger:active {
  transform: scale(0.975);
}

.shell--mobile .nav-group__children {
  gap: 1px;
  margin: 2px 0 3px;
  padding: 2px;
  border-left: 0;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.025);
}

.shell--mobile .nav-group__chevron {
  display: grid;
  width: 21px;
  height: 21px;
  place-items: center;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.055);
  transition: transform 0.24s cubic-bezier(0.22, 1, 0.36, 1), background 0.18s ease;
}

.shell--mobile .nav-group--open > .nav-group__trigger .nav-group__chevron {
  background: rgba(222, 117, 82, 0.15);
}

.shell--mobile .aside-profile {
  flex: 0 0 auto;
  min-height: 46px;
  margin-top: 0;
  padding: 6px 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 13px;
  background: rgba(31, 36, 32, 0.92);
  box-shadow: 0 -10px 24px rgba(20, 24, 21, 0.22);
}

.shell--mobile .aside-profile__avatar {
  flex-basis: 30px;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  font-size: 0.72rem;
}

.shell--mobile .aside-profile__copy {
  gap: 1px;
}

.shell--mobile .aside-profile__copy strong {
  font-size: 0.76rem;
}

.shell--mobile .aside-profile__copy span {
  font-size: 0.62rem;
}

.shell--mobile .nav-item--root + .nav-group:not(.nav-group--rail),
.shell--mobile .nav-group--rail + .nav-group--rail,
.shell--mobile .nav-item--root + .nav-group--rail {
  margin-top: 2px;
  padding-top: 2px;
}

.shell--mobile .main {
  background:
    radial-gradient(circle at 100% 0, rgba(205, 103, 68, 0.07), transparent 34%),
    var(--cl-parchment);
}

.shell--mobile .top {
  min-height: 50px;
  margin: 5px 10px 0;
  padding: 5px 8px;
  border: 1px solid rgba(58, 54, 47, 0.09);
  border-radius: 15px;
  background: rgba(255, 253, 248, 0.88);
  box-shadow: 0 8px 28px rgba(53, 45, 37, 0.08);
  backdrop-filter: blur(18px) saturate(1.08);
  -webkit-backdrop-filter: blur(18px) saturate(1.08);
}

.shell--mobile .nav-toggle {
  width: 38px;
  height: 38px;
  border-color: rgba(58, 54, 47, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 4px 14px rgba(53, 45, 37, 0.08);
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.shell--mobile .nav-toggle:active {
  background: #fff;
  box-shadow: 0 2px 8px rgba(53, 45, 37, 0.08);
  transform: scale(0.94);
}

.shell--mobile .nav-toggle__bar {
  transition: top 0.22s ease, opacity 0.16s ease, transform 0.22s ease;
}

.shell--mobile .nav-toggle__bar:nth-child(1) {
  top: 12px;
}

.shell--mobile .nav-toggle__bar:nth-child(2) {
  top: 18px;
}

.shell--mobile .nav-toggle__bar:nth-child(3) {
  top: 24px;
}

.shell--mobile .nav-toggle[aria-expanded='true'] .nav-toggle__bar:nth-child(1) {
  top: 18px;
  transform: rotate(45deg);
}

.shell--mobile .nav-toggle[aria-expanded='true'] .nav-toggle__bar:nth-child(2) {
  opacity: 0;
  transform: scaleX(0.4);
}

.shell--mobile .nav-toggle[aria-expanded='true'] .nav-toggle__bar:nth-child(3) {
  top: 18px;
  transform: rotate(-45deg);
}

.shell--mobile .title {
  font-size: 0.95rem;
  letter-spacing: 0.01em;
}

.shell--mobile .top .btn {
  min-height: 36px;
  padding: 0 11px;
  border-radius: 11px;
}

.shell--mobile .content {
  padding: 8px 12px max(14px, env(safe-area-inset-bottom, 0px));
}

.shell--mobile .content :deep(button),
.shell--mobile .content :deep(a) {
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

.shell--mobile .content :deep(button:not(:disabled)) {
  transition-property: transform, color, background-color, border-color, box-shadow;
  transition-duration: 0.18s;
}

.shell--mobile .content :deep(button:not(:disabled):active) {
  transform: scale(0.97);
}

.shell--mobile .content :deep(.primary),
.shell--mobile .content :deep(.ghost) {
  min-height: 40px;
  border-radius: 12px;
}

@media (min-width: 480px) and (max-width: 719px) {
  .shell--mobile .who {
    display: none;
  }
}

/* 避免 iOS/部分移动浏览器聚焦小字号表单时自动放大页面。 */
@media (max-width: 768px) {
  .shell--mobile .content :deep(input),
  .shell--mobile .content :deep(textarea),
  .shell--mobile .content :deep(select) {
    font-size: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .shell--mobile .aside,
  .shell--mobile .aside::after,
  .shell--mobile .nav-backdrop,
  .shell--mobile .nav > * {
    animation: none !important;
    transition-duration: 0.01ms !important;
  }
}

</style>
