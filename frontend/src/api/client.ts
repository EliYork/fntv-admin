import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '../types/api'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15000
})

let redirectingToLogin = false

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('fntv_admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isCancel(error)) {
      return Promise.reject(error)
    }
    const message = error.response?.data?.error?.message || '请求失败'
    if (error.response?.status === 401) {
      localStorage.removeItem('fntv_admin_token')
      if (!redirectingToLogin && window.location.pathname !== '/login') {
        redirectingToLogin = true
        const redirect = `${window.location.pathname}${window.location.search}${window.location.hash}`
        window.location.assign(`/login?redirect=${encodeURIComponent(redirect)}`)
      }
      return Promise.reject(new Error('登录已过期，请重新登录'))
    }
    if (error.response?.status !== 401) {
      ElMessage.error(message)
    }
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
