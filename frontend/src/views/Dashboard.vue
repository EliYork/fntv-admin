<template>
  <section class="dashboard-monitor-page">
    <div class="monitor-shell">
      <header class="page-header monitor-topbar">
        <div>
          <h1 class="page-title">仪表盘</h1>
          <p class="page-subtitle">飞牛影视数据概览和近期播放活动</p>
        </div>
        <div class="monitor-actions">
          <span v-if="lastUpdatedAt" class="updated-at">更新于 {{ lastUpdatedAt }}</span>
          <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
        </div>
      </header>

      <div v-if="overview?.error" class="monitor-error">{{ overview.error }}</div>
      <div v-if="sectionErrors.overview" class="monitor-error">{{ sectionErrors.overview }}</div>

      <section class="monitor-stats">
        <article v-for="item in metricCards" :key="item.label" class="glass-card stat-card">
          <span class="stat-accent"></span>
          <span class="stat-label">{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <span class="stat-note">{{ item.note }}</span>
        </article>
      </section>

      <section class="monitor-grid">
        <article class="glass-card monitor-card trend-card">
          <PanelHead title="播放趋势" note="最近一年播放活跃度，颜色越深播放越多。" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.trend" :message="sectionErrors.trend" />
            <PlaybackHeatmap v-if="trendItems.length" :date-items="trendItems" :modes="['date']" />
            <EmptyState v-else description="暂无播放趋势数据" />
          </div>
        </article>
      </section>

      <section class="monitor-grid two-columns">
        <article class="glass-card monitor-card">
          <PanelHead title="播放时段" note="按最近 30 天播放记录聚合，使用本地时区。" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.hourly" :message="sectionErrors.hourly" />
            <div v-if="hourlyItems.length" class="hour-bars">
              <div v-for="item in hourlyItems" :key="item.hour" class="hour-bar-row">
                <span class="hour-label">{{ item.label }}</span>
                <div class="hour-track">
                  <span :style="{ width: `${barWidth(item.play_count, hourlyMax)}%` }"></span>
                </div>
                <span class="hour-count">{{ item.play_count }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无播放时段数据" />
          </div>
        </article>

        <article class="glass-card monitor-card">
          <PanelHead title="媒体类型分布" note="媒体类型统计" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.mediaTypes" :message="sectionErrors.mediaTypes" />
            <div v-if="mediaTypeItems.length" class="hour-bars">
              <div v-for="row in mediaTypeItems" :key="row.type" class="hour-bar-row">
                <span class="hour-label">{{ row.type || '未知' }}</span>
                <div class="hour-track">
                  <span :style="{ width: `${barWidth(row.count, mediaTypeMax)}%` }"></span>
                </div>
                <span class="hour-count">{{ row.count }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无媒体类型数据" />
          </div>
        </article>
      </section>

      <section class="monitor-grid two-columns">
        <article class="glass-card monitor-card">
          <PanelHead title="活跃用户榜" note="最近 30 天播放排行" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.topUsers" :message="sectionErrors.topUsers" />
            <div v-if="topUserItems.length" class="rank-list">
              <div v-for="(item, index) in topUserItems" :key="item.user_guid || item.username" class="glass-list-item rank-item">
                <div class="rank-title">
                  <strong>{{ index + 1 }}. {{ item.username || item.user_guid || '-' }}</strong>
                  <span>播放 {{ item.play_count }} 次 · 看完 {{ item.watched_count }} 次</span>
                </div>
              </div>
            </div>
            <EmptyState v-else description="暂无活跃用户数据" />
          </div>
        </article>

        <article class="glass-card monitor-card">
          <PanelHead title="分辨率分布" note="最近 30 天播放记录" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.resolutions" :message="sectionErrors.resolutions" />
            <div v-if="resolutionItems.length" class="hour-bars">
              <div v-for="row in resolutionItems" :key="row.resolution" class="hour-bar-row">
                <span class="hour-label" :class="{ 'muted-label': row.resolution === '未记录' }">{{ row.resolution || '未记录' }}</span>
                <div class="hour-track">
                  <span :style="{ width: `${barWidth(row.play_count, resolutionMax)}%` }"></span>
                </div>
                <span class="hour-count">{{ row.play_count }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无分辨率数据" />
          </div>
        </article>
      </section>

      <section class="monitor-grid two-columns">
        <article class="glass-card monitor-card history-card">
          <PanelHead title="观看历史" note="最近播放记录简版" />
          <div class="card-body scroll-panel">
            <InlineError v-if="sectionErrors.history" :message="sectionErrors.history" />
            <div v-if="activities.length" class="history-table">
              <div class="history-row header-row">
                <span>用户</span>
                <span>内容</span>
                <span>类型</span>
                <span>进度</span>
                <span>时间</span>
              </div>
              <div v-for="item in activities" :key="item.id || `${item.user_guid}-${item.item_guid}-${item.played_at}`" class="history-row">
                <span class="text-ellipsis">{{ item.username || item.user || '-' }}</span>
                <span class="text-ellipsis title-cell" :title="item.display_title || item.title">{{ item.display_title || item.title || '-' }}</span>
                <span><em class="type-tag">{{ historyType(item) }}</em></span>
                <span>
                  <i class="mini-progress"><b :style="{ width: `${progressWidth(item)}%` }"></b></i>
                </span>
                <span class="muted text-ellipsis">{{ item.played_at || item.started_at || '-' }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无播放活动或未识别播放记录表" />
          </div>
        </article>

        <article class="glass-card monitor-card">
          <PanelHead title="热门内容" note="最近 7 天热门内容" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.topMedia" :message="sectionErrors.topMedia" />
            <div v-if="topMediaItems.length" class="rank-list">
              <div v-for="(item, index) in topMediaItems" :key="item.item_guid || item.title" class="glass-list-item rank-item">
                <div class="rank-title">
                  <strong>{{ index + 1 }}. {{ item.title || item.item_guid || '-' }}</strong>
                  <span>{{ item.parent_title || '近7天播放' }}</span>
                </div>
                <span class="count-badge">{{ item.play_count }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无热门内容数据" />
          </div>
        </article>
      </section>

      <section class="monitor-grid two-columns">
        <article class="glass-card monitor-card">
          <PanelHead title="收藏记录" note="最近收藏媒体" />
          <div class="card-body compact-list">
            <InlineError v-if="sectionErrors.favorites" :message="sectionErrors.favorites" />
            <div v-if="favoriteItems.length" class="simple-list">
              <div v-for="item in favoriteItems" :key="`${item.user_guid}-${item.item_guid}-${item.favorite_time}`" class="glass-list-item">
                <div class="item-main">
                  <strong>{{ item.title || item.item_guid || '-' }}</strong>
                  <span>{{ item.username || item.user_guid || '-' }} · {{ item.media_type || '未知' }}</span>
                </div>
                <span class="muted">{{ item.favorite_time || '-' }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无收藏" />
          </div>
        </article>

        <article class="glass-card monitor-card">
          <PanelHead title="下载记录" note="最近下载任务" />
          <div class="card-body compact-list">
            <InlineError v-if="sectionErrors.downloads" :message="sectionErrors.downloads" />
            <div v-if="downloadItems.length" class="simple-list">
              <div v-for="item in downloadItems" :key="`${item.user_guid}-${item.media_file}-${item.create_time}`" class="glass-list-item">
                <div class="item-main">
                  <strong>{{ item.media_file || item.output_file || '-' }}</strong>
                  <span>{{ item.username || item.user_guid || '-' }} · {{ item.resolution || item.status_text || '未知' }}</span>
                </div>
                <span class="muted">{{ item.update_time || item.create_time || '-' }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无下载" />
          </div>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import {
  fetchDashboardOverview,
  fetchDownloads,
  fetchFavorites,
  fetchRecentActivities,
  fetchReportHourlyDistribution,
  fetchReportMediaTypeDistribution,
  fetchReportOverview,
  fetchReportPlayTrend,
  fetchReportResolutionDistribution,
  fetchReportTopMedia,
  fetchReportTopUsers,
  type DashboardOverview,
  type DownloadItem,
  type FavoriteItem,
  type HistoryItem,
  type HourlyDistributionItem,
  type MediaTypeDistributionItem,
  type PlayTrendItem,
  type ReportOverview,
  type ResolutionDistributionItem,
  type TopMediaReportItem,
  type TopUserReportItem
} from '../api/modules'
import EmptyState from '../components/EmptyState.vue'
import PlaybackHeatmap from '../components/PlaybackHeatmap.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const PanelHead = defineComponent({
  props: {
    title: { type: String, required: true },
    note: { type: String, default: '' }
  },
  setup(props) {
    return () =>
      h('div', { class: 'panel-head' }, [
        h('strong', props.title),
        props.note ? h('span', props.note) : null
      ])
  }
})

const InlineError = defineComponent({
  props: {
    message: { type: String, required: true }
  },
  setup(props) {
    return () => h('div', { class: 'inline-error' }, props.message)
  }
})

const overview = ref<DashboardOverview | null>(null)
const reportOverview = ref<ReportOverview | null>(null)
const activities = ref<HistoryItem[]>([])
const hourlyItems = ref<HourlyDistributionItem[]>([])
const topMediaItems = ref<TopMediaReportItem[]>([])
const favoriteItems = ref<FavoriteItem[]>([])
const downloadItems = ref<DownloadItem[]>([])
const trendItems = ref<PlayTrendItem[]>([])
const mediaTypeItems = ref<MediaTypeDistributionItem[]>([])
const topUserItems = ref<TopUserReportItem[]>([])
const resolutionItems = ref<ResolutionDistributionItem[]>([])
const lastUpdatedAt = ref('')
const loading = ref(false)

const sectionErrors = reactive({
  overview: '',
  history: '',
  hourly: '',
  topMedia: '',
  favorites: '',
  downloads: '',
  trend: '',
  mediaTypes: '',
  topUsers: '',
  resolutions: ''
})

const metricCards = computed(() => [
  {
    label: '总用户数',
    value: formatNumber(reportOverview.value?.total_users ?? overview.value?.total_users),
    note: '飞牛用户'
  },
  {
    label: '活跃用户',
    value: formatNumber(reportOverview.value?.active_users_7d),
    note: '最近 7 天'
  },
  {
    label: '今日播放',
    value: formatNumber(overview.value?.today_plays),
    note: '本地日期'
  },
  {
    label: '播放记录',
    value: formatNumber(reportOverview.value?.total_play_records ?? overview.value?.total_play_records),
    note: '累计只读统计'
  }
])

async function loadData() {
  loading.value = true
  clearErrors()
  try {
    const [dashboard, report, recent, hourly, topMedia, favorites, downloads, trend, mediaTypes, topUsers, resolutions] = await Promise.allSettled([
      fetchDashboardOverview(),
      fetchReportOverview(),
      fetchRecentActivities(30),
      fetchReportHourlyDistribution(30),
      fetchReportTopMedia({ days: '7', limit: 10, mode: 'series' }),
      fetchFavorites({ page: 1, page_size: 5 }),
      fetchDownloads({ page: 1, page_size: 5 }),
      fetchReportPlayTrend(365),
      fetchReportMediaTypeDistribution(),
      fetchReportTopUsers({ days: '30', limit: 5 }),
      fetchReportResolutionDistribution('30')
    ])

    if (dashboard.status === 'fulfilled') overview.value = dashboard.value
    else sectionErrors.overview = errorMessage(dashboard.reason, '仪表盘概览加载失败')

    if (report.status === 'fulfilled') reportOverview.value = report.value
    else sectionErrors.overview = sectionErrors.overview || errorMessage(report.reason, '报表概览加载失败')

    if (trend.status === 'fulfilled') trendItems.value = trend.value
    else sectionErrors.trend = errorMessage(trend.reason, '播放趋势加载失败')

    if (mediaTypes.status === 'fulfilled') mediaTypeItems.value = mediaTypes.value
    else sectionErrors.mediaTypes = errorMessage(mediaTypes.reason, '媒体类型分布加载失败')

    if (topUsers.status === 'fulfilled') topUserItems.value = topUsers.value
    else sectionErrors.topUsers = errorMessage(topUsers.reason, '活跃用户榜加载失败')

    if (resolutions.status === 'fulfilled') resolutionItems.value = resolutions.value
    else sectionErrors.resolutions = errorMessage(resolutions.reason, '分辨率分布加载失败')

    if (recent.status === 'fulfilled') activities.value = recent.value
    else sectionErrors.history = errorMessage(recent.reason, '观看历史加载失败')

    if (hourly.status === 'fulfilled') hourlyItems.value = hourly.value
    else sectionErrors.hourly = errorMessage(hourly.reason, '播放时段加载失败')

    if (topMedia.status === 'fulfilled') topMediaItems.value = topMedia.value
    else sectionErrors.topMedia = errorMessage(topMedia.reason, '热门内容加载失败')

    if (favorites.status === 'fulfilled') favoriteItems.value = favorites.value.items || []
    else sectionErrors.favorites = errorMessage(favorites.reason, '收藏记录加载失败')

    if (downloads.status === 'fulfilled') downloadItems.value = downloads.value.items || []
    else sectionErrors.downloads = errorMessage(downloads.reason, '下载记录加载失败')
    lastUpdatedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit' })
  } finally {
    loading.value = false
  }
}

function clearErrors() {
  for (const key of Object.keys(sectionErrors) as Array<keyof typeof sectionErrors>) {
    sectionErrors[key] = ''
  }
}

function formatNumber(value: number | null | undefined): string {
  return value == null ? '-' : value.toLocaleString('zh-CN')
}

function barWidth(value: number, max: number): number {
  if (max <= 0 || value <= 0) return 0
  return Math.max(6, Math.round((value / max) * 100))
}

const hourlyMax = computed(() => hourlyItems.value.reduce((max, item) => Math.max(max, item.play_count), 0))
const mediaTypeMax = computed(() => mediaTypeItems.value.reduce((max, item) => Math.max(max, item.count), 0))
const resolutionMax = computed(() => resolutionItems.value.reduce((max, item) => Math.max(max, item.play_count), 0))

function historyType(item: HistoryItem): string {
  return item.resolution || item.watched_text || '记录'
}

function progressWidth(item: HistoryItem): number {
  if (item.progress_percent != null) return Math.max(0, Math.min(100, item.progress_percent))
  if (item.watched) return 100
  return 0
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

onMounted(() => {
  loadData()
})

useRouteRefresh(loadData)
</script>

<style scoped>
.dashboard-monitor-page {
  --monitor-ink: var(--app-title);
  --monitor-muted: var(--app-muted);
  --monitor-accent: var(--app-accent);
  --monitor-border: var(--app-border);
  --monitor-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
  color: var(--monitor-ink);
}

.monitor-shell {
  display: grid;
  gap: 16px;
  width: 100%;
}

.monitor-topbar,
.monitor-stats,
.monitor-grid {
  min-width: 0;
}

.monitor-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.monitor-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.updated-at {
  color: var(--monitor-muted);
  font-variant-numeric: tabular-nums;
}

.glass-card,
.monitor-actions :deep(.el-button) {
  border: 1px solid var(--monitor-border);
  background: var(--app-surface);
  box-shadow: var(--monitor-shadow);
}

.glass-card {
  overflow: hidden;
  border-radius: 10px;
}

.monitor-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  display: grid;
  gap: 6px;
  min-height: 116px;
  padding: 18px;
}

.stat-accent {
  width: 30px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--monitor-accent), rgba(47, 123, 255, 0.18));
}

.stat-label,
.stat-note,
.muted {
  color: var(--monitor-muted);
}

.stat-label {
  font-size: 13px;
}

.stat-card strong {
  color: var(--monitor-ink);
  font-size: 28px;
  line-height: 1.1;
}

.stat-note {
  font-size: 12px;
}

.monitor-grid {
  display: grid;
  gap: 16px;
}

.two-columns {
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.95fr);
}

.monitor-card {
  min-height: 282px;
}

.trend-card {
  min-height: auto;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px 0;
}

.panel-head strong {
  color: var(--monitor-ink);
  font-size: 15px;
  font-weight: 720;
}

.panel-head span {
  color: var(--monitor-muted);
  font-size: 12px;
  text-align: right;
}

.card-body {
  padding: 16px 18px 18px;
}

.rank-list,
.simple-list {
  display: grid;
  gap: 10px;
}

.compact-list {
  min-height: 160px;
}

.glass-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 11px 12px;
  border: 1px solid var(--app-border-soft);
  border-radius: 8px;
  background: var(--app-surface-soft);
}

.item-main,
.rank-title {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.item-main strong,
.rank-title strong {
  overflow: hidden;
  color: var(--monitor-ink);
  font-size: 13px;
  font-style: normal;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-main span,
.rank-title span {
  overflow: hidden;
  color: var(--monitor-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hour-bars {
  display: grid;
  gap: 7px;
}

.hour-bar-row {
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr) 36px;
  align-items: center;
  gap: 10px;
  min-height: 20px;
}

.hour-label,
.hour-count {
  color: var(--monitor-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.muted-label {
  color: var(--monitor-muted);
}

.hour-count {
  text-align: right;
}

.hour-track,
.mini-progress {
  display: block;
  overflow: hidden;
  border-radius: 999px;
  background: var(--app-bar-track);
}

.hour-track {
  height: 9px;
}

.hour-track span,
.mini-progress b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6fb0ff, var(--monitor-accent));
}

.scroll-panel {
  max-height: 430px;
  overflow: auto;
}

.history-table {
  min-width: 560px;
}

.history-row {
  display: grid;
  grid-template-columns: minmax(70px, 0.8fr) minmax(150px, 1.9fr) 74px minmax(86px, 0.8fr) minmax(120px, 1fr);
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-bottom: 1px solid var(--app-border-soft);
  color: var(--monitor-ink);
  font-size: 13px;
}

.header-row {
  color: var(--monitor-muted);
  font-size: 12px;
  font-weight: 650;
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-cell {
  color: var(--monitor-ink);
  font-weight: 620;
}

.type-tag {
  display: inline-flex;
  max-width: 70px;
  overflow: hidden;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(47, 123, 255, 0.12);
  color: var(--monitor-accent);
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-progress {
  width: 100%;
  height: 6px;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  border-radius: 50%;
  color: #ffffff;
  font-size: 13px;
  font-weight: 760;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.55), rgba(255, 255, 255, 0) 45%),
    linear-gradient(135deg, #cfd6e2 0%, #99a5b8 58%, #7f899a 100%);
  box-shadow: inset 0 0 8px rgba(255, 255, 255, 0.3);
}

.inline-error,
.monitor-error {
  margin-bottom: 10px;
  padding: 9px 12px;
  border: 1px solid rgba(251, 191, 36, 0.45);
  border-radius: 12px;
  background: rgba(255, 247, 237, 0.72);
  color: #9a3412;
  font-size: 13px;
}

.monitor-error {
  margin-bottom: 0;
}

.dashboard-monitor-page :deep(.empty-panel) {
  padding: 28px 10px;
  color: var(--monitor-muted);
}

:global([data-theme='dark']) .dashboard-monitor-page {
  --monitor-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
}

:global([data-theme='dark']) .glass-list-item {
  border-color: var(--app-border-soft);
  background: var(--app-surface-soft);
}

:global([data-theme='dark']) .hour-track,
:global([data-theme='dark']) .mini-progress {
  background: rgba(255, 255, 255, 0.12);
}

:global([data-theme='dark']) .inline-error,
:global([data-theme='dark']) .monitor-error {
  border-color: rgba(251, 146, 60, 0.35);
  background: rgba(67, 39, 18, 0.58);
  color: #fdba74;
}

@media (max-width: 980px) {
  .monitor-stats,
  .two-columns {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .two-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .monitor-topbar,
  .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .monitor-actions {
    justify-content: flex-start;
  }

  .monitor-stats {
    grid-template-columns: 1fr;
  }

  .panel-head span {
    text-align: left;
  }

  .history-table {
    min-width: 520px;
  }
}
</style>
