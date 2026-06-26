import { getApi, postApi } from './client'

export interface AdminUser {
  id: number
  username: string
  role: string
  created_at: number
  last_login_at?: number | null
}

export interface AuthStatus {
  admin_initialized: boolean
}

export interface TokenPayload {
  token: string
  token_type: string
  user: AdminUser
}

export function fetchAuthStatus() {
  return getApi<AuthStatus>('/auth/status')
}

export function initAdmin(username: string, password: string) {
  return postApi<{ user: AdminUser }>('/auth/init-admin', { username, password })
}

export function login(username: string, password: string) {
  return postApi<TokenPayload>('/auth/login', { username, password })
}

export function logout() {
  return postApi<Record<string, never>>('/auth/logout')
}

export function fetchMe() {
  return getApi<AdminUser>('/auth/me')
}

