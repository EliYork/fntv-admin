import { defineStore } from 'pinia'
import { fetchMe, login, logout, type AdminUser } from '../api/auth'

interface AuthState {
  token: string
  user: AdminUser | null
  checked: boolean
  loadingMe: Promise<AdminUser | null> | null
  accessDeniedMessage: string
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('fntv_admin_token') || '',
    user: null,
    checked: false,
    loadingMe: null,
    accessDeniedMessage: ''
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token || state.user?.auth_mode === 'local_no_auth'),
    isLocalNoAuth: (state) => state.user?.auth_mode === 'local_no_auth'
  },
  actions: {
    async login(username: string, password: string) {
      const payload = await login(username, password)
      this.token = payload.token
      this.user = payload.user
      this.checked = true
      this.accessDeniedMessage = ''
      if (payload.token) {
        localStorage.setItem('fntv_admin_token', payload.token)
      } else {
        localStorage.removeItem('fntv_admin_token')
      }
    },
    async loadMe(force = false) {
      if (this.loadingMe) return this.loadingMe
      if (!force && this.checked && this.user) return this.user
      this.loadingMe = (async () => {
        try {
          const user = await fetchMe()
          this.user = user
          this.checked = true
          this.accessDeniedMessage = ''
          if (user.auth_mode === 'local_no_auth') {
            this.token = ''
            localStorage.removeItem('fntv_admin_token')
          }
          return user
        } catch (error) {
          this.checked = true
          this.user = null
          this.accessDeniedMessage = authErrorMessage(error)
          if (this.token) {
            this.token = ''
            localStorage.removeItem('fntv_admin_token')
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
      if (this.checked && !this.token && !this.user) return false
      try {
        await this.loadMe()
        return this.isAuthenticated
      } catch {
        return false
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
        localStorage.removeItem('fntv_admin_token')
      }
    }
  }
})

function authErrorMessage(error: unknown): string {
  const maybe = error as { response?: { status?: number; data?: { error?: { message?: string } } } }
  if (maybe.response?.status === 403) {
    return maybe.response.data?.error?.message || '外部访问已被禁止'
  }
  return ''
}
