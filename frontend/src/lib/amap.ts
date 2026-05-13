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

/**
 * 浏览器中调起「驾车导航」到指定点（手机端 `callnative=1` 会尝试打开高德地图 App）。
 * 文档：https://lbs.amap.com/api/uri-api/guide/mobile/universal-map
 * 微信内置浏览器等环境可能拦截外链，需提示用户用系统浏览器打开。
 */
export function openAmapNavigationTo(lng: number, lat: number, poiName = '目的地') {
  const q = `https://uri.amap.com/navigation?to=${lng},${lat},${encodeURIComponent(poiName)}&mode=car&coordinate=gaode&callnative=1`
  /**
   * 注意：第三个参数含 `noopener` 时，规范要求 `window.open` 固定返回 `null`，
   * 即使新标签已打开 —— 若据此再执行 `location.href` 会导致当前页也被跳转。
   */
  const opened = window.open(q, '_blank')
  if (opened) {
    try {
      opened.opener = null
    } catch {
      /* 跨域等环境下可能无法赋值 */
    }
    return
  }
  /** 仅当弹窗被拦截时回退为当前页打开 */
  window.location.href = q
}
