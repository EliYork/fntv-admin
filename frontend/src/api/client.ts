import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '../types/api'
import {
  clearStoredToken,
  getStoredToken,
  getUnauthorizedAction,
  setStoredToken,
} from './authSession'

declare module 'axios' {
  export interface AxiosRequestConfig {
    skipAuthRecheck?: boolean
  }
}

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15000
})

let redirectingToLogin = false
let authRecheck: Promise<boolean> | null = null
let lastAuthErrorEndpoint = ''
let lastAuthErrorStatus: number | null = null

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (axios.isCancel(error)) {
      return Promise.reject(error)
    }
    const status = error.response?.status as number | undefined
    rememberAuthError(error.config?.url, status)
    const message = error.response?.data?.error?.message || '请求失败'
    const action = getUnauthorizedAction({
      status,
      url: error.config?.url,
      skipAuthRecheck: error.config?.skipAuthRecheck
    })
    if (action === 'expire') {
      expireSession()
      return Promise.reject(error)
    }
    if (action === 'recheck') {
      const stillValid = await recheckCurrentSession()
      if (!stillValid) {
        expireSession()
        return Promise.reject(error)
      }
      ElMessage.error(message)
      return Promise.reject(error)
    }
    if (status === 401) return Promise.reject(new Error(message))
    if (status !== 401) ElMessage.error(message)
    return Promise.reject(error)
  }
)

export async function getApi<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url, { params })
  if (!response.data.success) {
    throw new Error(response.data.error.message)
  }
  return response.data.data
}

export async function postApi<T>(url: string, data?: unknown): Promise<T> {
  const response = await apiClient.post<ApiResponse<T>>(url, data)
  if (!response.data.success) {
    throw new Error(response.data.error.message)
  }
  return response.data.data
}

export async function putApi<T>(url: string, data?: unknown): Promise<T> {
  const response = await apiClient.put<ApiResponse<T>>(url, data)
  if (!response.data.success) {
    throw new Error(response.data.error.message)
  }
  return response.data.data
}

export function getLastAuthError() {
  return {
    endpoint: lastAuthErrorEndpoint,
    status: lastAuthErrorStatus
  }
}

function rememberAuthError(url: string | undefined, status: number | undefined): void {
  if (!status) return
  lastAuthErrorEndpoint = url || ''
  lastAuthErrorStatus = status
  window.dispatchEvent(new CustomEvent('fntv-auth-error', { detail: getLastAuthError() }))
}

function expireSession(): void {
  clearStoredToken()
  if (!redirectingToLogin && window.location.pathname !== '/login') {
    redirectingToLogin = true
    const redirect = `${window.location.pathname}${window.location.search}${window.location.hash}`
    window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`)
  }
}

async function recheckCurrentSession(): Promise<boolean> {
  if (!getStoredToken()) return false
  if (!authRecheck) {
    authRecheck = apiClient
      .get('/auth/me', { skipAuthRecheck: true })
      .then(() => true)
      .catch((error) => {
        const status = error.response?.status as number | undefined
        return status !== 401
      })
      .finally(() => {
        authRecheck = null
      })
  }
  return authRecheck
}

export { getStoredToken, setStoredToken, clearStoredToken }
