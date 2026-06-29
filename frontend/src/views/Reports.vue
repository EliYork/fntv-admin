<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">报表中心</h1>
        <p class="page-subtitle">只读统计飞牛影视数据，不修改飞牛数据库</p>
      </div>
      <el-button :icon="Refresh" :loading="globalLoading" @click="loadAll">刷新</el-button>
    </div>

    <div class="toolbar">
      <el-radio-group v-model="selectedDays" @change="loadRangeData">
        <el-radio-button v-for="item in rangeOptions" :key="item.value" :label="item.value">
          {{ item.label }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <div class="metrics section" v-loading="overview.loading">
      <div v-for="item in overviewMetrics" :key="item.label" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </div>
    </div>
    <div v-if="overview.error" class="error-panel section">{{ overview.error }}</div>

    <div class="reports-grid section">
      <div class="table-panel">
        <div class="panel-title">播放趋势</div>
        <div class="panel-body" v-loading="trend.loading">
          <div v-if="trend.error" class="inline-error">{{ trend.error }}</div>
          <template v-else-if="trend.items.length">
            <div class="heatmap-wrap">
              <div class="heatmap-grid" :style="{ '--heatmap-columns': String(heatmapColumns) }">
                <div
                  v-for="row in trend.items"
                  :key="row.date"
                  class="heatmap-cell"
                  :class="`level-${heatmapLevel(row.play_count)}`"
                  :title="`${row.date}：${row.play_count} 次播放`"
                ></div>
              </div>
              <div class="heatmap-summary">
                <span>{{ trend.items[0]?.date }} 至 {{ trend.items[trend.items.length - 1]?.date }}</span>
                <span>共 {{ trendTotal }} 次播放</span>
              </div>
            </div>
          </template>
          <EmptyState v-else description="暂无播放趋势数据" />
        </div>
      </div>

      <div class="table-panel">
        <div class="panel-title">媒体类型分布</div>
        <div class="panel-body" v-loading="mediaTypes.loading">
          <div v-if="mediaTypes.error" class="inline-error">{{ mediaTypes.error }}</div>
          <template v-else-if="mediaTypes.items.length">
            <div v-for="row in mediaTypes.items" :key="row.type" class="distribution-row">
              <span class="distribution-name">{{ row.type || '未知' }}</span>
              <div class="bar-track">
                <div class="bar-fill alt" :style="{ width: `${barWidth(row.count, mediaTypeMax)}%` }"></div>
              </div>
              <span class="distribution-count">{{ row.count }}</span>
            </div>
          </template>
          <EmptyState v-else description="暂无媒体类型数据" />
        </div>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title">活跃用户榜</div>
      <div class="panel-body" v-loading="topUsers.loading">
        <div v-if="topUsers.error" class="inline-error">{{ topUsers.error }}</div>
        <el-table v-else-if="topUsers.items.length" :data="topUsers.items">
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
          <el-table-column prop="last_played_at" label="最近播放" min-width="160" />
        </el-table>
        <EmptyState v-else description="暂无活跃用户数据" />
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>热门媒体榜</span>
        <el-radio-group v-model="topMediaMode" size="small" @change="loadTopMedia">
          <el-radio-button label="episode">单集</el-radio-button>
          <el-radio-button label="series">整部剧</el-radio-button>
        </el-radio-group>
      </div>
      <div class="panel-body" v-loading="topMedia.loading">
        <div v-if="topMedia.error" class="inline-error">{{ topMedia.error }}</div>
        <template v-else>
          <div class="panel-note">{{ topMediaMode === 'series' ? '按剧级别合并单集播放记录；没有父级的媒体按自身统计。' : '按单条媒体或单集播放记录统计。' }}</div>
          <el-table v-if="topMedia.items.length" :data="topMedia.items">
            <el-table-column label="媒体" min-width="260">
              <template #default="{ row }">
                <span>{{ row.title || row.item_guid || '-' }}</span>
                <div v-if="row.parent_title" class="muted-guid">{{ row.parent_title }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="play_count" label="播放" width="100" />
            <el-table-column prop="watched_count" label="看完" width="100" />
            <el-table-column prop="last_played_at" label="最近播放" min-width="160" />
          </el-table>
          <EmptyState v-else description="暂无热门媒体数据" />
        </template>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title">分辨率分布</div>
      <div class="panel-body" v-loading="resolutions.loading">
        <div v-if="resolutions.error" class="inline-error">{{ resolutions.error }}</div>
        <template v-else>
          <template v-if="resolutions.items.length">
            <div v-for="row in resolutions.items" :key="row.resolution" class="distribution-row">
              <span class="distribution-name" :class="{ muted: row.resolution === '未记录' }">{{ row.resolution || '未记录' }}</span>
              <div class="bar-track">
                <div class="bar-fill warm" :style="{ width: `${barWidth(row.play_count, resolutionMax)}%` }"></div>
              </div>
              <span class="distribution-count">{{ row.play_count }}</span>
            </div>
          </template>
          <EmptyState v-else description="暂无分辨率数据" />
          <div class="panel-note">飞牛播放记录中没有记录分辨率时会归入“未记录”。</div>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import EmptyState from '../components/EmptyState.vue'
import {
  fetchReportMediaTypeDistribution,
  fetchReportOverview,
  fetchReportPlayTrend,
  fetchReportResolutionDistribution,
  fetchReportTopMedia,
  fetchReportTopUsers,
  type MediaTypeDistributionItem,
  type PlayTrendItem,
  type ReportOverview,
  type ResolutionDistributionItem,
  type TopMediaReportItem,
  type TopUserReportItem
} from '../api/modules'
import { useAuthStore } from '../stores/auth'
import { useRouteRefresh } from '../utils/routeRefresh'

type RangeKey = '7' | '30' | '90' | 'all'

interface DetailState<T> {
  loading: boolean
  error: string
  data: T | null
}

interface ListState<T> {
  loading: boolean
  error: string
  items: T[]
}

const selectedDays = ref<RangeKey>('30')
const topMediaMode = ref<'episode' | 'series'>('episode')
const auth = useAuthStore()
const rangeOptions: Array<{ label: string; value: RangeKey }> = [
  { label: '7 天', value: '7' },
  { label: '30 天', value: '30' },
  { label: '90 天', value: '90' },
  { label: '全部', value: 'all' }
]

const overview = reactive<DetailState<ReportOverview>>({ loading: false, error: '', data: null })
const trend = reactive<ListState<PlayTrendItem>>({ loading: false, error: '', items: [] })
const topUsers = reactive<ListState<TopUserReportItem>>({ loading: false, error: '', items: [] })
const topMedia = reactive<ListState<TopMediaReportItem>>({ loading: false, error: '', items: [] })
const mediaTypes = reactive<ListState<MediaTypeDistributionItem>>({ loading: false, error: '', items: [] })
const resolutions = reactive<ListState<ResolutionDistributionItem>>({ loading: false, error: '', items: [] })

const globalLoading = computed(() => overview.loading || trend.loading || topUsers.loading || topMedia.loading || mediaTypes.loading || resolutions.loading)
const trendMax = computed(() => maxValue(trend.items.map((item) => item.play_count)))
const trendTotal = computed(() => trend.items.reduce((total, item) => total + item.play_count, 0))
const heatmapColumns = computed(() => Math.max(1, Math.ceil(trend.items.length / 7)))
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
  { label: '生成时间', value: overview.data?.generated_at || '-' }
])

async function loadDetail<T>(state: DetailState<T>, loader: () => Promise<T>) {
  state.loading = true
  state.error = ''
  try {
    state.data = await loader()
  } catch (error) {
    state.error = errorMessage(error)
    state.data = null
  } finally {
    state.loading = false
  }
}

async function loadList<T>(state: ListState<T>, loader: () => Promise<T[]>) {
  state.loading = true
  state.error = ''
  try {
    state.items = await loader()
  } catch (error) {
    state.error = errorMessage(error)
    state.items = []
  } finally {
    state.loading = false
  }
}

function trendDays(): number | string {
  return selectedDays.value === 'all' ? 'all' : Number(selectedDays.value)
}

async function loadRangeData() {
  if (!(await ensureAuthReady())) return
  await Promise.all([
    loadList(trend, () => fetchReportPlayTrend(trendDays())),
    loadList(topUsers, () => fetchReportTopUsers({ days: selectedDays.value, limit: 10 })),
    loadTopMedia(),
    loadList(resolutions, () => fetchReportResolutionDistribution(selectedDays.value))
  ])
}

async function loadTopMedia() {
  if (!(await ensureAuthReady())) return
  await loadList(topMedia, () => fetchReportTopMedia({ days: selectedDays.value, limit: 10, mode: topMediaMode.value }))
}

async function loadAll() {
  if (!(await ensureAuthReady())) return
  await Promise.all([
    loadDetail(overview, fetchReportOverview),
    loadRangeData(),
    loadList(mediaTypes, fetchReportMediaTypeDistribution)
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

function maxValue(values: number[]): number {
  return values.reduce((max, value) => Math.max(max, value), 0)
}

function barWidth(value: number, max: number): number {
  if (max <= 0 || value <= 0) return 0
  return Math.max(8, Math.round((value / max) * 100))
}

function heatmapLevel(value: number): number {
  if (value <= 0 || trendMax.value <= 0) return 0
  const ratio = value / trendMax.value
  if (ratio >= 0.75) return 4
  if (ratio >= 0.5) return 3
  if (ratio >= 0.25) return 2
  return 1
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return '报表数据加载失败'
}

onMounted(loadAll)
useRouteRefresh(loadAll)
</script>

<style scoped>
.reports-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  gap: 14px;
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

.panel-note {
  margin-bottom: 10px;
  color: var(--app-muted);
  font-size: 12px;
  line-height: 1.5;
}

.inline-error {
  padding: 10px 12px;
  border: 1px solid #f5c2c7;
  border-radius: 8px;
  background: #fff1f2;
  color: #b42318;
}

.distribution-row {
  display: grid;
  grid-template-columns: 120px minmax(90px, 1fr) 56px;
  align-items: center;
  gap: 10px;
  min-height: 30px;
}

.heatmap-wrap {
  display: grid;
  gap: 10px;
  overflow-x: auto;
}

.heatmap-grid {
  --heatmap-columns: 5;
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 12px);
  grid-template-columns: repeat(var(--heatmap-columns), 12px);
  gap: 4px;
  align-items: center;
  width: max-content;
  min-width: 100%;
}

.heatmap-cell {
  width: 12px;
  height: 12px;
  border: 1px solid var(--app-border-soft);
  border-radius: 3px;
  background: #edf2f7;
}

.heatmap-cell.level-1 {
  background: #bfdbfe;
}

.heatmap-cell.level-2 {
  background: #60a5fa;
}

.heatmap-cell.level-3 {
  background: #2563eb;
}

.heatmap-cell.level-4 {
  background: #1e40af;
}

.heatmap-summary {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  color: var(--app-muted);
  font-size: 12px;
}

.distribution-name,
.distribution-count {
  color: #4b5563;
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
  background: #edf1f7;
}

.bar-fill {
  height: 100%;
  border-radius: inherit;
  background: #2563eb;
}

.bar-fill.alt {
  background: #059669;
}

.bar-fill.warm {
  background: #d97706;
}

[data-theme='dark'] .distribution-name,
[data-theme='dark'] .distribution-count {
  color: #c7d0df;
}

[data-theme='dark'] .heatmap-cell {
  border-color: #263149;
  background: #1d2633;
}

[data-theme='dark'] .heatmap-cell.level-1 {
  background: #1e3a5f;
}

[data-theme='dark'] .heatmap-cell.level-2 {
  background: #1d4ed8;
}

[data-theme='dark'] .heatmap-cell.level-3 {
  background: #3b82f6;
}

[data-theme='dark'] .heatmap-cell.level-4 {
  background: #93c5fd;
}

[data-theme='dark'] .bar-track {
  background: #263149;
}

@media (max-width: 900px) {
  .reports-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .distribution-row {
    grid-template-columns: 1fr 1fr 44px;
  }

  .panel-title-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
