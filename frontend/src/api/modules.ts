import { apiClient, getApi, putApi, postApi } from './client'
import type { PageData } from '../types/api'

export interface DashboardOverview {
  database_ok: boolean
  error?: string
  total_users: number
  total_media: number
  total_play_records: number
  today_plays: number
  latest_play_time?: string | number | null
}

export interface HistoryItem {
  id: string
  user: string
  title: string
  played_at?: string | number | null
  progress?: string | number | null
  watched: boolean
}

export interface UserItem {
  guid: string
  username: string
  is_admin: boolean
  status: string
  last_login_at?: string | number | null
  last_play_at?: string | number | null
  play_count: number
  watch_seconds: number
  hidden: boolean
  display_name?: string | null
  note?: string | null
}

export interface MediaItem {
  guid: string
  title: string
  original_title: string
  media_type: string
  runtime?: string | number | null
  release_time?: string | number | null
  parent?: string | null
  children_count: number
  play_count: number
  last_play_at?: string | number | null
  hidden: boolean
  note?: string | null
}

export function fetchDashboardOverview() {
  return getApi<DashboardOverview>('/dashboard/overview')
}

export function fetchRecentActivities() {
  return getApi<HistoryItem[]>('/dashboard/recent-activities')
}

export function fetchHistory(params: Record<string, unknown>) {
  return getApi<PageData<HistoryItem>>('/history', params)
}

export async function downloadHistoryCsv() {
  const response = await apiClient.get('/history/export', { responseType: 'blob' })
  return response.data as Blob
}

export function fetchUsers(params: Record<string, unknown>) {
  return getApi<PageData<UserItem>>('/users', params)
}

export function updateUserProfile(guid: string, data: { display_name?: string; note?: string }) {
  return putApi(`/users/${encodeURIComponent(guid)}/profile`, data)
}

export function hideUser(guid: string, hidden: boolean) {
  return postApi(`/users/${encodeURIComponent(guid)}/${hidden ? 'hide' : 'unhide'}`)
}

export function fetchMedia(params: Record<string, unknown>) {
  return getApi<PageData<MediaItem>>('/media', params)
}

export function updateMediaProfile(guid: string, data: { display_title?: string; note?: string }) {
  return putApi(`/media/${encodeURIComponent(guid)}/profile`, data)
}

export function hideMedia(guid: string, hidden: boolean) {
  return postApi(`/media/${encodeURIComponent(guid)}/${hidden ? 'hide' : 'unhide'}`)
}
