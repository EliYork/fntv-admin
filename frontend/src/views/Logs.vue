<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">日志中心</h1>
        <p class="page-subtitle">日志读取范围限定在 /data/logs</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
        <el-button :icon="Delete">清理旧日志</el-button>
      </div>
    </div>
    <div class="toolbar">
      <el-select v-model="level" placeholder="日志等级" style="width: 160px" @change="applyFilters">
        <el-option label="全部" value="" />
        <el-option label="INFO" value="INFO" />
        <el-option label="ERROR" value="ERROR" />
      </el-select>
    </div>
    <div class="table-panel">
      <div class="panel-title">运行日志</div>
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column prop="created_at" label="时间" min-width="160" />
        <el-table-column prop="level" label="等级" width="100" />
        <el-table-column prop="message" label="内容" min-width="260" />
      </el-table>
      <EmptyState v-else description="暂无可展示日志" />
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
import { Delete, Refresh } from '@element-plus/icons-vue'
import { fetchLogs, type LogItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const level = ref('')
const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<LogItem> | null>(null)
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchLogs({ page: page.value, page_size: pageSize.value, level: level.value })
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

onMounted(loadData)
useRouteRefresh(loadData)
</script>

<style scoped>
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
