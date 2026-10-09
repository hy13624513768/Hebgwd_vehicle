import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { createPinia, setActivePinia } from 'pinia'

let serial = 0
const asModule = (source) => `data:text/javascript;base64,${Buffer.from(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 } }).outputText + `\n// instance ${serial++}`).toString('base64')}`
const read = (file) => readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8')
function storage(initial = {}, blocked = []) {
  const values = new Map(Object.entries(initial))
  return {
    getItem(key) { if (blocked.includes('read')) throw new DOMException('Blocked', 'SecurityError'); return values.get(key) ?? null },
    setItem(key, value) { if (blocked.includes('write')) throw new DOMException('Full', 'QuotaExceededError'); values.set(key, value) },
    removeItem(key) { if (blocked.includes('remove')) throw new DOMException('Blocked', 'SecurityError'); values.delete(key) },
  }
}
async function setup(local, session, getterBlocked = false) {
  const replacements = []
  const listeners = {}
  globalThis.window = { addEventListener: (name, fn) => { listeners[name] = fn }, sessionStorage: session, location: { pathname: '/app/dashboard', search: '', replace: (url) => replacements.push(url) } }
  if (getterBlocked) Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('Blocked', 'SecurityError') } })
  else window.localStorage = local
  const tokenUrl = asModule(read('lib/authToken.ts'))
  const token = await import(tokenUrl)
  const httpUrl = asModule(read('api/http.ts').replace("from 'axios'", `from '${import.meta.resolve('axios')}'`).replace("from '@/lib/authToken'", `from '${tokenUrl}'`).replace('import.meta.env.VITE_API_BASE_URL', 'undefined'))
  const { http } = await import(httpUrl)
  const authUrl = asModule(read('api/auth.ts').replace("from '@/api/http'", `from '${httpUrl}'`))
  const storeUrl = asModule(read('stores/user.ts').replace("from 'pinia'", `from '${import.meta.resolve('pinia')}'`).replace("from '@/api/auth'", `from '${authUrl}'`).replace("from '@/lib/authToken'", `from '${tokenUrl}'`))
  setActivePinia(createPinia())
  const { useUserStore } = await import(storeUrl)
  const user = useUserStore()
  const calls = []
  http.defaults.adapter = async (config) => {
    calls.push(config)
    return { data: config.url === '/auth/login' ? { access_token: 'new-token', user: { id: 1, username: 'test', display_name: 'test', role: 'staff', workshop_id: null } } : { id: 1, username: 'test' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  return { token, http, user, calls, replacements, listeners }
}
const login = (user) => user.login({ username: 'test', password: 'test-password' })

test('normal login persists the token and authenticates subsequent requests', async () => {
  const local = storage()
  const { user, calls } = await setup(local, storage())
  await login(user)
  assert.equal(local.getItem('access_token'), 'new-token')
  await user.fetchMe()
  assert.equal(calls[1].headers.Authorization, 'Bearer new-token')
  user.logout()
  assert.equal(local.getItem('access_token'), null)
})

test('mobile quota failure still completes login and falls back to session storage', async () => {
  const session = storage()
  const { user, calls } = await setup(storage({}, ['write']), session)
  await login(user)
  assert.equal(user.token, 'new-token')
  assert.equal(session.getItem('access_token'), 'new-token')
  await user.fetchMe()
  assert.equal(calls[1].headers.Authorization, 'Bearer new-token')
})

test('blocked storage getters and session storage still allow login, API calls and logout', async () => {
  const { user, calls, token } = await setup(null, storage({}, ['read', 'write', 'remove']), true)
  await login(user)
  await user.fetchMe()
  assert.equal(calls[1].headers.Authorization, 'Bearer new-token')
  user.logout()
  assert.equal(token.getAccessToken(), '')
  assert.equal(user.profile, null)
  await user.fetchMe()
  assert.equal(calls[2].headers.Authorization, undefined)
})

test('an unwritable old token cannot replace the newly authenticated token', async () => {
  const { user, calls } = await setup(storage({ access_token: 'stale-token' }, ['write', 'remove']), storage({}, ['write']))
  await login(user)
  await user.fetchMe()
  assert.equal(calls[1].headers.Authorization, 'Bearer new-token')
  user.logout()
  await user.fetchMe()
  assert.equal(calls[2].headers.Authorization, undefined)
})

test('reload restores a session token when local persistence is unavailable', async () => {
  const { user, calls } = await setup(storage({}, ['read', 'write']), storage({ access_token: 'session-token' }))
  assert.equal(user.token, 'session-token')
  await user.fetchMe()
  assert.equal(calls[0].headers.Authorization, 'Bearer session-token')
})

test('401 handling preserves the API error and redirects even when storage removal throws', async () => {
  const { user, http, token, replacements } = await setup(storage({}, ['write', 'remove']), storage({}, ['write', 'remove']))
  await login(user)
  const failure = { response: { status: 401 }, config: { url: '/auth/me' } }
  http.defaults.adapter = async () => { throw failure }
  await assert.rejects(user.fetchMe(), (error) => error === failure)
  assert.equal(token.getAccessToken(), '')
  assert.equal(replacements.length, 1)
})

test('incorrect-password responses leave error handling to the login page', async () => {
  const { user, http, replacements } = await setup(storage(), storage())
  const failure = { response: { status: 401, data: { detail: '用户名密码错误' } }, config: { url: '/auth/login' } }
  http.defaults.adapter = async () => { throw failure }
  await assert.rejects(login(user), (error) => error === failure)
  assert.equal(user.token, '')
  assert.equal(replacements.length, 0)
})

test('logout and account changes from another tab update subsequent requests', async () => {
  const local = storage()
  const { user, token, listeners, calls } = await setup(local, storage())
  await login(user)
  listeners.storage({ storageArea: local, key: 'access_token', newValue: 'other-account-token' })
  await user.fetchMe()
  assert.equal(calls[1].headers.Authorization, 'Bearer other-account-token')
  listeners.storage({ storageArea: local, key: 'access_token', newValue: null })
  assert.equal(token.getAccessToken(), '')
  await user.fetchMe()
  assert.equal(calls[2].headers.Authorization, undefined)
})
