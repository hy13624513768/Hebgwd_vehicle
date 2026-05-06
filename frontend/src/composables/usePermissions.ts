import { computed } from 'vue'

import { useUserStore } from '@/stores/user'

/** 与后端 app.core.roles / RBAC 对齐（含旧版兼容） */
const FLEET_MANAGEMENT_ROLES = new Set([
  'super_admin',
  'section_admin',
  'workshop_director',
  'workshop_admin',
  'admin',
  'fleet_manager',
])

const ACCOUNT_ADMIN_ROLES = new Set([
  'super_admin',
  'section_admin',
  'admin',
  'fleet_manager',
])

export function usePermissions() {
  const user = useUserStore()

  const role = computed(() => user.profile?.role || 'vehicle_driver')

  const isAdmin = computed(() => role.value === 'admin' || role.value === 'super_admin')
  const isFleetManager = computed(() => role.value === 'fleet_manager' || role.value === 'section_admin')
  const isDriver = computed(() => role.value === 'driver' || role.value === 'vehicle_driver')
  const isStaff = computed(() => role.value === 'staff')

  const canManageFleet = computed(() => FLEET_MANAGEMENT_ROLES.has(role.value))
  const canExportReports = computed(() => FLEET_MANAGEMENT_ROLES.has(role.value))
  const canManageAccounts = computed(() => ACCOUNT_ADMIN_ROLES.has(role.value))

  return {
    role,
    isAdmin,
    isFleetManager,
    isDriver,
    isStaff,
    canManageFleet,
    canExportReports,
    canManageAccounts,
  }
}
