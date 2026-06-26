<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">观看历史</h1>
        <p class="page-subtitle">分页查看播放记录，筛选能力已预留</p>
      </div>
      <el-button :icon="Download" @click="exportCsv">导出 CSV</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索标题" style="width: 260px" clearable @keyup.enter="loadData" />
      <el-button :icon="Search" type="primary" @click="loadData">筛选</el-button>
    </div>
    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" :data="pageData.items">
        <el-table-column prop="user" label="用户" min-width="140" />
        <el-table-column prop="title" label="媒体标题" min-width="240" />
        <el-table-column prop="played_at" label="播放时间" min-width="160" />
        <el-table-column prop="progress" label="进度" width="120" />
        <el-table-column prop="watched" label="看完" width="90" />
      </el-table>
      <EmptyState v-else description="暂无观看历史或未识别播放记录表" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Download, Search } from '@element-plus/icons-vue'
import { downloadHistoryCsv, fetchHistory, type HistoryItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'

const keyword = ref('')
const pageData = ref<PageData<HistoryItem> | null>(null)

async function loadData() {
  pageData.value = await fetchHistory({ page: 1, page_size: 20, keyword: keyword.value })
}

async function exportCsv() {
  const blob = await downloadHistoryCsv()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'fntv-history.csv'
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(loadData)
</script>
