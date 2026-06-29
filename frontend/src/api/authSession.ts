export const TOKEN_STORAGE_KEY = 'fntv_admin_token'

export type UnauthorizedAction = 'ignore' | 'recheck' | 'expire'

export interface UnauthorizedContext {
  status?: number
  url?: string
  skipAuthRecheck?: boolean
}

export function getStoredToken(): string {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
}

export function setStoredToken(token: string): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY)
  }
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export function shouldClearTokenForStatus(status?: number): boolean {
  return status === 401
}

export function getUnauthorizedAction(context: UnauthorizedContext): UnauthorizedAction {
  if (context.status !== 401) return 'ignore'
  if (context.skipAuthRecheck) return 'expire'
  const path = normalizeApiPath(context.url)
  if (path === '/auth/me' || path === '/auth/logout') return 'expire'
  if (path === '/auth/login' || path === '/auth/init-admin' || path === '/auth/status') return 'ignore'
  return 'recheck'
}

export function normalizeApiPath(url?: string): string {
  if (!url) return ''
  const withoutOrigin = url.replace(/^https?:\/\/[^/]+/i, '')
  const withoutQuery = withoutOrigin.split(/[?#]/, 1)[0] || ''
  return withoutQuery.startsWith('/api/') ? withoutQuery.slice(4) : withoutQuery
}
