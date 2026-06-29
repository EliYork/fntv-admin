import { defineStore } from 'pinia'
import { fetchMe, login, logout, type AdminUser } from '../api/auth'
import { clearStoredToken, getLastAuthError, getStoredToken, setStoredToken } from '../api/client'

interface AuthState {
  token: string
  user: AdminUser | null
  checked: boolean
  loadingMe: Promise<AdminUser | null> | null
  accessDeniedMessage: string
  lastAuthErrorEndpoint: string
  lastAuthErrorStatus: number | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: getStoredToken(),
    user: null,
    checked: false,
    loadingMe: null,
    accessDeniedMessage: '',
    lastAuthErrorEndpoint: '',
    lastAuthErrorStatus: null
  }),
  getters: {
    hasToken: (state) => Boolean(state.token || getStoredToken()),
    isAuthenticated: (state) => Boolean(state.token || getStoredToken() || state.user?.auth_mode === 'local_no_auth'),
    isLocalNoAuth: (state) => state.user?.auth_mode === 'local_no_auth',
    authPolicy: (state) =>
      state.user
        ? {
            local_auth_required: state.user.local_auth_required,
            remote_access_policy: state.user.remote_access_policy,
            is_local_request: state.user.is_local_request,
            auth_mode: state.user.auth_mode
          }
        : null
  },
  actions: {
    syncTokenFromStorage() {
      this.token = getStoredToken()
    },
    async login(username: string, password: string) {
      const payload = await login(username, password)
      setStoredToken(payload.token)
      this.token = getStoredToken()
      this.user = payload.user
      this.checked = true
      this.accessDeniedMessage = ''
      this.lastAuthErrorEndpoint = ''
      this.lastAuthErrorStatus = null
    },
    async loadMe(force = false) {
      if (this.loadingMe) return this.loadingMe
      if (!force && this.checked && this.user) return this.user
      this.syncTokenFromStorage()
      this.loadingMe = (async () => {
        try {
          const user = await fetchMe()
          this.user = user
          this.checked = true
          this.accessDeniedMessage = ''
          if (user.auth_mode === 'local_no_auth') {
            this.token = ''
            clearStoredToken()
          } else {
            this.syncTokenFromStorage()
          }
          return user
        } catch (error) {
          this.checked = true
          this.captureAuthError(error)
          if (isUnauthorized(error)) {
            this.user = null
            this.token = ''
            clearStoredToken()
            this.accessDeniedMessage = ''
          } else if (isForbidden(error)) {
            this.accessDeniedMessage = authErrorMessage(error)
          }
          throw error
        } finally {
          this.loadingMe = null
        }
      })()
      return this.loadingMe
    },
    async ensureReady() {
      if (this.checked && this.isAuthenticated) return true
      if (this.checked && this.accessDeniedMessage) return false
      this.syncTokenFromStorage()
      if (this.checked && !this.hasToken && !this.user) return false
      try {
        await this.loadMe()
        return this.isAuthenticated
      } catch (error) {
        if (isUnauthorized(error)) return false
        if (this.hasToken && !isForbidden(error)) return true
        return Boolean(this.hasToken && this.accessDeniedMessage)
      }
    },
    async logout() {
      try {
        if (this.token || this.user?.auth_mode === 'local_no_auth') await logout()
      } finally {
        this.token = ''
        if (this.user?.auth_mode !== 'local_no_auth') {
          this.user = null
        }
        clearStoredToken()
      }
    },
    captureAuthError(error: unknown) {
      const status = httpStatus(error)
      if (status) {
        const last = getLastAuthError()
        this.lastAuthErrorEndpoint = last.endpoint || endpoint(error)
        this.lastAuthErrorStatus = status
      }
    }
  }
})

function authErrorMessage(error: unknown): string {
  if (isForbidden(error)) return errorMessage(error) || '外部访问已被禁止'
  return ''
}

function isUnauthorized(error: unknown): boolean {
  return httpStatus(error) === 401
}

function isForbidden(error: unknown): boolean {
  return httpStatus(error) === 403
}

function httpStatus(error: unknown): number | undefined {
  return (error as { response?: { status?: number } }).response?.status
}

function errorMessage(error: unknown): string {
  return (error as { response?: { data?: { error?: { message?: string } } } }).response?.data?.error?.message || ''
}

function endpoint(error: unknown): string {
  return (error as { config?: { url?: string } }).config?.url || ''
}
