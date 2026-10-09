import AMapLoader from '@amap/amap-jsapi-loader'

export { buildAmapNavigationLinks, openAmapNavigationTo } from './amapNavigation'

declare global {
  interface Window {
    _AMapSecurityConfig?: { securityJsCode?: string; serviceHost?: string }
  }
}

/** 须在 AMapLoader.load 之前调用（高德 v2 强制） */
export function configureAmapSecurity(): void {
  const securityJsCode = import.meta.env.VITE_AMAP_SECURITY_JSCODE
  if (!securityJsCode) {
    console.warn('[amap] 未配置 VITE_AMAP_SECURITY_JSCODE，地图可能无法加载')
    return
  }
  window._AMapSecurityConfig = { securityJsCode }
}

/** Web 端 Key 是否已配置（构建时注入，修改后需重启 Vite） */
export function isAmapKeyConfigured(): boolean {
  return Boolean(import.meta.env.VITE_AMAP_KEY?.trim())
}

/** 安全密钥是否已配置（JS API 2.x 强烈建议配置，否则常被拒绝） */
export function isAmapSecurityConfigured(): boolean {
  return Boolean(import.meta.env.VITE_AMAP_SECURITY_JSCODE?.trim())
}

export function getAmapKey(): string {
  const key = import.meta.env.VITE_AMAP_KEY
  if (!key?.trim()) {
    throw new Error('未配置 VITE_AMAP_KEY，请在 frontend/.env.development.local 或 .env.local 中填写高德 Web Key')
  }
  return key.trim()
}

export function loadAmap(plugins: string[] = []) {
  configureAmapSecurity()
  return AMapLoader.load({
    key: getAmapKey(),
    version: '2.0',
    plugins,
  })
}
