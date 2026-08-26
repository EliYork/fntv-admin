<template>
  <section class="history-feed" aria-labelledby="history-feed-title">
    <header class="history-heading">
      <div>
        <component :is="headingTag" id="history-feed-title">{{ heading }}</component>
        <p aria-live="polite">已显示 {{ items.length.toLocaleString('zh-CN') }} / {{ total.toLocaleString('zh-CN') }} 条</p>
      </div>
      <el-button :icon="Download" :loading="exporting" @click="exportCsv">导出 CSV</el-button>
    </header>

    <form class="history-toolbar" aria-label="观看历史筛选" @submit.prevent="applyFilters">
      <el-input
        v-model="keyword"
        class="history-search"
        aria-label="搜索标题或用户"
        placeholder="搜索标题或用户"
        clearable
        :prefix-icon="Search"
        @clear="applyFilters"
      />
      <el-select v-model="range" aria-label="选择时间范围" @change="applyFilters">
        <el-option label="今天" value="today" />
        <el-option label="最近 7 天" value="7d" />
        <el-option label="最近 30 天" value="30d" />
        <el-option label="全部时间" value="all" />
      </el-select>
      <el-select v-model="userGuid" aria-label="选择用户" clearable filterable placeholder="全部用户" @change="applyFilters">
        <el-option v-for="user in userOptions" :key="user.guid" :label="user.display_name || user.username || user.guid" :value="user.guid" />
      </el-select>
      <el-button native-type="submit" :loading="initialLoading">筛选</el-button>
      <label class="batch-control">
        <span>每批加载</span>
        <el-select v-model="pageSize" aria-label="每批加载条数" @change="changePageSize">
          <el-option :value="20" label="20" />
          <el-option :value="50" label="50" />
          <el-option :value="100" label="100" />
        </el-select>
      </label>
    </form>

    <div v-if="errorMessage" class="history-error" role="alert">{{ errorMessage }}</div>

    <div v-if="initialLoading" class="history-loading" aria-label="正在加载观看历史">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="groups.length" class="history-groups">
      <section v-for="group in groups" :key="group.key" class="history-day">
        <h3>{{ group.label }}</h3>
        <div class="history-list">
          <article
            v-for="item in group.items"
            :key="historyKey(item)"
            v-memo="[historyKey(item), item.progress_percent, item.watched]"
            class="history-entry"
          >
            <div class="history-time">
              <time :datetime="historyDateTime(item)">{{ formatTime(item) }}</time>
              <span>{{ item.username || item.user || '未知用户' }}</span>
            </div>

            <div class="history-title-block">
              <strong :title="item.display_title || item.title">{{ item.display_title || item.title || '未命名媒体' }}</strong>
              <span v-if="secondaryTitle(item)">{{ secondaryTitle(item) }}</span>
            </div>

            <div class="history-progress">
              <div class="progress-copy">
                <span>{{ progressText(item) }}</span>
                <span v-if="progressWarning(item)" class="progress-warning">{{ progressWarning(item) }}</span>
              </div>
              <div class="progress-track" :class="{ 'is-unknown': progressPercent(item) === null, 'is-warning': Boolean(progressWarning(item)) }">
                <span :style="{ width: `${progressPercent(item) ?? 0}%` }"></span>
              </div>
            </div>

            <span class="history-resolution">{{ item.resolution || '—' }}</span>
          </article>
        </div>
      </section>
    </div>

    <EmptyState v-else description="暂无观看历史或未识别播放记录表" />

    <footer v-if="items.length" class="history-footer">
      <div ref="loadSentinel" class="load-sentinel" aria-hidden="true"></div>
      <el-button v-if="hasMore" :loading="loadingMore" @click="loadNextPage">加载更多</el-button>
      <p v-else>已到达历史记录末尾</p>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { Download, Search } from '@element-plus/icons-vue'
import { downloadHistoryCsv, fetchHistory, fetchUsers, type HistoryItem, type UserItem } from '../api/modules'
import EmptyState from './EmptyState.vue'
import { applicationTodayKey, calendarDayDifference, parseApplicationDateTime, type ApplicationDateParts } from '../utils/applicationTime'

withDefaults(defineProps<{ heading?: string; headingTag?: 'h1' | 'h2' }>(), { heading: '观看历史', headingTag: 'h2' })

type HistoryRange = 'today' | '7d' | '30d' | 'all'

interface HistoryGroup {
  key: string
  label: string
  items: HistoryItem[]
}

const keyword = ref('')
const range = ref<HistoryRange>('all')
const userGuid = ref('')
const pageSize = ref(50)
const nextPage = ref(1)
const total = ref(0)
const totalPages = ref(0)
const items = ref<HistoryItem[]>([])
const userOptions = ref<UserItem[]>([])
const initialLoading = ref(false)
const loadingMore = ref(false)
const exporting = ref(false)
const exhausted = ref(false)
const errorMessage = ref('')
const applicationTimezone = ref('Asia/Shanghai')
const loadSentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null
let requestVersion = 0

const hasMore = computed(() => {
  if (exhausted.value) return false
  if (total.value === 0) return false
  return items.value.length < total.value && nextPage.value <= totalPages.value
})

const groups = computed<HistoryGroup[]>(() => {
  const grouped = new Map<string, HistoryGroup>()
  for (const item of items.value) {
    const parts = historyDateParts(item)
    const key = parts?.dateKey || 'unknown'
    const group = grouped.get(key) || { key, label: formatGroupLabel(parts), items: [] }
    group.items.push(item)
    grouped.set(key, group)
  }
  return Array.from(grouped.values())
})

async function loadNextPage() {
  if (initialLoading.value || loadingMore.value || exhausted.value) return
  const requestedPage = nextPage.value
  const version = requestVersion
  const isInitial = requestedPage === 1 && items.value.length === 0
  if (isInitial) initialLoading.value = true
  else loadingMore.value = true
  errorMessage.value = ''

  try {
    const data = await fetchHistory({
      page: requestedPage,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      range: range.value,
      user_guid: userGuid.value || undefined
    })
    if (version !== requestVersion) return
    if (data.error) throw new Error('history-data-unavailable')

    const knownKeys = new Set(items.value.map(historyKey))
    const uniqueItems = data.items.filter((item) => {
      const key = historyKey(item)
      if (knownKeys.has(key)) return false
      knownKeys.add(key)
      return true
    })

    items.value = requestedPage === 1 ? uniqueItems : [...items.value, ...uniqueItems]
    total.value = data.total
    totalPages.value = data.pages
    applicationTimezone.value = data.application_timezone || applicationTimezone.value
    nextPage.value = data.page + 1
    errorMessage.value = ''
    exhausted.value = data.items.length === 0 || (requestedPage > 1 && uniqueItems.length === 0) || items.value.length >= data.total || data.page >= data.pages
  } catch {
    // Keep every previously committed page and retry the same nextPage later.
  } finally {
    if (version === requestVersion) {
      initialLoading.value = false
      loadingMore.value = false
    }
  }
}

async function resetAndLoad(preserveExisting = false) {
  requestVersion += 1
  const version = requestVersion
  observer?.disconnect()
  initialLoading.value = false
  loadingMore.value = false
  errorMessage.value = ''
  if (!preserveExisting) {
    items.value = []
    total.value = 0
    totalPages.value = 0
    nextPage.value = 1
    exhausted.value = false
  }
  initialLoading.value = items.value.length === 0
  try {
    const data = await fetchHistory({
      page: 1,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      range: range.value,
      user_guid: userGuid.value || undefined
    })
    if (version !== requestVersion || data.error) return
    const uniqueItems = deduplicate(data.items)
    items.value = uniqueItems
    total.value = data.total
    totalPages.value = data.pages
    nextPage.value = data.page + 1
    exhausted.value = data.items.length === 0 || uniqueItems.length >= data.total || data.page >= data.pages
    applicationTimezone.value = data.application_timezone || applicationTimezone.value
  } catch {
    // Refresh is atomic: existing history remains visible after any failure.
  } finally {
    if (version === requestVersion) initialLoading.value = false
  }
  await nextTick()
  setupObserver()
}

async function applyFilters() {
  await resetAndLoad()
}

async function changePageSize() {
  await resetAndLoad()
}

async function exportCsv() {
  exporting.value = true
  try {
    const blob = await downloadHistoryCsv({
      keyword: keyword.value.trim() || undefined,
      range: range.value,
      user_guid: userGuid.value || undefined
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'fntv-history.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  } catch (error) {
    errorMessage.value = 'CSV 导出失败，请稍后重试'
  } finally {
    exporting.value = false
  }
}

async function loadUserOptions() {
  try {
    const data = await fetchUsers({ page: 1, page_size: 100, sort_by: 'play_count', sort_order: 'desc' }, { suppressGlobalError: true })
    userOptions.value = data.items
  } catch {
    userOptions.value = []
  }
}

function setupObserver() {
  observer?.disconnect()
  if (!loadSentinel.value) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting) && hasMore.value) void loadNextPage()
    },
    { root: document.querySelector('.main-view'), rootMargin: '0px 0px 360px 0px' }
  )
  observer.observe(loadSentinel.value)
}

function historyKey(item: HistoryItem): string {
  return item.id || [item.user_guid, item.item_guid, item.played_at || item.started_at || '', item.position_seconds ?? ''].join(':')
}

function historyDateTime(item: HistoryItem): string {
  return String(item.played_at || item.started_at || '')
}

function historyDateParts(item: HistoryItem): ApplicationDateParts | null {
  const value = item.played_at || item.started_at
  return parseApplicationDateTime(value, applicationTimezone.value)
}

function formatTime(item: HistoryItem): string {
  const parts = historyDateParts(item)
  return parts ? parts.timeKey.slice(0, 5) : '时间未知'
}

function formatGroupLabel(parts: ApplicationDateParts | null): string {
  if (!parts) return '时间未知'
  const todayKey = applicationTodayKey(applicationTimezone.value)
  const days = todayKey ? calendarDayDifference(todayKey, parts.dateKey) : -1
  const dateLabel = `${parts.month} 月 ${parts.day} 日`
  if (days === 0) return `今天 · ${dateLabel}`
  if (days === 1) return `昨天 · ${dateLabel}`
  return `${parts.year} 年 ${dateLabel}`
}

function secondaryTitle(item: HistoryItem): string {
  const raw = item.title?.trim()
  const display = item.display_title?.trim()
  return raw && display && raw !== display && !display.endsWith(raw) ? raw : ''
}

function progressPercent(item: HistoryItem): number | null {
  if (item.watched) return 100
  if (typeof item.progress_percent === 'number') return Math.max(0, Math.min(100, item.progress_percent))
  if (item.position_seconds != null && item.runtime_seconds && item.runtime_seconds > 0) {
    return Math.max(0, Math.min(100, (item.position_seconds / item.runtime_seconds) * 100))
  }
  return null
}

function progressText(item: HistoryItem): string {
  if (item.progress) return item.progress
  const percent = progressPercent(item)
  return percent == null ? '进度未知' : `${Math.round(percent)}%`
}

function progressWarning(item: HistoryItem): string {
  if (item.position_seconds != null && item.runtime_seconds && item.position_seconds > item.runtime_seconds) return '进度异常'
  return ''
}

function deduplicate(source: HistoryItem[]): HistoryItem[] {
  const known = new Set<string>()
  return source.filter((item) => {
    const key = historyKey(item)
    if (known.has(key)) return false
    known.add(key)
    return true
  })
}

async function refresh() {
  await resetAndLoad(true)
}

defineExpose({ refresh })

onMounted(async () => {
  void loadUserOptions()
  await resetAndLoad()
})

onUnmounted(() => observer?.disconnect())
</script>

<style scoped>
.history-feed {
  display: grid;
  gap: 20px;
  min-width: 0;
  padding-top: clamp(8px, 1.5vw, 20px);
}

.history-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--app-border);
}

.history-heading h1, .history-heading h2 { margin: 0; color: var(--app-title); font-size: clamp(20px, 2vw, 26px); font-weight: 670; letter-spacing: -0.02em; }
.history-heading p { margin: 5px 0 0; color: var(--app-muted); font-size: 12px; font-variant-numeric: tabular-nums; }

.history-toolbar {
  display: grid;
  grid-template-columns: minmax(220px, 1.6fr) minmax(130px, 0.65fr) minmax(150px, 0.85fr) auto minmax(144px, auto);
  align-items: center;
  gap: 10px;
}

.batch-control { display: flex; align-items: center; justify-content: flex-end; gap: 8px; color: var(--app-muted); font-size: 12px; white-space: nowrap; }
.batch-control :deep(.el-select) { width: 76px; }
.history-error { padding: 11px 13px; border: 1px solid var(--app-error-border); border-radius: 8px; background: var(--app-error-bg); color: var(--app-error-text); }
.history-loading { padding: 8px 0; }
.history-groups { display: grid; gap: 28px; }
.history-day { min-width: 0; }

.history-day h3 {
  position: sticky;
  z-index: 2;
  top: -1px;
  margin: 0;
  padding: 10px 0 9px;
  background: var(--app-bg);
  color: var(--app-muted-strong);
  font-size: 12px;
  font-weight: 680;
  letter-spacing: 0.035em;
}

.history-list { border-top: 1px solid var(--app-border-soft); }

.history-entry {
  display: grid;
  grid-template-columns: 142px minmax(250px, 1fr) minmax(210px, 0.7fr) 70px;
  align-items: center;
  gap: 22px;
  min-height: 82px;
  padding: 14px 10px;
  border-bottom: 1px solid var(--app-border-soft);
  transition: background-color 160ms ease;
  content-visibility: auto;
  contain-intrinsic-size: 82px;
}

.history-entry:hover { background: var(--app-row-hover); }
.history-time, .history-title-block, .history-progress { display: grid; gap: 5px; min-width: 0; }
.history-time time { color: var(--app-title); font-size: 15px; font-variant-numeric: tabular-nums; }
.history-time span, .history-title-block span, .progress-copy, .history-resolution { color: var(--app-muted); font-size: 12px; }
.history-title-block strong { overflow: hidden; color: var(--app-title); font-size: 15px; font-weight: 630; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.history-title-block span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.progress-copy { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-variant-numeric: tabular-nums; }
.progress-warning { color: var(--app-danger); font-weight: 650; }

.progress-track {
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--app-bar-track);
}

.progress-track > span { display: block; height: 100%; border-radius: inherit; background: var(--app-accent); }
.progress-track.is-unknown { background: repeating-linear-gradient(90deg, var(--app-bar-track), var(--app-bar-track) 7px, var(--app-border) 7px, var(--app-border) 10px); }
.progress-track.is-warning > span { background: var(--app-danger); }
.history-resolution { text-align: right; font-variant-numeric: tabular-nums; }
.history-footer { display: grid; justify-items: center; gap: 10px; padding-top: 8px; }
.history-footer p { margin: 0; color: var(--app-muted); font-size: 12px; }
.load-sentinel { width: 100%; height: 1px; }

@media (max-width: 980px) {
  .history-toolbar { grid-template-columns: minmax(220px, 1fr) repeat(2, minmax(130px, 0.55fr)); }
  .history-toolbar > :deep(.el-button) { justify-self: start; }
  .batch-control { justify-content: flex-start; }
  .history-entry { grid-template-columns: 120px minmax(220px, 1fr) minmax(180px, 0.75fr) 60px; gap: 16px; }
}

@media (max-width: 700px) {
  .history-heading { align-items: center; }
  .history-toolbar { grid-template-columns: 1fr 1fr; }
  .history-search, .batch-control { grid-column: 1 / -1; }
  .history-toolbar > :deep(.el-button) { width: 100%; }
  .batch-control { justify-content: space-between; }
  .history-toolbar :deep(.el-input__wrapper), .history-toolbar :deep(.el-select__wrapper), .history-toolbar :deep(.el-button) { min-height: 44px; }
  .history-entry { grid-template-columns: minmax(0, 1fr) auto; gap: 10px 14px; min-height: 0; padding: 15px 4px; }
  .history-time { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; }
  .history-time time { font-size: 13px; }
  .history-time span { text-align: right; }
  .history-title-block { grid-column: 1 / -1; }
  .history-title-block strong { white-space: normal; }
  .history-progress { grid-column: 1; }
  .history-resolution { grid-column: 2; align-self: end; }
}

@media (max-width: 420px) {
  .history-toolbar { grid-template-columns: 1fr; }
  .history-search, .batch-control { grid-column: auto; }
}
</style>
