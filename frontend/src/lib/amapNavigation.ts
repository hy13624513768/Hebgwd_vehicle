/** https://lbs.amap.com/api/amap-mobile/guide/harmony-os/route-next */
export function isHarmonyOS(userAgent: string): boolean {
  // Some compatibility UAs hide the OS name but retain the ArkWeb engine.
  // AMap's own callnativeOs module uses ArkWeb to recognize Harmony browsers.
  return /OpenHarmony|HarmonyOS|Harmony[ /]OS|ArkWeb\//i.test(userAgent)
}

export interface NavigationOrigin {
  lng: number
  lat: number
}

export function buildAmapNavigationLinks(lng: number, lat: number, poiName = '目的地', origin?: NavigationOrigin) {
  const name = encodeURIComponent(poiName)
  const web = `https://uri.amap.com/navigation?to=${lng},${lat},${name}&mode=car&coordinate=gaode`
  // Use the exact route used by AMap's H5 callnativeSchemas module (no trailing
  // slash). An app-to-app startAbility example does not prove browser support.
  const harmony = origin
    ? `amapuri://route/plan?sourceApplication=Hebgwd_vehicle&slon=${origin.lng}&slat=${origin.lat}&sname=${encodeURIComponent('我的位置')}&dlon=${lng}&dlat=${lat}&dname=${name}&t=0&dev=0`
    : undefined
  return {
    // A web fallback must not trigger AMap's failed-launch/download chain.
    web: `${web}&callnative=0`,
    nativeWeb: `${web}&callnative=1`,
    harmony,
    // AMap's callByAppLink uses /applink/?schema=<encoded full app URI>.
    // m.amap.com publishes .well-known/applinking.json for HarmonyOS.
    harmonyAppLink: harmony ? `https://m.amap.com/applink/?schema=${encodeURIComponent(harmony)}` : undefined,
  }
}

/** AMap's H5 callBySchema uses an iframe for non-iOS browsers. No download fallback. */
export function launchAmapScheme(uri: string): void {
  let frame = document.getElementById('heb-amap-launch') as HTMLIFrameElement | null
  if (!frame) {
    frame = document.createElement('iframe')
    frame.id = 'heb-amap-launch'
    frame.hidden = true
    frame.title = '打开高德地图'
    document.body.appendChild(frame)
  }
  frame.src = uri
}

export function disposeAmapSchemeLauncher(): void {
  document.getElementById('heb-amap-launch')?.remove()
}

/** Must run synchronously in the click handler to retain user activation. */
export function openAmapNavigationTo(lng: number, lat: number, poiName = '目的地', origin?: NavigationOrigin) {
  const links = buildAmapNavigationLinks(lng, lat, poiName, origin)
  const harmonyOS = isHarmonyOS(navigator.userAgent)
  if (harmonyOS && links.harmonyAppLink) {
    window.location.href = links.harmonyAppLink
    return
  }

  // Retain the existing iOS/Android/desktop web entry and popup fallback.
  const url = harmonyOS ? links.web : links.nativeWeb
  const opened = window.open(url, '_blank')
  if (opened) {
    try {
      opened.opener = null
    } catch {
      /* Some cross-origin contexts disallow assigning opener. */
    }
    return
  }
  window.location.href = url
}
