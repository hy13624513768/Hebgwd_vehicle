import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { ref, computed } from 'vue'

const source = readFileSync(new URL('../src/lib/amapNavigation.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
})
const { buildAmapNavigationLinks, disposeAmapSchemeLauncher, isHarmonyOS, launchAmapScheme, openAmapNavigationTo } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`
)

test('recognizes HarmonyOS before Android compatibility identifiers', () => {
  for (const ua of [
    'Mozilla/5.0 (Phone; OpenHarmony 5.0) ArkWeb/4.1',
    'Mozilla/5.0 (Linux; Android 12; HarmonyOS 5.0)',
    'Mozilla/5.0 (Tablet; Harmony OS 6.0)',
    'Mozilla/5.0 (Linux; Android 12; Mobile) ArkWeb/4.1.6.1',
  ]) assert.equal(isHarmonyOS(ua), true)
  for (const ua of ['iPhone OS 18', 'Linux; Android 14; HUAWEI', 'Windows NT 10.0']) {
    assert.equal(isHarmonyOS(ua), false)
  }
})

test('keeps destination coordinates and safely encodes Chinese names and URL delimiters', () => {
  const name = '哈车间 & 北门#1?入口=东'
  const links = buildAmapNavigationLinks(126.57466, 45.706031, name, { lng: 126.5, lat: 45.7 })
  const harmony = new URL(links.harmony)
  assert.equal(harmony.protocol, 'amapuri:')
  assert.equal(harmony.hostname, 'route')
  assert.equal(harmony.pathname, '/plan')
  assert.equal(harmony.searchParams.get('slon'), '126.5')
  assert.equal(harmony.searchParams.get('slat'), '45.7')
  assert.equal(harmony.searchParams.get('sname'), '我的位置')
  assert.equal(harmony.searchParams.get('dlon'), '126.57466')
  assert.equal(harmony.searchParams.get('dlat'), '45.706031')
  assert.equal(harmony.searchParams.get('dname'), name)
  assert.equal(harmony.searchParams.get('t'), '0')
  assert.equal(harmony.searchParams.get('dev'), '0')
  assert.equal(harmony.searchParams.get('sourceApplication'), 'Hebgwd_vehicle')
  const web = new URL(links.web)
  assert.equal(web.searchParams.get('to'), `126.57466,45.706031,${name}`)
  assert.equal(web.searchParams.get('callnative'), '0')
  assert.equal(web.searchParams.get('coordinate'), 'gaode')
  const appLink = new URL(links.harmonyAppLink)
  assert.equal(appLink.origin, 'https://m.amap.com')
  assert.equal(appLink.pathname, '/applink/')
  assert.equal(appLink.searchParams.get('schema'), links.harmony)
  assert.equal(new URL(links.nativeWeb).searchParams.get('callnative'), '1')
})

function withBrowser(userAgent, opened, callback) {
  const originals = new Map(['window', 'navigator'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]))
  const calls = []
  const fakeWindow = { location: { href: '' }, open: (...args) => { calls.push(args); return opened } }
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { userAgent } })
  Object.defineProperty(globalThis, 'window', { configurable: true, value: fakeWindow })
  try { callback(fakeWindow, calls) } finally {
    for (const [key, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor)
      else delete globalThis[key]
    }
  }
}

test('Harmony opens the official HTTPS app link synchronously without opening a new tab', () => {
  withBrowser('Phone; OpenHarmony 5.0', null, (window, calls) => {
    openAmapNavigationTo(126, 45, '北门', { lng: 125, lat: 44 })
    assert.equal(window.location.href, buildAmapNavigationLinks(126, 45, '北门', { lng: 125, lat: 44 }).harmonyAppLink)
    assert.deepEqual(calls, [])
  })
})

for (const ua of ['iPhone OS 18', 'Linux; Android 14', 'Windows NT 10.0']) {
  test(`${ua}: preserves web entry without redirecting the original page`, () => {
    const tab = { opener: {} }
    withBrowser(ua, tab, (window, calls) => {
      openAmapNavigationTo(126, 45)
      assert.deepEqual(calls, [[buildAmapNavigationLinks(126, 45).nativeWeb, '_blank']])
      assert.equal(tab.opener, null)
      assert.equal(window.location.href, '')
    })
  })
}

test('blocked web popup falls back to the current page', () => {
  withBrowser('iPhone OS 18', null, window => {
    openAmapNavigationTo(126, 45)
    assert.equal(window.location.href, buildAmapNavigationLinks(126, 45).nativeWeb)
  })
})

test('opener assignment failure does not open a duplicate page', () => {
  const tab = Object.defineProperty({}, 'opener', { set() { throw new Error('Cross origin') } })
  withBrowser('iPhone OS 18', tab, window => {
    openAmapNavigationTo(126, 45)
    assert.equal(window.location.href, '')
  })
})


test('without a real origin, Harmony uses the web fallback instead of a malformed app route', () => {
  assert.equal(buildAmapNavigationLinks(126, 45).harmony, undefined)
  withBrowser('Phone; OpenHarmony 5.0', null, window => {
    openAmapNavigationTo(126, 45)
    assert.equal(window.location.href, buildAmapNavigationLinks(126, 45).web)
  })
})

// Exercise the component's actual navigation state/handlers without loading
// the remote map SDK or pretending a desktop browser can launch a phone app.
const component = readFileSync(new URL('../src/components/AmapContainer.vue', import.meta.url), 'utf8')
const handlers = component.slice(component.indexOf('const harmonyNavOpen ='), component.indexOf('onMounted(async () =>'))
const handlerJs = ts.transpileModule(handlers, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText
function navigationState(geolocationRaw, env = {}) {
  const factory = new Function(
    'ref', 'computed', 'buildAmapNavigationLinks', 'isHarmonyOS', 'openAmapNavigationTo',
    'geolocationRaw', 'navigator', 'navTarget', 'document', 'window', 'disposeAmapSchemeLauncher', 'launchAmapScheme', 'setTimeout', 'clearTimeout',
    `${handlerJs}\nreturn { prepareHarmonyNavigation, closeHarmonyNavigation, openNavForCurrent,
      harmonyNavOpen, harmonyNavLoading, harmonyNavError, harmonyNavTarget, harmonyNavigationLinks, tryHarmonyScheme, harmonyLaunchHint }`,
  )
  return factory(ref, computed, buildAmapNavigationLinks, isHarmonyOS, openAmapNavigationTo,
    geolocationRaw, { userAgent: 'Phone; OpenHarmony 5.0' }, ref({ lng: 126, lat: 45, name: '北门' }),
    env.document ?? { removeEventListener() {}, addEventListener() {}, visibilityState: 'visible' },
    env.window ?? { removeEventListener() {}, addEventListener() {} },
    env.dispose ?? (() => {}), env.launch ?? (() => {}), env.setTimeout ?? setTimeout, env.clearTimeout ?? clearTimeout)
}

test('Harmony button obtains a real GCJ-02 origin and prepares a link without launching from the callback', () => {
  const callbacks = []
  const state = navigationState({ getCurrentPosition: callback => callbacks.push(callback) })
  state.openNavForCurrent()
  assert.equal(state.harmonyNavOpen.value, true)
  assert.equal(state.harmonyNavLoading.value, true)
  assert.equal(state.harmonyNavigationLinks.value.harmony, undefined)
  callbacks[0]('complete', { position: { lng: 125, lat: 44 } })
  assert.equal(state.harmonyNavLoading.value, false)
  assert.equal(state.harmonyNavError.value, '')
  const route = new URL(state.harmonyNavigationLinks.value.harmony)
  assert.equal(route.searchParams.get('slon'), '125')
  assert.equal(route.searchParams.get('slat'), '44')
  assert.equal(route.searchParams.get('dname'), '北门')
})

test('location permission failure keeps the web entry and hides the native link', () => {
  const state = navigationState({ getCurrentPosition: callback => callback('error', { info: 'PERMISSION_DENIED' }) })
  state.openNavForCurrent()
  assert.equal(state.harmonyNavLoading.value, false)
  assert.ok(state.harmonyNavError.value)
  assert.equal(state.harmonyNavigationLinks.value.harmony, undefined)
  assert.equal(new URL(state.harmonyNavigationLinks.value.web).hostname, 'uri.amap.com')
})

test('closing or retrying ignores stale location callbacks and preserves the chosen destination', () => {
  const callbacks = []
  const state = navigationState({ getCurrentPosition: callback => callbacks.push(callback) })
  state.openNavForCurrent()
  state.closeHarmonyNavigation()
  callbacks[0]('complete', { position: { lng: 125, lat: 44 } })
  assert.equal(state.harmonyNavOpen.value, false)
  assert.equal(state.harmonyNavigationLinks.value.harmony, undefined)
  state.openNavForCurrent()
  state.prepareHarmonyNavigation({ lng: 127, lat: 46, name: '南门' })
  callbacks[2]('complete', { position: { lng: 124, lat: 43 } })
  callbacks[1]('error', {})
  const route = new URL(state.harmonyNavigationLinks.value.harmony)
  assert.equal(route.searchParams.get('dname'), '南门')
  assert.equal(route.searchParams.get('slon'), '124')
  assert.equal(state.harmonyNavError.value, '')
})

test('missing geolocation, SDK errors and invalid positions produce recoverable errors', () => {
  for (const sdk of [null,
    { getCurrentPosition() { throw new Error('SDK error') } },
    { getCurrentPosition: callback => callback('complete', { position: { lng: 999, lat: 44 } }) },
  ]) {
    const state = navigationState(sdk)
    state.openNavForCurrent()
    assert.equal(state.harmonyNavLoading.value, false)
    assert.ok(state.harmonyNavError.value)
    assert.equal(state.harmonyNavigationLinks.value.harmony, undefined)
  }
})

test('scheme launcher reuses one hidden frame and can remove it without changing page location', () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'document')
  let frame
  let created = 0
  const document = {
    getElementById: () => frame,
    createElement: tag => {
      assert.equal(tag, 'iframe')
      created++
      return { remove() { frame = undefined } }
    },
    body: { appendChild: element => { frame = element } },
  }
  Object.defineProperty(globalThis, 'document', { configurable: true, value: document })
  try {
    const uri = buildAmapNavigationLinks(126, 45, '北门', { lng: 125, lat: 44 }).harmony
    launchAmapScheme(uri)
    assert.equal(frame.hidden, true)
    assert.equal(frame.src, uri)
    launchAmapScheme(uri)
    assert.equal(created, 1)
    disposeAmapSchemeLauncher()
    assert.equal(frame, undefined)
  } finally {
    if (previous) Object.defineProperty(globalThis, 'document', previous)
    else delete globalThis.document
  }
})

test('unconfirmed launch reports browser restrictions without redirecting to download', () => {
  let tick
  const launches = []
  const state = navigationState({ getCurrentPosition: callback => callback('complete', { position: { lng: 125, lat: 44 } }) }, {
    setTimeout: callback => { tick = callback; return 1 }, clearTimeout() {},
    launch: uri => launches.push(uri),
  })
  state.openNavForCurrent()
  state.tryHarmonyScheme()
  assert.deepEqual(launches, [state.harmonyNavigationLinks.value.harmony])
  tick()
  assert.match(state.harmonyLaunchHint.value, /尚未确认/)
  assert.match(state.harmonyLaunchHint.value, /无需重新下载安装/)
})

test('app switch during scheme launch avoids a false failure message', () => {
  let tick
  let visibilityCallback
  const document = {
    visibilityState: 'visible', removeEventListener() {},
    addEventListener: (name, callback) => { if (name === 'visibilitychange') visibilityCallback = callback },
  }
  const state = navigationState({ getCurrentPosition: callback => callback('complete', { position: { lng: 125, lat: 44 } }) }, {
    document, setTimeout: callback => { tick = callback; return 1 }, clearTimeout() {},
  })
  state.openNavForCurrent()
  state.tryHarmonyScheme()
  document.visibilityState = 'hidden'
  visibilityCallback()
  document.visibilityState = 'visible'
  tick()
  assert.equal(state.harmonyLaunchHint.value, '')
})
