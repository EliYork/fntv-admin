<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">媒体库</h1>
        <p class="page-subtitle">浏览顶层媒体；电视剧的季与单集在详情中按层级加载</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索电影或电视剧" class="media-search" clearable @clear="applyFilters" @keyup.enter="applyFilters" />
      <el-select v-model="mediaType" aria-label="媒体类型" class="media-type-select" @change="applyFilters">
        <el-option label="全部" value="" />
        <el-option label="电影" value="Movie" />
        <el-option label="剧集" value="Series" />
      </el-select>
      <el-button :icon="Search" type="primary" :loading="loading" @click="applyFilters">筛选</el-button>
    </div>

    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items" row-key="guid" @row-click="openSeriesFromRow">
        <el-table-column label="标题" min-width="260">
          <template #default="{ row }">
            <button v-if="isSeries(row)" class="series-title-button" type="button" @click.stop="openSeries(row)">{{ row.title || '-' }}</button>
            <span v-else>{{ row.title || '-' }}</span>
            <div v-if="row.title === row.guid" class="muted-guid">{{ row.guid }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110"><template #default="{ row }">{{ mediaTypeLabel(row.media_type) }}</template></el-table-column>
        <el-table-column label="内容概况 / 时长" min-width="150"><template #default="{ row }">{{ contentSummary(row) }}</template></el-table-column>
        <el-table-column prop="play_count" label="播放次数" width="110" />
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button v-if="isSeries(row)" size="small" text @click.stop="openSeries(row)">查看层级</el-button>
            <el-button size="small" text @click.stop="toggleHidden(row.guid, !row.hidden)">{{ row.hidden ? '恢复' : '隐藏' }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else description="暂无顶层媒体数据或未识别媒体表" />
      <PaginationFooter v-if="pageData" :page="page" :page-size="pageSize" :total="pageData.total" :disabled="loading" @page-change="handlePageChange" @page-size-change="handlePageSizeChange" />
    </div>

    <el-drawer v-model="seriesDrawerVisible" class="series-drawer" size="min(94vw, 520px)" destroy-on-close @closed="resetSeriesDrawer">
      <template #header>
        <div class="series-drawer-heading"><strong>{{ selectedSeries?.title || '电视剧详情' }}</strong><span>{{ seriesMeta }}</span></div>
      </template>
      <div v-loading="seriesLoading" class="series-hierarchy">
        <div v-if="selectedSeries" class="series-basics">
          <span class="media-type-chip">剧集</span>
          <span v-if="selectedSeries.play_count">播放 {{ selectedSeries.play_count }} 次</span>
          <span v-if="selectedSeries.release_time">{{ selectedSeries.release_time }}</span>
        </div>
        <div v-if="seriesError" class="hierarchy-empty">{{ seriesError }}</div>
        <template v-else-if="seriesChildren.length">
          <div v-for="season in seasons" :key="season.guid" class="season-group">
            <button class="season-button" type="button" :aria-expanded="expandedSeasons.has(season.guid)" @click="toggleSeason(season)">
              <span><strong>{{ seasonLabel(season) }}</strong><small>{{ season.children_count ? `${season.children_count} 集` : '点击查看单集' }}</small></span>
              <el-icon aria-hidden="true" :class="{ 'is-expanded': expandedSeasons.has(season.guid) }"><ArrowRight /></el-icon>
            </button>
            <div v-if="expandedSeasons.has(season.guid)" class="episode-list" v-loading="seasonLoading.has(season.guid)">
              <div v-for="episode in episodesBySeason[season.guid] || []" :key="episode.guid" class="episode-row">
                <span class="episode-marker">{{ episodeMarker(episode, season) }}</span><span class="episode-title">{{ episode.title || '未命名单集' }}</span><span v-if="episode.runtime && episode.runtime !== '-'" class="episode-runtime">{{ episode.runtime }}</span>
              </div>
              <div v-if="!seasonLoading.has(season.guid) && !(episodesBySeason[season.guid] || []).length" class="hierarchy-empty compact">暂无可用的单集信息</div>
            </div>
          </div>
          <div v-if="directEpisodes.length" class="season-group">
            <div class="season-button is-static"><span><strong>未分季</strong><small>{{ directEpisodes.length }} 集</small></span></div>
            <div class="episode-list">
              <div v-for="episode in directEpisodes" :key="episode.guid" class="episode-row">
                <span class="episode-marker">{{ episodeMarker(episode) }}</span><span class="episode-title">{{ episode.title || '未命名单集' }}</span><span v-if="episode.runtime && episode.runtime !== '-'" class="episode-runtime">{{ episode.runtime }}</span>
              </div>
            </div>
          </div>
        </template>
        <div v-else-if="!seriesLoading" class="hierarchy-empty">暂无可用的季/集层级信息</div>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ArrowRight, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchMedia, fetchMediaChildren, hideMedia, type MediaItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const keyword = ref('')
const mediaType = ref('')
const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<MediaItem> | null>(null)
const loading = ref(false)
const seriesDrawerVisible = ref(false)
const selectedSeries = ref<MediaItem | null>(null)
const seriesChildren = ref<MediaItem[]>([])
const seriesLoading = ref(false)
const seriesError = ref('')
const expandedSeasons = ref(new Set<string>())
const seasonLoading = ref(new Set<string>())
const episodesBySeason = ref<Record<string, MediaItem[]>>({})

const seasons = computed(() => seriesChildren.value.filter((item) => item.media_type.toLowerCase() === 'season'))
const directEpisodes = computed(() => seriesChildren.value.filter((item) => item.media_type.toLowerCase() === 'episode'))
const seriesMeta = computed(() => {
  if (seriesLoading.value) return '正在读取层级…'
  const parts: string[] = []
  if (seasons.value.length) parts.push(`${seasons.value.length} 季`)
  if (directEpisodes.value.length) parts.push(`${directEpisodes.value.length} 集未分季`)
  return parts.join(' · ') || '层级详情'
})

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchMedia({ page: page.value, page_size: pageSize.value, keyword: keyword.value, media_type: mediaType.value, scope: 'library' })
    page.value = pageData.value.page
    pageSize.value = pageData.value.page_size
  } finally { loading.value = false }
}

async function applyFilters() { page.value = 1; await loadData() }
async function handlePageChange(value: number) { page.value = value; await loadData() }
async function handlePageSizeChange(value: number) { pageSize.value = value; page.value = 1; await loadData() }
async function toggleHidden(guid: string, hidden: boolean) { await hideMedia(guid, hidden); ElMessage.success(hidden ? '已隐藏媒体' : '已恢复媒体'); page.value = 1; await loadData() }
function openSeriesFromRow(row: MediaItem): void { if (isSeries(row)) void openSeries(row) }

async function openSeries(series: MediaItem): Promise<void> {
  selectedSeries.value = series
  seriesDrawerVisible.value = true
  seriesLoading.value = true
  seriesError.value = ''
  seriesChildren.value = []
  try { seriesChildren.value = await fetchMediaChildren(series.guid) }
  catch { seriesError.value = '暂无可用的季/集层级信息' }
  finally { seriesLoading.value = false }
}

async function toggleSeason(season: MediaItem): Promise<void> {
  const nextExpanded = new Set(expandedSeasons.value)
  if (nextExpanded.has(season.guid)) { nextExpanded.delete(season.guid); expandedSeasons.value = nextExpanded; return }
  nextExpanded.add(season.guid)
  expandedSeasons.value = nextExpanded
  if (episodesBySeason.value[season.guid]) return
  seasonLoading.value = new Set(seasonLoading.value).add(season.guid)
  try { episodesBySeason.value = { ...episodesBySeason.value, [season.guid]: await fetchMediaChildren(season.guid) } }
  catch { episodesBySeason.value = { ...episodesBySeason.value, [season.guid]: [] } }
  finally { const nextLoading = new Set(seasonLoading.value); nextLoading.delete(season.guid); seasonLoading.value = nextLoading }
}

function resetSeriesDrawer(): void { selectedSeries.value = null; seriesChildren.value = []; seriesError.value = ''; expandedSeasons.value = new Set(); seasonLoading.value = new Set(); episodesBySeason.value = {} }
function isSeries(item: MediaItem): boolean { return ['series', 'tv'].includes(item.media_type.toLowerCase()) }
function contentSummary(item: MediaItem): string {
  return isSeries(item) ? '剧集' : String(item.runtime || '-')
}
function seasonLabel(season: MediaItem): string { return season.season_number !== null && season.season_number !== undefined ? `第 ${season.season_number} 季` : season.title || '未命名季' }
function episodeMarker(episode: MediaItem, season?: MediaItem): string {
  const seasonNumber = episode.season_number ?? season?.season_number
  const episodeNumber = episode.episode_number
  if (seasonNumber !== null && seasonNumber !== undefined && episodeNumber !== null && episodeNumber !== undefined) return `S${String(seasonNumber).padStart(2, '0')}E${String(episodeNumber).padStart(2, '0')}`
  if (episodeNumber !== null && episodeNumber !== undefined) return `E${String(episodeNumber).padStart(2, '0')}`
  return '单集'
}
function mediaTypeLabel(type: string): string { return ({ Movie: '电影', Series: '剧集', TV: '剧集', Video: '视频' } as Record<string, string>)[type] || type || '未知' }

onMounted(loadData)
useRouteRefresh(loadData)
</script>

<style scoped>
.media-search { width: 280px; }
.media-type-select { width: 180px; }
.series-title-button { padding: 0; border: 0; background: transparent; color: var(--app-accent); cursor: pointer; font: inherit; font-weight: 650; text-align: left; }
.series-title-button:hover { text-decoration: underline; }
.series-title-button:focus-visible { outline: 2px solid var(--app-accent); outline-offset: 3px; border-radius: 2px; }
.series-drawer-heading { display: grid; gap: 4px; min-width: 0; }
.series-drawer-heading strong { overflow: hidden; color: var(--app-title); font-size: 18px; text-overflow: ellipsis; white-space: nowrap; }
.series-drawer-heading span { color: var(--app-muted); font-size: 12px; }
.series-hierarchy { min-height: 180px; }
.series-basics { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-bottom: 24px; color: var(--app-muted); font-size: 12px; }
.media-type-chip { padding: 4px 8px; border-radius: 999px; background: var(--app-surface-soft); color: var(--app-accent); font-weight: 650; }
.season-group { overflow: hidden; margin-bottom: 10px; border: 1px solid var(--app-border-soft); border-radius: 10px; background: var(--app-surface); }
.season-button { display: flex; align-items: center; justify-content: space-between; gap: 16px; width: 100%; min-height: 58px; padding: 10px 14px; border: 0; background: transparent; color: var(--app-text); cursor: pointer; text-align: left; }
.season-button:hover { background: var(--app-surface-soft); }
.season-button:focus-visible { outline: 2px solid var(--app-accent); outline-offset: -3px; }
.season-button > span { display: grid; gap: 3px; }
.season-button strong { color: var(--app-title); font-size: 14px; }
.season-button small { color: var(--app-muted); font-size: 12px; }
.season-button .el-icon { transition: transform 160ms ease; }
.season-button .el-icon.is-expanded { transform: rotate(90deg); }
.season-button.is-static { cursor: default; }
.season-button.is-static:hover { background: transparent; }
.episode-list { min-height: 48px; padding: 2px 14px 10px; border-top: 1px solid var(--app-border-soft); }
.episode-row { display: grid; grid-template-columns: 68px minmax(0, 1fr) auto; align-items: center; gap: 10px; min-height: 45px; border-bottom: 1px solid var(--app-border-soft); font-size: 13px; }
.episode-row:last-child { border-bottom: 0; }
.episode-marker { color: var(--app-muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.episode-title { min-width: 0; overflow: hidden; color: var(--app-title); text-overflow: ellipsis; white-space: nowrap; }
.episode-runtime { color: var(--app-muted); font-size: 11px; white-space: nowrap; }
.hierarchy-empty { padding: 36px 16px; color: var(--app-muted); text-align: center; }
.hierarchy-empty.compact { padding: 22px 8px 12px; font-size: 12px; }
@media (max-width: 640px) { .media-search, .media-type-select { width: 100%; } .episode-row { grid-template-columns: 58px minmax(0, 1fr); } .episode-runtime { display: none; } }
</style>
