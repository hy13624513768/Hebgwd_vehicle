import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/lib/browserDrivingRoute.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } })
const { planBrowserDrivingRoute } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)

function sdk(status = 'complete', routes) {
  const calls = []
  class Driving {
    constructor(options) {
      assert.equal(options.map, undefined, 'search must not draw stale results automatically')
    }
    search(origin, destination, callback) {
      calls.push([origin, destination])
      callback(status, { routes })
    }
  }
  return { Driving, calls }
}
const locate = { getCurrentPosition: callback => callback('complete', { position: { lng: 125.5, lat: 44.5 } }) }

test('browser route uses real GCJ-02 origin, selected destination and AMap step geometry', async () => {
  const amap = sdk('complete', [{ distance: 1500, time: 360, steps: [{
    instruction: '沿道路向北行驶', distance: 1500,
    path: [{ lng: 125.5, lat: 44.5 }, { getLng: () => 126, getLat: () => 45 }],
  }] }])
  const route = await planBrowserDrivingRoute(amap, locate, { lng: 126, lat: 45 })
  assert.deepEqual(amap.calls, [[[125.5, 44.5], [126, 45]]])
  assert.deepEqual(route.path, [[125.5, 44.5], [126, 45]])
  assert.equal(route.distance, 1500)
  assert.equal(route.duration, 360)
  assert.equal(route.steps[0].instruction, '沿道路向北行驶')
})

test('denied location does not start a route from a fabricated origin', async () => {
  const amap = sdk()
  await assert.rejects(planBrowserDrivingRoute(amap, {
    getCurrentPosition: callback => callback('error', {}),
  }, { lng: 126, lat: 45 }), /定位/)
  assert.deepEqual(amap.calls, [])
})

test('missing SDK and no route return actionable errors', async () => {
  await assert.rejects(planBrowserDrivingRoute({}, locate, { lng: 126, lat: 45 }), /未就绪/)
  await assert.rejects(planBrowserDrivingRoute(sdk('no_data', []), locate, { lng: 126, lat: 45 }), /未能规划/)
})

test('invalid path is rejected and coordinate arrays are supported', async () => {
  await assert.rejects(planBrowserDrivingRoute(sdk('complete', [{ steps: [{ path: [[999, 45]] }] }]), locate,
    { lng: 126, lat: 45 }), /不完整/)
  const route = await planBrowserDrivingRoute(sdk('complete', [{ steps: [{ path: [[125, 44], [126, 45]] }] }]), locate,
    { lng: 126, lat: 45 })
  assert.deepEqual(route.path, [[125, 44], [126, 45]])
})
