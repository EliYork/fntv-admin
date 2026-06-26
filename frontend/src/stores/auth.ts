import { defineStore } from 'pinia'
import { fetchMe, login, logout, type AdminUser } from '../api/auth'

interface AuthState {
  token: string
  user: AdminUser | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('fntv_admin_token') || '',
    user: null
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token)
  },
  actions: {
    async login(username: string, password: string) {
      const payload = await login(username, password)
      this.token = payload.token
      this.user = payload.user
      localStorage.setItem('fntv_admin_token', payload.token)
    },
    async loadMe() {
      if (!this.token) return
      this.user = await fetchMe()
    },
    async logout() {
      try {
        if (this.token) await logout()
      } finally {
        this.token = ''
        this.user = null
        localStorage.removeItem('fntv_admin_token')
      }
    }
  }
})

