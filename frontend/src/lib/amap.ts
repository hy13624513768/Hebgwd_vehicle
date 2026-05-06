import AMapLoader from '@amap/amap-jsapi-loader'

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

export function getAmapKey(): string {
  const key = import.meta.env.VITE_AMAP_KEY
  if (!key) {
    throw new Error('未配置 VITE_AMAP_KEY，请在 frontend/.env.local 中填写高德 Web Key')
  }
  return key
}

export function loadAmap(plugins: string[] = []) {
  configureAmapSecurity()
  return AMapLoader.load({
    key: getAmapKey(),
    version: '2.0',
    plugins,
  })
}

/**
 * 浏览器中调起「驾车导航」到指定点（手机端 `callnative=1` 会尝试打开高德地图 App）。
 * 文档：https://lbs.amap.com/api/uri-api/guide/mobile/universal-map
 * 微信内置浏览器等环境可能拦截外链，需提示用户用系统浏览器打开。
 */
export function openAmapNavigationTo(lng: number, lat: number, poiName = '目的地') {
  const q = `https://uri.amap.com/navigation?to=${lng},${lat},${encodeURIComponent(poiName)}&mode=car&coordinate=gaode&callnative=1`
  const ua = typeof navigator !== 'undefined' ? navigator.userAgent : ''
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)
  if (isMobile) {
    window.location.href = q
  } else {
    window.open(q, '_blank', 'noopener,noreferrer')
  }
}
