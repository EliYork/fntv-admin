<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">报表中心</h1>
        <p class="page-subtitle">只读统计飞牛影视数据，不修改飞牛数据库</p>
      </div>
      <div class="header-actions">
        <div class="refresh-meta">
          <span>最后更新：{{ latestReportUpdatedAt || '-' }}</span>
          <span v-if="anyRefreshing">正在更新...</span>
        </div>
        <el-button :icon="Refresh" :loading="globalLoading && !hasAnyLoaded" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <div class="metrics section" v-loading="initialLoading(overview)">
      <div v-for="item in overviewMetrics" :key="item.label" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </div>
    </div>
    <div v-if="overview.error" class="section" :class="overview.hasLoaded ? 'inline-warning' : 'error-panel'">{{ overview.error }}</div>

    <div class="reports-grid section">
      <div class="table-panel">
        <div class="panel-title panel-title-row">
          <span>播放趋势</span>
          <span class="panel-heading-meta"><span>最近 1 年</span><span class="panel-state">{{ panelStatus(trend) }}</span></span>
        </div>
        <div class="panel-body" v-loading="initialLoading(trend)">
          <div v-if="trend.loading && trend.hasLoaded" class="inline-updating">正在更新...</div>
          <div v-if="trend.error" :class="trend.hasLoaded ? 'inline-warning' : 'inline-error'">{{ trend.error }}</div>
          <template v-if="trend.items.length">
            <PlaybackHeatmap :date-items="trend.items" :modes="['date']" />
          </template>
          <EmptyState v-else-if="!trend.loading && !trend.error" description="暂无播放趋势数据" />
        </div>
      </div>

      <div class="table-panel">
        <div class="panel-title panel-title-row">
          <span>播放时段分布</span>
          <span class="panel-controls">
            <el-select v-model="hourlyDays" class="period-select" size="small" aria-label="播放时段统计周期" @change="loadHourly">
              <el-option v-for="item in rangeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
            <span class="panel-state">{{ panelStatus(hourly) }}</span>
          </span>
        </div>
        <div class="panel-body" v-loading="initialLoading(hourly)">
          <div v-if="hourly.loading && hourly.hasLoaded" class="inline-updating">正在更新...</div>
          <div v-if="hourly.error" :class="hourly.hasLoaded ? 'inline-warning' : 'inline-error'">{{ hourly.error }}</div>
          <template v-if="hourly.items.length">
            <div v-for="row in hourly.items" :key="row.hour" class="distribution-row">
              <span class="distribution-name">{{ row.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: `${barWidth(row.play_count, hourlyMax)}%` }"></div>
              </div>
              <span class="distribution-count">{{ row.play_count }}</span>
            </div>
          </template>
          <EmptyState v-else-if="!hourly.loading && !hourly.error" description="暂无播放时段数据" />
        </div>
      </div>

      <div class="table-panel">
        <div class="panel-title panel-title-row">
          <span>媒体类型分布</span>
          <span class="panel-state">{{ panelStatus(mediaTypes) }}</span>
        </div>
        <div class="panel-body" v-loading="initialLoading(mediaTypes)">
          <div v-if="mediaTypes.loading && mediaTypes.hasLoaded" class="inline-updating">正在更新...</div>
          <div v-if="mediaTypes.error" :class="mediaTypes.hasLoaded ? 'inline-warning' : 'inline-error'">{{ mediaTypes.error }}</div>
          <template v-if="mediaTypes.items.length">
            <div v-for="row in mediaTypes.items" :key="row.type" class="distribution-row">
              <span class="distribution-name">{{ row.type || '未知' }}</span>
              <div class="bar-track">
                <div class="bar-fill alt" :style="{ width: `${barWidth(row.count, mediaTypeMax)}%` }"></div>
              </div>
              <span class="distribution-count">{{ row.count }}</span>
            </div>
          </template>
          <EmptyState v-else-if="!mediaTypes.loading && !mediaTypes.error" description="暂无媒体类型数据" />
        </div>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>活跃用户榜</span>
        <span class="panel-controls">
          <el-select v-model="topUsersDays" class="period-select" size="small" aria-label="活跃用户统计周期" @change="loadTopUsers">
            <el-option v-for="item in rangeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <span class="panel-state">{{ panelStatus(topUsers) }}</span>
        </span>
      </div>
      <div class="panel-body" v-loading="initialLoading(topUsers)">
        <div v-if="topUsers.loading && topUsers.hasLoaded" class="inline-updating">正在更新...</div>
        <div v-if="topUsers.error" :class="topUsers.hasLoaded ? 'inline-warning' : 'inline-error'">{{ topUsers.error }}</div>
        <el-table v-if="topUsers.items.length" :data="topUsers.items">
          <el-table-column label="用户" min-width="180">
            <template #default="{ row }">
              <span>{{ row.username || row.user_guid || '-' }}</span>
              <div v-if="row.username === row.user_guid" class="muted-guid">{{ row.user_guid }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="play_count" label="播放" width="100" />
          <el-table-column prop="watched_count" label="看完" width="100" />
          <el-table-column label="观看时长" width="140">
            <template #default="{ row }">{{ formatDuration(row.watch_seconds) }}</template>
          </el-table-column>
          <el-table-column prop="last_played_at" label="最近播放" min-width="170">
            <template #default="{ row }">{{ formatApplicationDateTime(row.last_played_at) }}</template>
          </el-table-column>
        </el-table>
        <EmptyState v-else-if="!topUsers.loading && !topUsers.error" description="暂无活跃用户数据" />
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>收藏记录</span>
        <span class="panel-state">{{ panelStatus(favorites) }}</span>
      </div>
      <div class="panel-body" v-loading="initialLoading(favorites)">
        <div v-if="favorites.loading && favorites.hasLoaded" class="inline-updating">正在更新...</div>
        <div v-if="favorites.error" :class="favorites.hasLoaded ? 'inline-warning' : 'inline-error'">{{ favorites.error }}</div>
        <el-table v-if="favorites.items.length" :data="favorites.items">
          <el-table-column prop="username" label="用户" min-width="160" />
          <el-table-column prop="title" label="媒体" min-width="260" />
          <el-table-column prop="media_type" label="类型" width="110" />
          <el-table-column prop="favorite_time" label="收藏时间" min-width="170">
            <template #default="{ row }">{{ formatApplicationDateTime(row.favorite_time) }}</template>
          </el-table-column>
        </el-table>
        <EmptyState v-else-if="!favorites.loading && !favorites.error" description="暂无收藏记录或未识别收藏表" />
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>热门媒体榜</span>
        <span class="panel-controls">
          <el-select v-model="topMediaDays" class="period-select" size="small" aria-label="热门媒体统计周期" @change="loadTopMedia">
            <el-option v-for="item in rangeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-radio-group v-model="topMediaMode" size="small" aria-label="热门媒体统计方式" @change="loadTopMedia">
            <el-radio-button value="episode">单集</el-radio-button>
            <el-radio-button value="series">整部剧</el-radio-button>
          </el-radio-group>
        </span>
      </div>
      <div class="panel-body" v-loading="initialLoading(topMedia)">
        <div class="panel-status-row">
          <span class="panel-state">{{ panelStatus(topMedia) }}</span>
        </div>
        <div v-if="topMedia.loading && topMedia.hasLoaded" class="inline-updating">正在更新...</div>
        <div v-if="topMedia.error" :class="topMedia.hasLoaded ? 'inline-warning' : 'inline-error'">{{ topMedia.error }}</div>
        <div class="report-content-stack">
          <div class="panel-note">{{ topMediaMode === 'series' ? '按剧级别合并单集播放记录；没有父级的媒体按自身统计。' : '按单条媒体或单集播放记录统计。' }}</div>
          <el-table v-if="hasListItems(topMedia)" :data="topMedia.items">
            <el-table-column label="媒体" min-width="260">
              <template #default="{ row }">
                <span>{{ row.title || row.item_guid || '-' }}</span>
                <div v-if="row.parent_title" class="muted-guid">{{ row.parent_title }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="play_count" label="播放" width="100" />
            <el-table-column prop="watched_count" label="看完" width="100" />
            <el-table-column prop="last_played_at" label="最近播放" min-width="170">
              <template #default="{ row }">{{ formatApplicationDateTime(row.last_played_at) }}</template>
            </el-table-column>
          </el-table>
          <EmptyState v-else-if="showListEmpty(topMedia)" description="暂无热门媒体数据" />
        </div>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>分辨率分布</span>
        <span class="panel-controls">
          <el-select v-model="resolutionDays" class="period-select" size="small" aria-label="分辨率统计周期" @change="loadResolutions">
            <el-option v-for="item in rangeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <span class="panel-state">{{ panelStatus(resolutions) }}</span>
        </span>
      </div>
      <div class="panel-body" v-loading="initialLoading(resolutions)">
        <div v-if="resolutions.loading && resolutions.hasLoaded" class="inline-updating">正在更新...</div>
        <div v-if="resolutions.error" :class="resolutions.hasLoaded ? 'inline-warning' : 'inline-error'">{{ resolutions.error }}</div>
        <div class="report-content-stack">
          <div v-if="hasListItems(resolutions)">
            <div v-for="row in resolutions.items" :key="row.resolution" class="distribution-row">
              <span class="distribution-name" :class="{ muted: row.resolution === '未记录' }">{{ row.resolution || '未记录' }}</span>
              <div class="bar-track">
                <div class="bar-fill warm" :style="{ width: `${barWidth(row.play_count, resolutionMax)}%` }"></div>
              </div>
              <span class="distribution-count">{{ row.play_count }}</span>
            </div>
          </div>
          <EmptyState v-else-if="showListEmpty(resolutions)" description="暂无分辨率数据" />
          <div class="panel-note">飞牛播放记录中没有记录分辨率时会归入“未记录”。</div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import EmptyState from '../components/EmptyState.vue'
import PlaybackHeatmap from '../components/PlaybackHeatmap.vue'
import {
  fetchReportMediaTypeDistribution,
  fetchReportOverview,
  fetchReportHourlyDistribution,
  fetchReportPlayTrend,
  fetchReportResolutionDistribution,
  fetchReportTopMedia,
  fetchReportTopUsers,
  fetchFavorites,
  type FavoriteItem,
  type HourlyDistributionItem,
  type MediaTypeDistributionItem,
  type PlayTrendItem,
  type ReportOverview,
  type ResolutionDistributionItem,
  type TopMediaReportItem,
  type TopUserReportItem
} from '../api/modules'
import { useAuthStore } from '../stores/auth'
import { useRouteRefresh } from '../utils/routeRefresh'
import { formatApplicationDateTime } from '../utils/applicationTime'
import { readSuccessfulData, writeSuccessfulData } from '../utils/successfulDataCache'

type RangeKey = '7' | '30' | '90' | 'all'

interface DetailState<T> {
  loading: boolean
  error: string
  hasLoaded: boolean
  lastUpdatedAt: number | null
  requestId: number
  data: T | null
}

interface ListState<T> {
  loading: boolean
  error: string
  hasLoaded: boolean
  lastUpdatedAt: number | null
  requestId: number
  items: T[]
}

const hourlyDays = ref<RangeKey>('30')
const topUsersDays = ref<RangeKey>('30')
const topMediaDays = ref<RangeKey>('7')
const resolutionDays = ref<RangeKey>('30')
const topMediaMode = ref<'episode' | 'series'>('episode')
const auth = useAuthStore()
const rangeOptions: Array<{ label: string; value: RangeKey }> = [
  { label: '7 天', value: '7' },
  { label: '30 天', value: '30' },
  { label: '90 天', value: '90' },
  { label: '全部', value: 'all' }
]
const REPORT_CACHE_PREFIX = 'fntv.reports.v2'

const overview = reactive<DetailState<ReportOverview>>(createDetailState<ReportOverview>())
const trend = reactive<ListState<PlayTrendItem>>(createListState<PlayTrendItem>())
const hourly = reactive<ListState<HourlyDistributionItem>>(createListState<HourlyDistributionItem>())
const topUsers = reactive<ListState<TopUserReportItem>>(createListState<TopUserReportItem>())
const topMedia = reactive<ListState<TopMediaReportItem>>(createListState<TopMediaReportItem>())
const mediaTypes = reactive<ListState<MediaTypeDistributionItem>>(createListState<MediaTypeDistributionItem>())
const resolutions = reactive<ListState<ResolutionDistributionItem>>(createListState<ResolutionDistributionItem>())
const favorites = reactive<ListState<FavoriteItem>>(createListState<FavoriteItem>())

const globalLoading = computed(() => overview.loading || trend.loading || hourly.loading || topUsers.loading || topMedia.loading || mediaTypes.loading || resolutions.loading || favorites.loading)
const allStates = computed(() => [overview, trend, hourly, topUsers, topMedia, mediaTypes, resolutions, favorites])
const hasAnyLoaded = computed(() => allStates.value.some((state) => state.hasLoaded))
const anyRefreshing = computed(() => allStates.value.some((state) => state.loading && state.hasLoaded))
const latestReportUpdatedAt = computed(() => {
  const latest = Math.max(...allStates.value.map((state) => state.lastUpdatedAt || 0))
  return latest > 0 ? formatClock(latest) : ''
})
const hourlyMax = computed(() => maxValue(hourly.items.map((item) => item.play_count)))
const mediaTypeMax = computed(() => maxValue(mediaTypes.items.map((item) => item.count)))
const resolutionMax = computed(() => maxValue(resolutions.items.map((item) => item.play_count)))

const overviewMetrics = computed(() => [
  { label: '总用户数', value: formatNumber(overview.data?.total_users) },
  { label: '总媒体数', value: formatNumber(overview.data?.total_media) },
  { label: '播放记录', value: formatNumber(overview.data?.total_play_records) },
  { label: '看完记录', value: formatNumber(overview.data?.watched_records) },
  { label: '7 天活跃用户', value: formatNumber(overview.data?.active_users_7d) },
  { label: '30 天活跃用户', value: formatNumber(overview.data?.active_users_30d) },
  { label: '7 天播放', value: formatNumber(overview.data?.plays_7d) },
  { label: '30 天播放', value: formatNumber(overview.data?.plays_30d) },
  { label: '总观看时长', value: formatDuration(overview.data?.total_watch_seconds) },
  { label: '平均进度', value: overview.data?.avg_progress_percent == null ? '-' : `${overview.data.avg_progress_percent}%` },
  { label: '生成时间', value: formatApplicationDateTime(overview.data?.generated_at) }
])

function createDetailState<T>(): DetailState<T> {
  return { loading: false, error: '', hasLoaded: false, lastUpdatedAt: null, requestId: 0, data: null }
}

function createListState<T>(): ListState<T> {
  return { loading: false, error: '', hasLoaded: false, lastUpdatedAt: null, requestId: 0, items: [] }
}

async function loadDetail<T>(state: DetailState<T>, loader: () => Promise<T>, key: string) {
  const requestId = state.requestId + 1
  state.requestId = requestId
  state.loading = true
  state.error = ''
  try {
    const data = await loader()
    if (state.requestId !== requestId) return
    state.data = data
    state.hasLoaded = true
    state.lastUpdatedAt = Date.now()
    writeSuccessfulData(key, data, state.lastUpdatedAt)
  } catch {
    if (state.requestId !== requestId) return
    state.error = state.hasLoaded ? '更新失败，仍显示上次成功数据' : '数据加载失败，请稍后重试'
  } finally {
    if (state.requestId === requestId) state.loading = false
  }
}

async function loadList<T>(state: ListState<T>, loader: () => Promise<T[]>, key: string) {
  const requestId = state.requestId + 1
  state.requestId = requestId
  state.loading = true
  state.error = ''
  try {
    const items = await loader()
    if (state.requestId !== requestId) return
    if (!Array.isArray(items)) {
      throw new Error('报表接口返回格式异常')
    }
    state.items = items
    state.hasLoaded = true
    state.lastUpdatedAt = Date.now()
    writeSuccessfulData(key, items, state.lastUpdatedAt)
  } catch {
    if (state.requestId !== requestId) return
    state.error = state.hasLoaded ? '更新失败，仍显示上次成功数据' : '数据加载失败，请稍后重试'
  } finally {
    if (state.requestId === requestId) state.loading = false
  }
}

function hasListItems<T>(state: ListState<T>): boolean {
  return Array.isArray(state.items) && state.items.length > 0
}

function showListEmpty<T>(state: ListState<T>): boolean {
  return !state.loading && !state.error && Array.isArray(state.items) && state.items.length === 0
}

function reportCacheKey(module: string, range?: RangeKey | '365', variant?: string): string {
  return [REPORT_CACHE_PREFIX, module, range, variant].filter(Boolean).join('.')
}

function restoreDetail<T>(state: DetailState<T>, key: string): void {
  const cached = readSuccessfulData<T>(key)
  if (!cached) return
  state.data = cached.data
  state.hasLoaded = true
  state.lastUpdatedAt = cached.updatedAt
}

function restoreList<T>(state: ListState<T>, key: string): boolean {
  const cached = readSuccessfulData<T[]>(key)
  if (!cached || !Array.isArray(cached.data)) return false
  state.items = cached.data
  state.hasLoaded = true
  state.lastUpdatedAt = cached.updatedAt
  return true
}

function activateListRange<T>(state: ListState<T>, key: string): void {
  if (restoreList(state, key)) return
  state.items = []
  state.hasLoaded = false
  state.lastUpdatedAt = null
  state.error = ''
}

async function loadTopMedia() {
  if (!(await ensureAuthReady())) return
  const key = reportCacheKey('topMedia', topMediaDays.value, topMediaMode.value)
  activateListRange(topMedia, key)
  await loadList(
    topMedia,
    () => fetchReportTopMedia({ days: topMediaDays.value, limit: 10, mode: topMediaMode.value }),
    key
  )
}

async function loadHourly() {
  if (!(await ensureAuthReady())) return
  const key = reportCacheKey('hourly', hourlyDays.value)
  activateListRange(hourly, key)
  await loadList(hourly, () => fetchReportHourlyDistribution(hourlyDays.value), key)
}

async function loadTopUsers() {
  if (!(await ensureAuthReady())) return
  const key = reportCacheKey('topUsers', topUsersDays.value)
  activateListRange(topUsers, key)
  await loadList(topUsers, () => fetchReportTopUsers({ days: topUsersDays.value, limit: 10 }), key)
}

async function loadResolutions() {
  if (!(await ensureAuthReady())) return
  const key = reportCacheKey('resolutions', resolutionDays.value)
  activateListRange(resolutions, key)
  await loadList(resolutions, () => fetchReportResolutionDistribution(resolutionDays.value), key)
}

async function loadAll() {
  if (!(await ensureAuthReady())) return
  await Promise.all([
    loadDetail(overview, fetchReportOverview, reportCacheKey('overview')),
    loadList(trend, () => fetchReportPlayTrend(365), reportCacheKey('trend', '365')),
    loadHourly(),
    loadTopUsers(),
    loadTopMedia(),
    loadResolutions(),
    loadList(mediaTypes, fetchReportMediaTypeDistribution, reportCacheKey('mediaTypes')),
    loadList(favorites, async () => (await fetchFavorites({ page: 1, page_size: 10 })).items, reportCacheKey('favorites'))
  ])
}

async function ensureAuthReady(): Promise<boolean> {
  if (!auth.isAuthenticated) return false
  if (!auth.user) {
    try {
      await auth.loadMe()
    } catch {
      return false
    }
  }
  return true
}

function formatNumber(value: number | null | undefined): string {
  return value == null ? '-' : value.toLocaleString()
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '-'
  const total = Math.max(0, Math.floor(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function formatClock(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function maxValue(values: number[]): number {
  return values.reduce((max, value) => Math.max(max, value), 0)
}

function barWidth(value: number, max: number): number {
  if (max <= 0 || value <= 0) return 0
  return Math.max(8, Math.round((value / max) * 100))
}

function initialLoading(state: { loading: boolean; hasLoaded: boolean }): boolean {
  return state.loading && !state.hasLoaded
}

function panelStatus(state: { loading: boolean; hasLoaded: boolean; lastUpdatedAt: number | null }): string {
  if (state.loading && state.hasLoaded) return '正在更新...'
  if (state.lastUpdatedAt) return `最后更新：${formatClock(state.lastUpdatedAt)}`
  return ''
}

function restoreReportsCache(): void {
  restoreDetail(overview, reportCacheKey('overview'))
  restoreList(trend, reportCacheKey('trend', '365'))
  restoreList(hourly, reportCacheKey('hourly', hourlyDays.value))
  restoreList(topUsers, reportCacheKey('topUsers', topUsersDays.value))
  restoreList(topMedia, reportCacheKey('topMedia', topMediaDays.value, topMediaMode.value))
  restoreList(resolutions, reportCacheKey('resolutions', resolutionDays.value))
  restoreList(mediaTypes, reportCacheKey('mediaTypes'))
  restoreList(favorites, reportCacheKey('favorites'))
}

restoreReportsCache()
onMounted(loadAll)
useRouteRefresh(loadAll)
</script>

<style scoped>
.reports-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  gap: 14px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.refresh-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  color: var(--app-muted);
  font-size: 12px;
  text-align: right;
}

.panel-body {
  min-height: 160px;
  padding: 14px 16px;
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-heading-meta,
.panel-controls {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  color: var(--app-muted);
  font-size: 12px;
  font-weight: 400;
}

.period-select { width: 88px; }

.panel-note {
  margin-bottom: 10px;
  color: var(--app-muted);
  font-size: 12px;
  line-height: 1.5;
}

.report-content-stack {
  display: grid;
  gap: 10px;
}

.report-content-stack .panel-note {
  margin-bottom: 0;
}

.panel-state,
.panel-status-row {
  color: var(--app-muted);
  font-size: 12px;
  font-weight: 400;
}

.panel-status-row {
  display: flex;
  justify-content: flex-end;
  min-height: 18px;
}

.inline-error {
  padding: 10px 12px;
  border: 1px solid var(--app-error-border);
  border-radius: 8px;
  background: var(--app-error-bg);
  color: var(--app-error-text);
}

.inline-warning,
.inline-updating {
  margin-bottom: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.inline-warning {
  border: 1px solid var(--app-warning-border);
  background: var(--app-warning-bg);
  color: var(--app-warning-text);
}

.inline-updating {
  border: 1px solid var(--app-updating-border);
  background: var(--app-updating-bg);
  color: var(--app-updating-text);
}

.distribution-row {
  display: grid;
  grid-template-columns: 120px minmax(90px, 1fr) 56px;
  align-items: center;
  gap: 10px;
  min-height: 30px;
}

.distribution-name,
.distribution-count {
  color: var(--app-text);
  font-size: 13px;
}

.distribution-count {
  text-align: right;
}

.distribution-name.muted {
  color: var(--app-muted);
}

.bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--app-bar-track);
}

.bar-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--app-accent);
}

.bar-fill.alt {
  background: var(--app-success);
}

.bar-fill.warm {
  background: var(--app-data-3);
}

@media (max-width: 900px) {
  .reports-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .header-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .refresh-meta {
    text-align: left;
  }

  .distribution-row {
    grid-template-columns: 1fr 1fr 44px;
  }

  .panel-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .panel-controls,
  .panel-heading-meta {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }
}
</style>
