import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/home',
      redirect: '/app/dashboard',
    },
    {
      path: '/app',
      component: () => import('@/layouts/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/app/dashboard',
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          meta: { title: '工作台' },
          component: () => import('@/views/app/DashboardView.vue'),
        },
        {
          path: 'location-navigation',
          name: 'locationNavigation',
          meta: { title: '段内导航' },
          component: () => import('@/views/app/LocationNavigationView.vue'),
        },
        {
          path: 'occupancy-query',
          name: 'occupancyQuery',
          meta: { title: '车辆调度' },
          component: () => import('@/views/app/OccupancyQueryView.vue'),
        },
        {
          path: 'vehicles',
          name: 'vehicles',
          meta: { title: '车辆管理' },
          component: () => import('@/views/app/VehiclesView.vue'),
        },
        {
          path: 'drivers',
          name: 'drivers',
          meta: { title: '驾驶员管理' },
          component: () => import('@/views/app/DriversView.vue'),
        },
        {
          path: 'accounts',
          name: 'accounts',
          meta: { title: '账户管理' },
          component: () => import('@/views/app/AccountsView.vue'),
        },
        {
          path: 'trips',
          name: 'trips',
          meta: { title: '用车申请' },
          component: () => import('@/views/app/TripsView.vue'),
        },
        {
          path: 'tracking',
          name: 'tracking',
          meta: { title: '定位管理' },
          component: () => import('@/views/app/TrackingView.vue'),
        },
        {
          path: 'approvals',
          name: 'approvals',
          meta: { title: '审批流转' },
          component: () => import('@/views/app/ApprovalsView.vue'),
        },
        {
          path: 'fuel-records',
          name: 'fuelRecords',
          meta: { title: '加油记录' },
          component: () => import('@/views/app/FuelRecordsView.vue'),
        },
        {
          path: 'repair-records',
          name: 'repairRecords',
          meta: { title: '维修记录' },
          component: () => import('@/views/app/RepairRecordsView.vue'),
        },
        {
          path: 'maintenance',
          name: 'maintenance',
          meta: { title: '维修保养' },
          component: () => import('@/views/app/MaintenanceView.vue'),
        },
        {
          path: 'fuel',
          name: 'fuel',
          meta: { title: '油卡余额' },
          component: () => import('@/views/app/FuelView.vue'),
        },
        {
          path: 'fuel-bills',
          name: 'fuelBills',
          meta: { title: '油卡账单' },
          component: () => import('@/views/app/FuelBillsView.vue'),
        },
        {
          path: 'insurance',
          name: 'insurance',
          meta: { title: '保险动态' },
          component: () => import('@/views/app/InsuranceDynamicsView.vue'),
        },
        {
          path: 'inspection',
          name: 'inspection',
          meta: { title: '检车动态' },
          component: () => import('@/views/app/InspectionDynamicsView.vue'),
        },
        {
          path: 'access',
          name: 'access',
          meta: { title: '通行动态' },
          component: () => import('@/views/app/AccessDynamicsView.vue'),
        },
        {
          path: 'reports',
          name: 'reports',
          meta: { title: '数据管理' },
          component: () => import('@/views/app/ReportsView.vue'),
        },
        {
          path: 'data-vehicle-export',
          name: 'dataVehicleExport',
          meta: { title: '车辆档案导出' },
          component: () => import('@/views/app/DataVehicleExportView.vue'),
        },
        {
          path: 'data-driver-export',
          name: 'dataDriverExport',
          meta: { title: '驾驶员档案导出' },
          component: () => import('@/views/app/DataDriverExportView.vue'),
        },
        {
          path: 'data-maintenance-terms',
          name: 'dataMaintenanceTerms',
          meta: { title: '维修词条管理' },
          component: () => import('@/views/app/DataMaintenanceTermsView.vue'),
        },
        {
          path: 'data-vehicle-usage-analysis',
          name: 'dataVehicleUsageAnalysis',
          meta: { title: '车辆使用分析' },
          component: () => import('@/views/app/DataVehicleUsageAnalysisView.vue'),
        },
        {
          path: 'data-fuel-consumption-analysis',
          name: 'dataFuelConsumptionAnalysis',
          meta: { title: '燃油消耗分析' },
          component: () => import('@/views/app/DataFuelConsumptionAnalysisView.vue'),
        },
        {
          path: 'data-maintenance-analysis',
          name: 'dataMaintenanceAnalysis',
          meta: { title: '维修数据分析' },
          component: () => import('@/views/app/DataMaintenanceAnalysisView.vue'),
        },
        {
          path: 'ai-data-analysis',
          name: 'aiDataAnalysis',
          meta: { title: 'AI数据分析' },
          component: () => import('@/views/app/AiDataAnalysisView.vue'),
        },
        {
          path: 'ai-data-learning',
          name: 'aiDataLearning',
          meta: { title: 'AI数据学习' },
          component: () => import('@/views/app/AiDataLearningView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  if (!to.matched.some((r) => Boolean(r.meta.requiresAuth))) return true
  const store = useUserStore()
  if (!store.token) return { name: 'login', query: { redirect: to.fullPath } }
  if (!store.profile) {
    try {
      await store.fetchMe()
    } catch {
      store.logout()
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

export default router
