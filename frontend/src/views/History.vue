<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">观看历史</h1>
        <p class="page-subtitle">分页查看播放记录，筛选能力已预留</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
        <el-button :icon="Download" :loading="exporting" @click="exportCsv">导出 CSV</el-button>
      </div>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索标题或用户" style="width: 260px" clearable @clear="applyFilters" @keyup.enter="applyFilters" />
      <el-select v-model="range" placeholder="时间范围" style="width: 150px" @change="applyFilters">
        <el-option label="今天" value="today" />
        <el-option label="最近 7 天" value="7d" />
        <el-option label="最近 30 天" value="30d" />
        <el-option label="全部" value="all" />
      </el-select>
      <el-button :icon="Search" type="primary" :loading="loading" @click="applyFilters">筛选</el-button>
    </div>
    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column prop="username" label="用户" min-width="150" />
        <el-table-column prop="display_title" label="媒体标题" min-width="260" />
        <el-table-column prop="played_at" label="播放时间" min-width="160" />
        <el-table-column label="进度" min-width="260">
          <template #default="{ row }">
            <div class="history-progress">
              <div class="progress-track" :class="{ 'is-unknown': progressPercent(row) === null }">
                <div class="progress-fill" :style="{ width: `${progressPercent(row) ?? 0}%` }"></div>
              </div>
              <div class="progress-meta">
                <span>{{ progressText(row) }}</span>
                <el-tag v-if="progressWarning(row)" size="small" type="warning" effect="light">{{ progressWarning(row) }}</el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="watched_text" label="看完" width="90" />
        <el-table-column prop="resolution" label="分辨率" width="110" />
      </el-table>
      <EmptyState v-else description="暂无观看历史或未识别播放记录表" />
      <PaginationFooter
        v-if="pageData"
        :page="page"
        :page-size="pageSize"
        :total="pageData.total"
        :disabled="loading"
        @page-change="handlePageChange"
        @page-size-change="handlePageSizeChange"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Download, Refresh, Search } from '@element-plus/icons-vue'
import { downloadHistoryCsv, fetchHistory, type HistoryItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const keyword = ref('')
const range = ref<'today' | '7d' | '30d' | 'all'>('all')
const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<HistoryItem> | null>(null)
const loading = ref(false)
const exporting = ref(false)

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchHistory({ page: page.value, page_size: pageSize.value, keyword: keyword.value, range: range.value })
    page.value = pageData.value.page
    pageSize.value = pageData.value.page_size
  } finally {
    loading.value = false
  }
}

async function applyFilters() {
  page.value = 1
  await loadData()
}

async function handlePageChange(value: number) {
  page.value = value
  await loadData()
}

async function handlePageSizeChange(value: number) {
  pageSize.value = value
  page.value = 1
  await loadData()
}

async function exportCsv() {
  exporting.value = true
  try {
    const blob = await downloadHistoryCsv({ keyword: keyword.value, range: range.value })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'fntv-history.csv'
    link.click()
    URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

function progressPercent(row: HistoryItem): number | null {
  if (row.watched) return 100
  if (typeof row.progress_percent === 'number') return Math.max(0, Math.min(100, row.progress_percent))
  if (row.position_seconds != null && row.runtime_seconds && row.runtime_seconds > 0) {
    return Math.max(0, Math.min(100, (row.position_seconds / row.runtime_seconds) * 100))
  }
  return null
}

function progressText(row: HistoryItem): string {
  if (row.watched && !row.progress) return '已看完'
  return row.progress || '-'
}

function progressWarning(row: HistoryItem): string {
  if (row.watched) return '已看完'
  if (row.position_seconds != null && row.runtime_seconds && row.position_seconds > row.runtime_seconds) {
    return '进度异常'
  }
  return ''
}

onMounted(loadData)
useRouteRefresh(loadData)
</script>

<style scoped>
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-progress {
  display: grid;
  gap: 6px;
  min-width: 180px;
}

.progress-track {
  width: 100%;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--app-bar-track);
}

.progress-track.is-unknown {
  background: repeating-linear-gradient(90deg, var(--app-bar-track), var(--app-bar-track) 8px, var(--app-border) 8px, var(--app-border) 12px);
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--app-accent);
}

.progress-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  color: var(--app-muted-strong);
  font-size: 12px;
}
</style>
