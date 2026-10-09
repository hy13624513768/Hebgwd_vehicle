const TOKEN_KEY = 'access_token'
let memoryToken: string | undefined

// Preserve logout/account changes made in another tab after using memory here.
if (typeof window !== 'undefined' && window.addEventListener) {
  window.addEventListener('storage', (event) => {
    try {
      if (event.storageArea !== window.localStorage) return
      if (event.key === TOKEN_KEY || event.key === null) {
        memoryToken = event.newValue ?? ''
        try { window.sessionStorage.removeItem(TOKEN_KEY) } catch { /* Best effort. */ }
      }
    } catch { /* Local storage access may itself throw. */ }
  })
}

function readStoredToken(kind: 'localStorage' | 'sessionStorage'): string {
  try {
    return window[kind].getItem(TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function getAccessToken(): string {
  // All request paths must use the same token when browser storage is restricted.
  return memoryToken ?? (readStoredToken('localStorage') || readStoredToken('sessionStorage'))
}

export function setAccessToken(token: string): void {
  memoryToken = token
  try {
    window.localStorage.setItem(TOKEN_KEY, token)
    try { window.sessionStorage.removeItem(TOKEN_KEY) } catch { /* Storage may be blocked. */ }
    return
  } catch {
    // Some mobile browsers allow reads but reject writes (quota or privacy policy).
    try { window.localStorage.removeItem(TOKEN_KEY) } catch { /* Best effort. */ }
  }
  try { window.sessionStorage.setItem(TOKEN_KEY, token) } catch { /* Use this page's memory. */ }
}

export function clearAccessToken(): void {
  memoryToken = ''
  for (const kind of ['localStorage', 'sessionStorage'] as const) {
    try { window[kind].removeItem(TOKEN_KEY) } catch { /* Logout must still clear memory. */ }
  }
}
