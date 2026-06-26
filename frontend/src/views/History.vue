<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">观看历史</h1>
        <p class="page-subtitle">分页查看播放记录，筛选能力已预留</p>
      </div>
      <el-button :icon="Download" :loading="exporting" @click="exportCsv">导出 CSV</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索标题或用户" style="width: 260px" clearable @clear="applyFilters" @keyup.enter="applyFilters" />
      <el-button :icon="Search" type="primary" :loading="loading" @click="applyFilters">筛选</el-button>
    </div>
    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column prop="username" label="用户" min-width="150" />
        <el-table-column prop="display_title" label="媒体标题" min-width="260" />
        <el-table-column prop="played_at" label="播放时间" min-width="160" />
        <el-table-column prop="progress" label="进度" width="120" />
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
import { Download, Search } from '@element-plus/icons-vue'
import { downloadHistoryCsv, fetchHistory, type HistoryItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'

const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<HistoryItem> | null>(null)
const loading = ref(false)
const exporting = ref(false)

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchHistory({ page: page.value, page_size: pageSize.value, keyword: keyword.value })
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
    const blob = await downloadHistoryCsv({ keyword: keyword.value })
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

onMounted(loadData)
</script>
