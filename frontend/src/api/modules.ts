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
  user_guid: string
  username: string
  user: string
  item_guid: string
  title: string
  display_title: string
  played_at?: string | null
  position_seconds?: number | null
  runtime_seconds?: number | null
  progress_percent?: number | null
  progress?: string | null
  watched: boolean
  watched_text: string
  resolution?: string | null
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
  watch_duration: string
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
  runtime_seconds?: number | null
  release_time?: string | number | null
  parent?: string | null
  parent_guid?: string | null
  children_count: number
  play_count: number
  last_play_at?: string | number | null
  hidden: boolean
  favorite?: boolean
  note?: string | null
}

export interface ReportOverview {
  total_users: number
  total_media: number
  total_play_records: number
  watched_records: number
  active_users_7d: number
  active_users_30d: number
  plays_7d: number
  plays_30d: number
  total_watch_seconds: number
  avg_progress_percent?: number | null
  generated_at: string
}

export interface PlayTrendItem {
  date: string
  play_count: number
  watched_count: number
  active_user_count: number
}

export interface TopUserReportItem {
  user_guid: string
  username: string
  play_count: number
  watched_count: number
  watch_seconds: number
  last_played_at?: string | null
}

export interface TopMediaReportItem {
  item_guid: string
  title: string
  type: string
  play_count: number
  watched_count: number
  last_played_at?: string | null
  parent_title?: string | null
}

export interface MediaTypeDistributionItem {
  type: string
  count: number
}

export interface ResolutionDistributionItem {
  resolution: string
  play_count: number
}

export function fetchDashboardOverview() {
  return getApi<DashboardOverview>('/dashboard/overview')
}

export function fetchRecentActivities(limit = 20) {
  return getApi<HistoryItem[]>('/dashboard/recent-activities', { limit })
}

export function fetchHistory(params: Record<string, unknown>) {
  return getApi<PageData<HistoryItem>>('/history', params)
}

export async function downloadHistoryCsv(params?: Record<string, unknown>) {
  const response = await apiClient.get('/history/export', { params, responseType: 'blob' })
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

export function fetchReportOverview() {
  return getApi<ReportOverview>('/reports/overview', undefined, { suppressGlobalError: true })
}

export function fetchReportPlayTrend(days: number | string = 30) {
  return getApi<PlayTrendItem[]>('/reports/play-trend', { days }, { suppressGlobalError: true })
}

export function fetchReportTopUsers(params: { days: string; limit: number }) {
  return getApi<TopUserReportItem[]>('/reports/top-users', params, { suppressGlobalError: true })
}

export function fetchReportTopMedia(params: { days: string; limit: number; mode?: 'episode' | 'series' }) {
  return getApi<TopMediaReportItem[]>('/reports/top-media', params, { suppressGlobalError: true })
}

export function fetchReportMediaTypeDistribution() {
  return getApi<MediaTypeDistributionItem[]>('/reports/media-type-distribution', undefined, { suppressGlobalError: true })
}

export function fetchReportResolutionDistribution(days: string) {
  return getApi<ResolutionDistributionItem[]>('/reports/resolution-distribution', { days }, { suppressGlobalError: true })
}

export interface LogItem {
  id?: string | number
  level?: string
  message?: string
  created_at?: string | number | null
}

export interface TaskItem {
  id?: string | number
  task_type?: string
  status?: string
  message?: string
  started_at?: string | number | null
}

export function fetchLogs(params: Record<string, unknown>) {
  return getApi<PageData<LogItem>>('/logs', params)
}

export function fetchTasks(params: Record<string, unknown>) {
  return getApi<PageData<TaskItem>>('/tasks', params)
}
