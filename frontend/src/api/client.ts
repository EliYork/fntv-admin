import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { AxiosRequestConfig } from 'axios'
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
    suppressGlobalError?: boolean
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
let lastToastMessage = ''
let lastToastAt = 0

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
    const suppressGlobalError = Boolean(error.config?.suppressGlobalError)
    rememberAuthError(error.config?.url, status)
    const message = normalizeErrorMessage(status, error.response?.data?.error?.message)
    const action = getUnauthorizedAction({
      status,
      url: error.config?.url,
      skipAuthRecheck: error.config?.skipAuthRecheck
    })
    if (action === 'expire') {
      expireSession()
      showErrorToast('请先登录')
      return Promise.reject(error)
    }
    if (action === 'recheck') {
      const stillValid = await recheckCurrentSession()
      if (!stillValid) {
        expireSession()
        showErrorToast('请先登录')
        return Promise.reject(error)
      }
      return Promise.reject(error)
    }
    if (status === 401) return Promise.reject(new Error(message))
    if (!suppressGlobalError) showErrorToast(message)
    return Promise.reject(error)
  }
)

export async function getApi<T>(url: string, params?: Record<string, unknown>, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url, { ...config, params })
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

function normalizeErrorMessage(status: number | undefined, message: unknown): string {
  if (status === 403) return '无权限或访问被禁止'
  if (typeof message === 'string' && message.trim()) {
    if (status !== 401 && message.includes('请先登录')) return '请求失败，请稍后重试'
    return message
  }
  if (status && status >= 500) return '服务器暂时不可用'
  return '请求失败'
}

function showErrorToast(message: string): void {
  const now = Date.now()
  if (message === lastToastMessage && now - lastToastAt < 3000) return
  lastToastMessage = message
  lastToastAt = now
  ElMessage.error(message)
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
