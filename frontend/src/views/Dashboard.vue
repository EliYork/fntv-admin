<template>
  <section class="observatory-page">
    <h1 class="sr-only">飞牛影视数据中心</h1>
    <section class="metric-strip" aria-label="核心指标">
      <article v-for="metric in metricCards" :key="metric.label" class="metric-item">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.note }}</small>
      </article>
    </section>

    <section class="data-section trend-section" aria-labelledby="trend-title">
      <header class="section-heading">
        <h2 id="trend-title">播放趋势</h2>
        <span class="section-period">最近 1 年</span>
      </header>
      <PlaybackHeatmap v-if="trendItems.length" :date-items="trendItems" :modes="['date']" />
      <EmptyState v-else-if="!loading" description="暂无播放趋势数据" />
    </section>

    <section class="data-section" aria-labelledby="hourly-title">
      <header class="section-heading">
        <h2 id="hourly-title">播放时段</h2>
        <el-select v-model="hourlyRange" class="period-select" size="small" aria-label="播放时段统计周期" @change="loadHourly">
          <el-option v-for="option in rangeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
      </header>
      <div v-if="hasHourlyData" class="hourly-scroll">
        <div class="hourly-chart" role="img" :aria-label="`${periodLabel(hourlyRange)}各小时播放次数柱状图`">
          <AppTooltip v-for="item in normalizedHourlyItems" :key="item.hour" :content="`${hourLabel(item.hour)} · ${item.play_count} 次播放`" placement="top">
            <div class="hour-column" :aria-label="`${item.hour} 点播放 ${item.play_count} 次`">
              <div class="hour-bar-zone">
                <span class="hour-bar" :style="{ height: `${hourBarHeight(item.play_count)}%` }"></span>
              </div>
              <span class="hour-tick">{{ visibleHourTick(item.hour) }}</span>
            </div>
          </AppTooltip>
        </div>
      </div>
      <EmptyState v-else-if="!loading" description="暂无播放时段数据" />
    </section>

    <section class="rank-grid">
      <article class="rank-panel" aria-labelledby="media-rank-title">
        <header class="section-heading">
          <h2 id="media-rank-title">热门内容</h2>
          <el-select v-model="topMediaRange" class="period-select" size="small" aria-label="热门内容统计周期" @change="loadTopMedia">
            <el-option v-for="option in rangeOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </header>
        <ol v-if="topMediaItems.length" class="rank-list">
          <li v-for="(item, index) in topMediaItems" :key="item.item_guid || `${item.title}-${index}`">
            <span class="rank-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="rank-content">
              <strong>{{ item.title || item.item_guid || '未命名媒体' }}</strong>
              <small v-if="item.parent_title">{{ item.parent_title }}</small>
            </span>
            <span class="rank-value">{{ item.play_count }}<small>次</small></span>
          </li>
        </ol>
        <EmptyState v-else-if="!loading" description="暂无热门内容数据" />
      </article>

      <article class="rank-panel" aria-labelledby="user-rank-title">
        <header class="section-heading">
          <h2 id="user-rank-title">活跃用户</h2>
          <el-select v-model="topUsersRange" class="period-select" size="small" aria-label="活跃用户统计周期" @change="loadTopUsers">
            <el-option v-for="option in rangeOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </header>
        <ol v-if="topUserItems.length" class="rank-list">
          <li v-for="(item, index) in topUserItems" :key="item.user_guid || `${item.username}-${index}`">
            <span class="rank-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="rank-content">
              <strong>{{ item.username || item.user_guid || '未知用户' }}</strong>
              <small v-if="item.watch_seconds">{{ formatWatchDuration(item.watch_seconds) }}</small>
            </span>
            <span class="rank-value">{{ item.play_count }}<small>次</small></span>
          </li>
        </ol>
        <EmptyState v-else-if="!loading" description="暂无活跃用户数据" />
      </article>
    </section>

    <HistoryFeed ref="historyFeed" />
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchDashboardOverview,
  fetchReportHourlyDistribution,
  fetchReportOverview,
  fetchReportPlayTrend,
  fetchReportTopMedia,
  fetchReportTopUsers,
  type DashboardOverview,
  type HourlyDistributionItem,
  type PlayTrendItem,
  type ReportOverview,
  type TopMediaReportItem,
  type TopUserReportItem
} from '../api/modules'
import EmptyState from '../components/EmptyState.vue'
import AppTooltip from '../components/AppTooltip.vue'
import HistoryFeed from '../components/HistoryFeed.vue'
import PlaybackHeatmap from '../components/PlaybackHeatmap.vue'
import { useRouteRefresh } from '../utils/routeRefresh'
import { readSuccessfulData, writeSuccessfulData } from '../utils/successfulDataCache'

const CACHE_PREFIX = 'fntv.dashboard.v1'
const FRESHNESS_KEY = `${CACHE_PREFIX}.freshness`
type DashboardModule = 'overview' | 'report' | 'hourly' | 'topMedia' | 'topUsers' | 'trend'
const lastSuccessfulAt: Partial<Record<DashboardModule, number>> = {}

const overview = ref<DashboardOverview | null>(null)
const reportOverview = ref<ReportOverview | null>(null)
const hourlyItems = ref<HourlyDistributionItem[]>([])
const topMediaItems = ref<TopMediaReportItem[]>([])
const trendItems = ref<PlayTrendItem[]>([])
const topUserItems = ref<TopUserReportItem[]>([])
type PeriodRange = '7' | '30' | '90' | 'all'
const rangeOptions: Array<{ label: string; value: PeriodRange }> = [
  { label: '7 天', value: '7' },
  { label: '30 天', value: '30' },
  { label: '90 天', value: '90' },
  { label: '全部', value: 'all' }
]
const hourlyRange = ref<PeriodRange>('30')
const topMediaRange = ref<PeriodRange>('7')
const topUsersRange = ref<PeriodRange>('30')
const loading = ref(false)
const historyFeed = ref<InstanceType<typeof HistoryFeed> | null>(null)
let loadRequestVersion = 0
const moduleRequestVersions: Partial<Record<DashboardModule, number>> = {}

const metricCards = computed(() => [
  { label: '总用户', value: formatNumber(reportOverview.value?.total_users ?? overview.value?.total_users), note: '全部用户' },
  { label: '活跃用户', value: formatNumber(reportOverview.value?.active_users_7d), note: '最近 7 天' },
  { label: '今日播放', value: formatNumber(overview.value?.today_plays), note: '本地日期' },
  { label: '播放记录', value: formatNumber(reportOverview.value?.total_play_records ?? overview.value?.total_play_records), note: '累计记录' }
])

const normalizedHourlyItems = computed<HourlyDistributionItem[]>(() => {
  const byHour = new Map(hourlyItems.value.map((item) => [item.hour, item]))
  return Array.from({ length: 24 }, (_, hour) => byHour.get(hour) || { hour, label: hourLabel(hour), play_count: 0 })
})

const hourlyMax = computed(() => normalizedHourlyItems.value.reduce((max, item) => Math.max(max, item.play_count), 0))
const hasHourlyData = computed(() => normalizedHourlyItems.value.some((item) => item.play_count > 0))

async function loadData() {
  const requestVersion = ++loadRequestVersion
  const requestedHourlyRange = hourlyRange.value
  const requestedTopMediaRange = topMediaRange.value
  const requestedTopUsersRange = topUsersRange.value
  loading.value = true
  const [dashboard, report, hourly, topMedia, topUsers, trend] = await Promise.allSettled([
    fetchDashboardOverview(),
    fetchReportOverview(),
    fetchReportHourlyDistribution(requestedHourlyRange),
    fetchReportTopMedia({ days: requestedTopMediaRange, limit: 8, mode: 'series' }),
    fetchReportTopUsers({ days: requestedTopUsersRange, limit: 5 }),
    fetchReportPlayTrend(365)
  ])
  if (requestVersion !== loadRequestVersion) return
  const completedAt = Date.now()

  if (dashboard.status === 'fulfilled' && dashboard.value.database_ok && !dashboard.value.error) commitModule('overview', dashboard.value, (value) => { overview.value = value }, cacheKey('overview'), completedAt)
  if (report.status === 'fulfilled') commitModule('report', report.value, (value) => { reportOverview.value = value }, cacheKey('report'), completedAt)
  if (hourly.status === 'fulfilled' && hourlyRange.value === requestedHourlyRange) commitModule('hourly', hourly.value, (value) => { hourlyItems.value = value }, periodCacheKey('hourly', requestedHourlyRange), completedAt)
  if (topMedia.status === 'fulfilled' && topMediaRange.value === requestedTopMediaRange) commitModule('topMedia', topMedia.value, (value) => { topMediaItems.value = value }, periodCacheKey('topMedia', requestedTopMediaRange), completedAt)
  if (topUsers.status === 'fulfilled' && topUsersRange.value === requestedTopUsersRange) commitModule('topUsers', topUsers.value, (value) => { topUserItems.value = value }, periodCacheKey('topUsers', requestedTopUsersRange), completedAt)
  if (trend.status === 'fulfilled') commitModule('trend', trend.value, (value) => { trendItems.value = value }, trendCacheKey(), completedAt)
  loading.value = false
  publishFreshness()
}

async function loadPeriodModule<T extends unknown[]>(module: DashboardModule, cachePeriod: PeriodRange, loader: () => Promise<T>, assign: (value: T) => void) {
  const requestVersion = (moduleRequestVersions[module] || 0) + 1
  moduleRequestVersions[module] = requestVersion
  const key = periodCacheKey(module, cachePeriod)
  if (!restoreModule(module, assign, key)) assign([] as unknown as T)
  try {
    const value = await loader()
    if (moduleRequestVersions[module] !== requestVersion) return
    commitModule(module, value, assign, key)
    publishFreshness()
  } catch { /* keep the last successful result for this range */ }
}

function loadHourly() { return loadPeriodModule('hourly', hourlyRange.value, () => fetchReportHourlyDistribution(hourlyRange.value), (value) => { hourlyItems.value = value }) }
function loadTopMedia() { return loadPeriodModule('topMedia', topMediaRange.value, () => fetchReportTopMedia({ days: topMediaRange.value, limit: 8, mode: 'series' }), (value) => { topMediaItems.value = value }) }
function loadTopUsers() { return loadPeriodModule('topUsers', topUsersRange.value, () => fetchReportTopUsers({ days: topUsersRange.value, limit: 5 }), (value) => { topUserItems.value = value }) }

async function refreshPage() {
  await Promise.all([loadData(), historyFeed.value?.refresh()])
}

function formatNumber(value: number | null | undefined): string {
  return value == null ? '—' : value.toLocaleString('zh-CN')
}

function hourBarHeight(value: number): number {
  if (value <= 0 || hourlyMax.value <= 0) return 2
  return Math.max(8, Math.round((value / hourlyMax.value) * 100))
}

function hourLabel(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}

function visibleHourTick(hour: number): string {
  return [0, 3, 6, 9, 12, 15, 18, 21, 23].includes(hour) ? String(hour) : ''
}

function periodLabel(period: PeriodRange): string {
  return period === 'all' ? '全部时间' : `最近 ${rangeOptions.find((option) => option.value === period)?.label || period}`
}

function formatWatchDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟`
  return `${minutes} 分钟`
}

function cacheKey(module: DashboardModule): string {
  return `${CACHE_PREFIX}.${module}`
}

function trendCacheKey(): string {
  return `${cacheKey('trend')}.365`
}

function periodCacheKey(module: DashboardModule, period: PeriodRange): string {
  return `${cacheKey(module)}.${period}`
}

function commitModule<T>(module: DashboardModule, value: T, assign: (value: T) => void, key = cacheKey(module), updatedAt = Date.now()): void {
  assign(value)
  lastSuccessfulAt[module] = updatedAt
  writeSuccessfulData(key, value, updatedAt)
}

function restoreModule<T>(module: DashboardModule, assign: (value: T) => void, key = cacheKey(module)): boolean {
  const cached = readSuccessfulData<T>(key)
  if (!cached) return false
  assign(cached.data)
  lastSuccessfulAt[module] = cached.updatedAt
  return true
}

function restoreTrendCache(): void {
  const cached = readSuccessfulData<PlayTrendItem[]>(trendCacheKey())
  trendItems.value = cached?.data || []
  if (cached) lastSuccessfulAt.trend = cached.updatedAt
  else delete lastSuccessfulAt.trend
}

function restoreDashboardCache(): void {
  restoreModule<DashboardOverview>('overview', (value) => { overview.value = value })
  restoreModule<ReportOverview>('report', (value) => { reportOverview.value = value })
  restoreModule<HourlyDistributionItem[]>('hourly', (value) => { hourlyItems.value = value }, periodCacheKey('hourly', hourlyRange.value))
  restoreModule<TopMediaReportItem[]>('topMedia', (value) => { topMediaItems.value = value }, periodCacheKey('topMedia', topMediaRange.value))
  restoreModule<TopUserReportItem[]>('topUsers', (value) => { topUserItems.value = value }, periodCacheKey('topUsers', topUsersRange.value))
  restoreTrendCache()
  publishFreshness()
}

function publishFreshness(): void {
  const timestamps = Object.values(lastSuccessfulAt).filter((value): value is number => typeof value === 'number')
  if (!timestamps.length) return
  const updatedAt = Math.min(...timestamps)
  const detail = {
    updatedAt,
    applicationTimezone: overview.value?.application_timezone || 'Asia/Shanghai',
    partial: timestamps.length < 6 || Math.max(...timestamps) - Math.min(...timestamps) > 1000
  }
  writeSuccessfulData(FRESHNESS_KEY, detail, updatedAt)
  window.dispatchEvent(new CustomEvent('fntv-dashboard-freshness', { detail }))
}

restoreDashboardCache()
onMounted(loadData)
useRouteRefresh(refreshPage)
</script>

<style scoped>
.observatory-page { display: grid; gap: clamp(34px, 4vw, 58px); min-width: 0; color: var(--app-text); }
.metric-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-top: 1px solid var(--app-border); border-bottom: 1px solid var(--app-border); }

.metric-item {
  display: grid;
  align-content: center;
  min-height: 132px;
  padding: 22px clamp(16px, 2.2vw, 30px);
  border-right: 1px solid var(--app-border-soft);
}

.metric-item:last-child { border-right: 0; }
.metric-item span, .metric-item small { color: var(--app-muted); }
.metric-item span { font-size: 12px; font-weight: 620; letter-spacing: 0.04em; }
.metric-item strong { margin: 9px 0 7px; color: var(--app-title); font-size: clamp(30px, 3.3vw, 46px); font-weight: 620; letter-spacing: -0.045em; line-height: 1; font-variant-numeric: tabular-nums; }
.metric-item small { font-size: 11px; }
.data-section, .rank-panel { min-width: 0; }
.data-section { display: grid; gap: 20px; }
.section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 32px; }
.section-heading h2 { margin: 0; color: var(--app-title); font-size: clamp(17px, 1.5vw, 20px); font-weight: 660; letter-spacing: -0.015em; }
.section-period { color: var(--app-muted); font-size: 12px; }
.period-select { width: 88px; }
.trend-section { padding-top: 2px; }

.hourly-scroll { overflow-x: auto; overflow-y: hidden; padding: 3px 0 2px; }
.hourly-chart { display: grid; grid-template-columns: repeat(24, minmax(18px, 1fr)); gap: clamp(4px, 0.7vw, 11px); min-width: 620px; height: 132px; padding-top: 8px; }
.hour-column { display: grid; grid-template-rows: 104px 20px; gap: 7px; min-width: 0; cursor: default; }
.hour-bar-zone { display: flex; align-items: flex-end; justify-content: center; height: 104px; border-bottom: 1px solid var(--app-border); }
.hour-bar { width: min(70%, 18px); min-height: 2px; border-radius: 3px 3px 1px 1px; background: var(--app-accent); opacity: 0.82; transition: opacity 160ms ease; }
.hour-column:hover .hour-bar { opacity: 1; }
.hour-tick { color: var(--app-muted); font-size: 10px; line-height: 20px; text-align: center; font-variant-numeric: tabular-nums; }

.rank-grid { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.85fr); gap: clamp(34px, 5vw, 76px); }
.rank-panel { display: grid; align-content: start; gap: 15px; }
.rank-list { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--app-border-soft); }
.rank-list li { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: center; gap: 12px; min-height: 58px; padding: 8px 4px; border-bottom: 1px solid var(--app-border-soft); }
.rank-index { color: var(--app-muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.rank-content { display: grid; gap: 2px; min-width: 0; }
.rank-content strong { overflow: hidden; color: var(--app-title); font-size: 14px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.rank-content small { overflow: hidden; color: var(--app-muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.rank-value { color: var(--app-title); font-size: 16px; font-weight: 650; font-variant-numeric: tabular-nums; }
.rank-value small { margin-left: 3px; color: var(--app-muted); font-size: 10px; font-weight: 500; }
.observatory-page :deep(.empty-panel) { padding: 32px 12px; }

@media (max-width: 900px) {
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-item:nth-child(2) { border-right: 0; }
  .metric-item:nth-child(-n + 2) { border-bottom: 1px solid var(--app-border-soft); }
  .rank-grid { grid-template-columns: 1fr; gap: 38px; }
}

@media (max-width: 560px) {
  .observatory-page { gap: 38px; }
  .metric-item { min-height: 104px; padding: 17px 14px; }
  .metric-item strong { font-size: 30px; }
  .section-heading { align-items: flex-start; }
  .section-heading :deep(.el-radio-group) { flex-shrink: 0; }
  .section-heading :deep(.el-radio-button__inner) { padding-right: 9px; padding-left: 9px; }
}
</style>
