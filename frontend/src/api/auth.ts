import { getApi, postApi, putApi } from './client'

export interface AdminUser {
  id: number | null
  username: string
  role: string
  created_at: number
  last_login_at?: number | null
  is_admin: boolean
  auth_mode: 'jwt' | 'local_no_auth'
  is_local_request: boolean
  local_auth_required: boolean
  remote_access_policy: RemoteAccessPolicy
}

export interface AuthStatus {
  admin_initialized: boolean
}

export interface TokenPayload {
  token: string
  token_type: string
  user: AdminUser
}

export type RemoteAccessPolicy = 'login' | 'deny'

export interface AuthPolicy {
  local_auth_required: boolean
  remote_access_policy: RemoteAccessPolicy
  trust_proxy_headers: boolean
  is_local_request?: boolean | null
  client_ip?: string | null
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

export function fetchAuthPolicy() {
  return getApi<AuthPolicy>('/settings/auth-policy')
}

export function updateAuthPolicy(payload: Pick<AuthPolicy, 'local_auth_required' | 'remote_access_policy'>) {
  return putApi<AuthPolicy>('/settings/auth-policy', payload)
}
