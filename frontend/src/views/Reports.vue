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

    <div class="toolbar">
      <el-radio-group v-model="selectedDays" @change="loadRangeData">
        <el-radio-button v-for="item in rangeOptions" :key="item.value" :label="item.value">
          {{ item.label }}
        </el-radio-button>
      </el-radio-group>
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
          <span class="panel-state">{{ panelStatus(trend) }}</span>
        </div>
        <div class="panel-body" v-loading="initialLoading(trend)">
          <div v-if="trend.loading && trend.hasLoaded" class="inline-updating">正在更新...</div>
          <div v-if="trend.error" :class="trend.hasLoaded ? 'inline-warning' : 'inline-error'">{{ trend.error }}</div>
          <template v-if="trend.items.length">
            <div class="heatmap-wrap" @mouseleave="hideHeatmapTooltip">
              <div class="heatmap-months" :style="{ '--heatmap-columns': String(heatmapWeeks.length) }">
                <span v-for="label in heatmapMonthLabels" :key="label.key">{{ label.text }}</span>
              </div>
              <div class="heatmap-body">
                <div class="heatmap-weekdays" aria-hidden="true">
                  <span></span>
                  <span>周一</span>
                  <span></span>
                  <span>周三</span>
                  <span></span>
                  <span>周五</span>
                  <span></span>
                </div>
                <div class="heatmap-grid" :style="{ '--heatmap-columns': String(heatmapWeeks.length) }">
                  <template v-for="week in heatmapWeeks" :key="week.key">
                    <div
                      v-for="cell in week.cells"
                      :key="cell.key"
                      class="heatmap-cell"
                      :class="[`level-${cell.item ? heatmapLevel(cell.item.play_count) : 0}`, { 'is-empty': !cell.item }]"
                      :aria-label="cell.item ? `${cell.date} 播放 ${cell.item.play_count} 次` : cell.date"
                      @mouseenter="showHeatmapTooltip($event, cell)"
                      @mousemove="moveHeatmapTooltip($event)"
                    ></div>
                  </template>
                </div>
                <div
                  v-if="heatmapTooltip.visible"
                  class="heatmap-tooltip"
                  :style="{ left: `${heatmapTooltip.left}px`, top: `${heatmapTooltip.top}px` }"
                >
                  <strong>{{ heatmapTooltip.date }}</strong>
                  <span>播放 {{ heatmapTooltip.playCount }} 次</span>
                  <span>看完 {{ heatmapTooltip.watchedCount }} 次</span>
                  <span>活跃用户 {{ heatmapTooltip.activeUserCount }} 人</span>
                </div>
              </div>
              <div class="heatmap-summary">
                <span>{{ trend.items[0]?.date }} 至 {{ trend.items[trend.items.length - 1]?.date }}</span>
                <span>共 {{ trendTotal }} 次播放</span>
              </div>
              <div class="heatmap-legend">
                <span>少</span>
                <i v-for="level in [0, 1, 2, 3, 4]" :key="level" class="heatmap-cell" :class="`level-${level}`"></i>
                <span>多</span>
              </div>
            </div>
          </template>
          <EmptyState v-else-if="!trend.loading" description="暂无播放趋势数据" />
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
          <EmptyState v-else-if="!mediaTypes.loading" description="暂无媒体类型数据" />
        </div>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>活跃用户榜</span>
        <span class="panel-state">{{ panelStatus(topUsers) }}</span>
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
          <el-table-column prop="last_played_at" label="最近播放" min-width="160" />
        </el-table>
        <EmptyState v-else-if="!topUsers.loading" description="暂无活跃用户数据" />
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
      <div class="panel-body" v-loading="initialLoading(topMedia)">
        <div class="panel-status-row">
          <span class="panel-state">{{ panelStatus(topMedia) }}</span>
        </div>
        <div v-if="topMedia.loading && topMedia.hasLoaded" class="inline-updating">正在更新...</div>
        <div v-if="topMedia.error" :class="topMedia.hasLoaded ? 'inline-warning' : 'inline-error'">{{ topMedia.error }}</div>
        <template>
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
          <EmptyState v-else-if="!topMedia.loading" description="暂无热门媒体数据" />
        </template>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>分辨率分布</span>
        <span class="panel-state">{{ panelStatus(resolutions) }}</span>
      </div>
      <div class="panel-body" v-loading="initialLoading(resolutions)">
        <div v-if="resolutions.loading && resolutions.hasLoaded" class="inline-updating">正在更新...</div>
        <div v-if="resolutions.error" :class="resolutions.hasLoaded ? 'inline-warning' : 'inline-error'">{{ resolutions.error }}</div>
        <template>
          <template v-if="resolutions.items.length">
            <div v-for="row in resolutions.items" :key="row.resolution" class="distribution-row">
              <span class="distribution-name" :class="{ muted: row.resolution === '未记录' }">{{ row.resolution || '未记录' }}</span>
              <div class="bar-track">
                <div class="bar-fill warm" :style="{ width: `${barWidth(row.play_count, resolutionMax)}%` }"></div>
              </div>
              <span class="distribution-count">{{ row.play_count }}</span>
            </div>
          </template>
          <EmptyState v-else-if="!resolutions.loading" description="暂无分辨率数据" />
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

interface HeatmapCell {
  key: string
  date: string
  item: PlayTrendItem | null
}

interface HeatmapWeek {
  key: string
  cells: HeatmapCell[]
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

const overview = reactive<DetailState<ReportOverview>>(createDetailState<ReportOverview>())
const trend = reactive<ListState<PlayTrendItem>>(createListState<PlayTrendItem>())
const topUsers = reactive<ListState<TopUserReportItem>>(createListState<TopUserReportItem>())
const topMedia = reactive<ListState<TopMediaReportItem>>(createListState<TopMediaReportItem>())
const mediaTypes = reactive<ListState<MediaTypeDistributionItem>>(createListState<MediaTypeDistributionItem>())
const resolutions = reactive<ListState<ResolutionDistributionItem>>(createListState<ResolutionDistributionItem>())
const heatmapTooltip = reactive({
  visible: false,
  left: 0,
  top: 0,
  date: '',
  playCount: 0,
  watchedCount: 0,
  activeUserCount: 0
})

const globalLoading = computed(() => overview.loading || trend.loading || topUsers.loading || topMedia.loading || mediaTypes.loading || resolutions.loading)
const allStates = computed(() => [overview, trend, topUsers, topMedia, mediaTypes, resolutions])
const hasAnyLoaded = computed(() => allStates.value.some((state) => state.hasLoaded))
const anyRefreshing = computed(() => allStates.value.some((state) => state.loading && state.hasLoaded))
const latestReportUpdatedAt = computed(() => {
  const latest = Math.max(...allStates.value.map((state) => state.lastUpdatedAt || 0))
  return latest > 0 ? formatClock(latest) : ''
})
const trendMax = computed(() => maxValue(trend.items.map((item) => item.play_count)))
const trendTotal = computed(() => trend.items.reduce((total, item) => total + item.play_count, 0))
const heatmapWeeks = computed(() => buildHeatmapWeeks(trend.items))
const heatmapMonthLabels = computed(() =>
  heatmapWeeks.value.map((week, index, weeks) => ({
    key: week.key,
    text: monthLabelForWeek(week, index, weeks)
  }))
)
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

function createDetailState<T>(): DetailState<T> {
  return { loading: false, error: '', hasLoaded: false, lastUpdatedAt: null, requestId: 0, data: null }
}

function createListState<T>(): ListState<T> {
  return { loading: false, error: '', hasLoaded: false, lastUpdatedAt: null, requestId: 0, items: [] }
}

async function loadDetail<T>(state: DetailState<T>, loader: () => Promise<T>) {
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
  } catch (error) {
    if (state.requestId !== requestId) return
    state.error = state.hasLoaded ? '更新失败，仍显示上次成功数据' : errorMessage(error)
  } finally {
    if (state.requestId === requestId) state.loading = false
  }
}

async function loadList<T>(state: ListState<T>, loader: () => Promise<T[]>) {
  const requestId = state.requestId + 1
  state.requestId = requestId
  state.loading = true
  state.error = ''
  try {
    const items = await loader()
    if (state.requestId !== requestId) return
    state.items = items
    state.hasLoaded = true
    state.lastUpdatedAt = Date.now()
  } catch (error) {
    if (state.requestId !== requestId) return
    state.error = state.hasLoaded ? '更新失败，仍显示上次成功数据' : errorMessage(error)
  } finally {
    if (state.requestId === requestId) state.loading = false
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

function heatmapLevel(value: number): number {
  if (value <= 0 || trendMax.value <= 0) return 0
  const ratio = value / trendMax.value
  if (ratio >= 0.75) return 4
  if (ratio >= 0.5) return 3
  if (ratio >= 0.25) return 2
  return 1
}

function initialLoading(state: { loading: boolean; hasLoaded: boolean }): boolean {
  return state.loading && !state.hasLoaded
}

function panelStatus(state: { loading: boolean; hasLoaded: boolean; lastUpdatedAt: number | null }): string {
  if (state.loading && state.hasLoaded) return '正在更新...'
  if (state.lastUpdatedAt) return `最后更新：${formatClock(state.lastUpdatedAt)}`
  return ''
}

function buildHeatmapWeeks(items: PlayTrendItem[]): HeatmapWeek[] {
  if (!items.length) return []
  const byDate = new Map(items.map((item) => [item.date, item]))
  const first = parseDateKey(items[0].date)
  const last = parseDateKey(items[items.length - 1].date)
  const start = addDays(first, -mondayIndex(first))
  const end = addDays(last, 6 - mondayIndex(last))
  const weeks: HeatmapWeek[] = []
  for (let cursor = start; cursor <= end; cursor = addDays(cursor, 7)) {
    const cells: HeatmapCell[] = []
    for (let day = 0; day < 7; day += 1) {
      const current = addDays(cursor, day)
      const key = formatDateKey(current)
      cells.push({ key, date: key, item: byDate.get(key) || null })
    }
    weeks.push({ key: formatDateKey(cursor), cells })
  }
  return weeks
}

function monthLabelForWeek(week: HeatmapWeek, index: number, weeks: HeatmapWeek[]): string {
  const firstCell = week.cells[0]
  const monthStart = week.cells.find((cell) => parseDateKey(cell.date).getDate() === 1)
  const previousMonth = index > 0 ? parseDateKey(weeks[index - 1].cells[0].date).getMonth() : -1
  const currentMonth = parseDateKey(firstCell.date).getMonth()
  const labelCell = monthStart || (index === 0 || currentMonth !== previousMonth ? firstCell : null)
  return labelCell ? `${parseDateKey(labelCell.date).getMonth() + 1}月` : ''
}

function parseDateKey(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function mondayIndex(date: Date): number {
  return (date.getDay() + 6) % 7
}

function showHeatmapTooltip(event: MouseEvent, cell: HeatmapCell): void {
  if (!cell.item) {
    hideHeatmapTooltip()
    return
  }
  heatmapTooltip.visible = true
  heatmapTooltip.date = cell.date
  heatmapTooltip.playCount = cell.item.play_count
  heatmapTooltip.watchedCount = cell.item.watched_count
  heatmapTooltip.activeUserCount = cell.item.active_user_count
  moveHeatmapTooltip(event)
}

function moveHeatmapTooltip(event: MouseEvent): void {
  if (!heatmapTooltip.visible) return
  heatmapTooltip.left = Math.max(8, Math.min(event.clientX + 14, window.innerWidth - 220))
  heatmapTooltip.top = Math.max(8, Math.min(event.clientY + 14, window.innerHeight - 120))
}

function hideHeatmapTooltip(): void {
  heatmapTooltip.visible = false
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

.panel-note {
  margin-bottom: 10px;
  color: var(--app-muted);
  font-size: 12px;
  line-height: 1.5;
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
  border: 1px solid #f5c2c7;
  border-radius: 8px;
  background: #fff1f2;
  color: #b42318;
}

.inline-warning,
.inline-updating {
  margin-bottom: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.inline-warning {
  border: 1px solid #fed7aa;
  background: #fff7ed;
  color: #9a3412;
}

.inline-updating {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #1d4ed8;
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
  padding-bottom: 2px;
}

.heatmap-months {
  --heatmap-columns: 5;
  display: grid;
  grid-template-columns: 38px repeat(var(--heatmap-columns), 14px);
  gap: 4px;
  width: max-content;
  min-width: 240px;
  color: var(--app-muted);
  font-size: 12px;
}

.heatmap-months span:first-child {
  grid-column: 2;
}

.heatmap-body {
  position: relative;
  display: flex;
  gap: 8px;
  width: max-content;
  min-width: 240px;
}

.heatmap-weekdays {
  display: grid;
  grid-template-rows: repeat(7, 14px);
  gap: 4px;
  width: 30px;
  color: var(--app-muted);
  font-size: 11px;
  line-height: 14px;
  text-align: right;
}

.heatmap-grid {
  --heatmap-columns: 5;
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 14px);
  grid-template-columns: repeat(var(--heatmap-columns), 14px);
  gap: 4px;
  align-items: center;
  width: max-content;
}

.heatmap-cell {
  width: 14px;
  height: 14px;
  border: 1px solid var(--app-border-soft);
  border-radius: 3px;
  background: #edf2f7;
}

.heatmap-cell.is-empty {
  opacity: 0.35;
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

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--app-muted);
  font-size: 12px;
}

.heatmap-legend .heatmap-cell {
  display: inline-block;
}

.heatmap-tooltip {
  position: fixed;
  z-index: 4000;
  display: grid;
  gap: 4px;
  width: 190px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
  color: #334155;
  font-size: 12px;
  pointer-events: none;
}

.heatmap-tooltip strong {
  color: #111827;
  font-size: 13px;
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

[data-theme='dark'] .inline-warning {
  border-color: #7c2d12;
  background: #2f1d12;
  color: #fdba74;
}

[data-theme='dark'] .inline-updating {
  border-color: #1d4ed8;
  background: #13233f;
  color: #93c5fd;
}

[data-theme='dark'] .heatmap-tooltip {
  border-color: #334155;
  background: rgba(15, 23, 42, 0.97);
  color: #cbd5e1;
}

[data-theme='dark'] .heatmap-tooltip strong {
  color: #f8fafc;
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
}
</style>
