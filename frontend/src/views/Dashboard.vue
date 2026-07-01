<template>
  <section class="dashboard-monitor-page">
    <div class="monitor-shell">
      <header class="monitor-topbar">
        <div class="monitor-brand">
          <span class="brand-dot"></span>
          <div>
            <h1>fntv-admin 影视监控</h1>
            <p>飞牛影视数据概览和轻监控面板</p>
          </div>
        </div>
        <div class="monitor-actions">
          <span class="clock">{{ currentClock }}</span>
          <el-switch v-model="darkMode" inline-prompt active-text="暗" inactive-text="亮" />
          <el-button round :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
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

      <section class="monitor-grid two-columns">
        <article class="glass-card monitor-card active-card">
          <PanelHead title="最近活跃观看" note="根据最近 5 分钟播放记录推断，非实时会话。" />
          <div class="card-body">
            <InlineError v-if="sectionErrors.active" :message="sectionErrors.active" />
            <div v-if="activeWatches.length" class="watch-list">
              <div v-for="item in activeWatches" :key="item.id || `${item.user_guid}-${item.item_guid}-${item.last_updated_at}`" class="glass-list-item watch-item">
                <div class="item-main">
                  <strong>{{ item.display_title || item.title || '-' }}</strong>
                  <span>{{ item.username || item.user || '-' }} · {{ item.progress || '进度未知' }}</span>
                </div>
                <span class="time-chip">{{ item.last_updated_at || item.played_at || '-' }}</span>
              </div>
            </div>
            <EmptyState v-else description="暂无最近活跃观看" />
          </div>
        </article>

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
import { computed, defineComponent, h, onMounted, onUnmounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import {
  fetchActiveWatches,
  fetchDashboardOverview,
  fetchDownloads,
  fetchFavorites,
  fetchRecentActivities,
  fetchReportHourlyDistribution,
  fetchReportOverview,
  fetchReportTopMedia,
  type ActiveWatchItem,
  type DashboardOverview,
  type DownloadItem,
  type FavoriteItem,
  type HistoryItem,
  type HourlyDistributionItem,
  type ReportOverview,
  type TopMediaReportItem
} from '../api/modules'
import EmptyState from '../components/EmptyState.vue'
import { useThemeStore } from '../stores/theme'
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

const theme = useThemeStore()
const overview = ref<DashboardOverview | null>(null)
const reportOverview = ref<ReportOverview | null>(null)
const activities = ref<HistoryItem[]>([])
const activeWatches = ref<ActiveWatchItem[]>([])
const hourlyItems = ref<HourlyDistributionItem[]>([])
const topMediaItems = ref<TopMediaReportItem[]>([])
const favoriteItems = ref<FavoriteItem[]>([])
const downloadItems = ref<DownloadItem[]>([])
const currentTime = ref(new Date())
const loading = ref(false)
let clockTimer: number | undefined

const sectionErrors = reactive({
  overview: '',
  active: '',
  history: '',
  hourly: '',
  topMedia: '',
  favorites: '',
  downloads: ''
})

const darkMode = computed({
  get: () => theme.resolved === 'dark',
  set: (enabled: boolean) => theme.setMode(enabled ? 'dark' : 'light')
})

const currentClock = computed(() => currentTime.value.toLocaleTimeString('zh-CN', { hour12: false }))

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
    const [dashboard, report, active, recent, hourly, topMedia, favorites, downloads] = await Promise.allSettled([
      fetchDashboardOverview(),
      fetchReportOverview(),
      fetchActiveWatches(300),
      fetchRecentActivities(30),
      fetchReportHourlyDistribution(30),
      fetchReportTopMedia({ days: '7', limit: 10, mode: 'series' }),
      fetchFavorites({ page: 1, page_size: 5 }),
      fetchDownloads({ page: 1, page_size: 5 })
    ])

    if (dashboard.status === 'fulfilled') overview.value = dashboard.value
    else sectionErrors.overview = errorMessage(dashboard.reason, '仪表盘概览加载失败')

    if (report.status === 'fulfilled') reportOverview.value = report.value
    else sectionErrors.overview = sectionErrors.overview || errorMessage(report.reason, '报表概览加载失败')

    if (active.status === 'fulfilled') activeWatches.value = active.value
    else sectionErrors.active = errorMessage(active.reason, '最近活跃观看加载失败')

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
  theme.init()
  clockTimer = window.setInterval(() => {
    currentTime.value = new Date()
  }, 1000)
  loadData()
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
})

useRouteRefresh(loadData)
</script>

<style scoped>
.dashboard-monitor-page {
  --monitor-ink: #1c2940;
  --monitor-muted: #6a7484;
  --monitor-accent: #2f7bff;
  --monitor-glass: rgba(255, 255, 255, 0.72);
  --monitor-glass-strong: rgba(255, 255, 255, 0.84);
  --monitor-border: rgba(255, 255, 255, 0.58);
  --monitor-shadow: 0 18px 36px rgba(65, 105, 155, 0.18);
  min-height: calc(100vh - 102px);
  margin: -22px;
  padding: 28px 22px 34px;
  color: var(--monitor-ink);
  background:
    radial-gradient(circle at 12% 8%, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0) 32%),
    linear-gradient(180deg, #cfe2ff 0%, #e7f1ff 52%, #ffffff 100%);
}

.monitor-shell {
  display: grid;
  gap: 16px;
  width: min(1220px, 100%);
  margin: 0 auto;
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

.monitor-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.brand-dot {
  width: 12px;
  height: 12px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--monitor-accent);
  box-shadow: 0 0 0 7px rgba(47, 123, 255, 0.16);
}

.monitor-brand h1 {
  margin: 0;
  color: var(--monitor-ink);
  font-size: 22px;
  font-weight: 760;
  letter-spacing: 0;
}

.monitor-brand p {
  margin: 5px 0 0;
  color: var(--monitor-muted);
  font-size: 13px;
}

.monitor-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.clock {
  color: var(--monitor-muted);
  font-variant-numeric: tabular-nums;
}

.glass-card,
.monitor-actions :deep(.el-button) {
  border: 1px solid var(--monitor-border);
  background:
    linear-gradient(180deg, var(--monitor-glass-strong), rgba(255, 255, 255, 0.22)),
    var(--monitor-glass);
  box-shadow: var(--monitor-shadow);
  backdrop-filter: blur(24px) saturate(170%);
  -webkit-backdrop-filter: blur(24px) saturate(170%);
}

.glass-card {
  overflow: hidden;
  border-radius: 18px;
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

.active-card {
  min-height: 260px;
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

.watch-list,
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
  border: 1px solid rgba(255, 255, 255, 0.62);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.48), rgba(255, 255, 255, 0.2));
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

.time-chip {
  flex: 0 0 auto;
  max-width: 148px;
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

.hour-count {
  text-align: right;
}

.hour-track,
.mini-progress {
  display: block;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.42);
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
  border-bottom: 1px solid rgba(255, 255, 255, 0.28);
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
  --monitor-ink: #edf4ff;
  --monitor-muted: #a7b2c2;
  --monitor-accent: #72a8ff;
  --monitor-glass: rgba(22, 28, 38, 0.74);
  --monitor-glass-strong: rgba(38, 48, 64, 0.78);
  --monitor-border: rgba(255, 255, 255, 0.18);
  --monitor-shadow: 0 22px 44px rgba(0, 0, 0, 0.46);
  background:
    radial-gradient(circle at 14% 8%, rgba(85, 137, 220, 0.28), rgba(255, 255, 255, 0) 34%),
    linear-gradient(180deg, #122a5c 0%, #0b1426 58%, #06090f 100%);
}

:global([data-theme='dark']) .glass-list-item {
  border-color: rgba(255, 255, 255, 0.14);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.04));
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
  .dashboard-monitor-page {
    margin: -22px -14px;
    padding: 20px 12px 28px;
  }

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
