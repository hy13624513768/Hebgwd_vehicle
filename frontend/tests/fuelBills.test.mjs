import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { nextTick } from 'vue'

// 执行页面的真实响应式逻辑，平台请求使用模拟接口，不触发真实同步。
const apiSource = `
export const calls = [];
export const syncCalls = [];
export let handler = async () => ({ items: [], total: 0 });
export function setHandler(fn) { handler = fn; }
export async function listFuelRecordsPaged(params) { calls.push({ ...params }); return handler(params); }
export async function listFuelRecordCardOptions() { return [{ card_asn: 'CARD-A', car_no: 'CAR-A' }, { card_asn: 'CARD-B', car_no: 'CAR-B' }]; }
export async function listFuelRecordWorkshops() { return ['W-A', 'W-B']; }
export async function listFuelRecordVehicles() { return ['CAR-A', 'CAR-B']; }
export async function syncFuelFromPlatform(params, onProgress) {
  syncCalls.push({ ...params });
  onProgress('等待验证码：系统正在自动读取短信转发邮件，请稍候…');
  return { ok: true, record_written: 663, record_inserted: 0, record_updated: 663, record_missing_card: 1, record_missing_volume: 1 };
}
`
const apiUrl = `data:text/javascript;base64,${Buffer.from(apiSource).toString('base64')}`
const api = await import(apiUrl)
const view = readFileSync(new URL('../src/views/app/FuelBillsView.vue', import.meta.url), 'utf8')
let script = view.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
script = script
  .replace("from 'vue'", `from '${import.meta.resolve('vue')}'`)
  .replace("import * as fuelApi from '@/api/fuel'", `import * as fuelApi from '${apiUrl}'`)
  .replace(/^import .* from '@\/components\/.*\r?\n/gm, '')
  .replace(/^import type .*\r?\n/gm, '')
  .replace('onBeforeUnmount, onMounted, ', '')
script += '\nexport { reload, recFilter, recSort, records, recordsTotal, recordCardOptions, toggleRecordSort, swapRecordSort, buildRecordQueryParams, nextRecordPage, loadingRecords, searchRecords, syncStatus, syncingRecords };'
script = 'const onMounted = () => {}; const onBeforeUnmount = () => {};\n' + script
const { outputText } = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } })
const page = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`)
const settle = async () => { await nextTick(); await new Promise(resolve => setImmediate(resolve)); await nextTick() }

test('filters update the list without another platform query and reset pagination', async () => {
  api.setHandler(async () => ({ items: [{ id: 1 }], total: 60 }))
  await page.reload()
  assert.equal(page.recordCardOptions.value[1].label, 'CAR-B：CARD-B')
  assert.equal(page.recordCardOptions.value[1].keywords, 'CAR-B CARD-B')
  page.nextRecordPage()
  await settle()
  assert.equal(page.recFilter.page, 2)
  api.calls.length = 0
  page.recFilter.vehicle_id = 2
  page.recFilter.workshop_id = 1
  page.recFilter.card_asn_id = 2
  page.recFilter.date_from = '2026-10-01'
  page.recFilter.date_to = '2026-10-08'
  await settle()
  assert.equal(api.calls.length, 1)
  assert.deepEqual(api.calls[0], {
    has_card_only: true, page: 1, page_size: 20,
    sort_by: 'occur_time', sort_dir: 'desc', sort_secondary_by: 'car_no', sort_secondary_dir: 'asc',
    car_no: 'CAR-B', workshop: 'W-A', card_asn: 'CARD-B', date_from: '2026-10-01', date_to: '2026-10-08',
  })
})

test('directions are independent and priorities can be swapped', async () => {
  page.toggleRecordSort('occur_time')
  await settle()
  assert.equal(api.calls.at(-1).sort_dir, 'asc')
  assert.equal(api.calls.at(-1).sort_secondary_dir, 'asc')
  page.toggleRecordSort('car_no')
  await settle()
  assert.equal(api.calls.at(-1).sort_dir, 'asc')
  assert.equal(api.calls.at(-1).sort_secondary_dir, 'desc')
  page.swapRecordSort()
  await settle()
  assert.equal(api.calls.at(-1).sort_by, 'car_no')
  assert.equal(api.calls.at(-1).sort_dir, 'desc')
  assert.equal(api.calls.at(-1).sort_secondary_by, 'occur_time')
  assert.equal(api.calls.at(-1).sort_secondary_dir, 'asc')
})

test('slow earlier filter requests cannot overwrite the latest result', async () => {
  const pending = []
  api.setHandler(() => new Promise(resolve => pending.push(resolve)))
  page.recFilter.vehicle_id = 1
  await settle()
  page.recFilter.vehicle_id = 2
  await settle()
  pending[1]({ items: [{ id: 22 }], total: 1 })
  await settle()
  pending[0]({ items: [{ id: 11 }], total: 99 })
  await settle()
  assert.deepEqual(page.records.value, [{ id: 22 }])
  assert.equal(page.recordsTotal.value, 1)
  assert.equal(page.loadingRecords.value, false)
})

test('invalid date range prevents a list request', async () => {
  api.calls.length = 0
  page.recFilter.date_from = '2026-10-09'
  await settle()
  assert.equal(api.calls.length, 0)
})

test('saved bills render directly without platform login and preserve the card selection', async () => {
  api.setHandler(async () => ({ items: [{ id: 22 }], total: 1 }))
  page.recFilter.date_from = '2026-10-01'
  await settle()
  api.syncCalls.length = 0
  await page.searchRecords()
  assert.equal(api.syncCalls.length, 0)
  assert.deepEqual(page.records.value, [{ id: 22 }])
  assert.equal(page.syncStatus.value, '共 1 条账单')
  assert.equal(page.syncingRecords.value, false)
  assert.equal(page.buildRecordQueryParams().card_asn, 'CARD-B')
})

test('empty database queries Kunlun once and later queries reuse saved bills', async () => {
  let reads = 0
  api.setHandler(async () => ++reads === 1 ? { items: [], total: 0 } : { items: [{ id: 33 }], total: 1 })
  api.syncCalls.length = 0
  await page.searchRecords()
  assert.equal(api.syncCalls.length, 1)
  assert.equal(api.syncCalls[0].target, 'bills')
  assert.equal(api.syncCalls[0].date_from, '2026-10-01')
  assert.equal(api.syncCalls[0].date_to, '2026-10-08')
  assert.deepEqual(page.records.value, [{ id: 33 }])
  assert.equal(page.syncStatus.value, '共 663 条账单')
  await page.searchRecords()
  assert.equal(api.syncCalls.length, 1)
  assert.equal(page.syncStatus.value, '共 1 条账单')
})

test('explicit update queries Kunlun even when saved bills exist', async () => {
  api.setHandler(async () => ({ items: [{ id: 44 }], total: 1 }))
  api.syncCalls.length = 0
  await page.searchRecords(true)
  assert.equal(api.syncCalls.length, 1)
  assert.equal(page.syncStatus.value, '共 663 条账单')
  assert.equal(page.buildRecordQueryParams().card_asn, 'CARD-B')
  assert.equal(page.syncingRecords.value, false)
})

test('database read failure stops the query without requesting Kunlun', async () => {
  api.setHandler(async () => { throw new Error('database unavailable') })
  api.syncCalls.length = 0
  await page.searchRecords()
  assert.equal(api.syncCalls.length, 0)
  assert.equal(page.syncStatus.value, '')
  assert.equal(page.syncingRecords.value, false)
  assert.equal(page.loadingRecords.value, false)
})

test('repeated clicks while reading saved bills cannot start duplicate queries', async () => {
  let complete
  api.setHandler(() => new Promise(resolve => { complete = resolve }))
  api.calls.length = 0
  api.syncCalls.length = 0
  const first = page.searchRecords()
  await page.searchRecords(true)
  assert.equal(api.calls.length, 1)
  complete({ items: [{ id: 55 }], total: 1 })
  await first
  assert.equal(api.syncCalls.length, 0)
  assert.equal(page.syncingRecords.value, false)
})
