<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">任务中心</h1>
        <p class="page-subtitle">任务记录将写入 admin.db，不触碰飞牛数据库</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
        <el-button @click="runHealthCheck">健康检查</el-button>
      </div>
    </div>
    <div class="table-panel">
      <div class="panel-title">任务列表</div>
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column prop="started_at" label="开始时间" min-width="160" />
        <el-table-column prop="task_type" label="任务" min-width="160" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="message" label="说明" min-width="240" />
      </el-table>
      <EmptyState v-else description="暂无任务记录" />
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
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchTasks, type TaskItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<TaskItem> | null>(null)
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchTasks({ page: page.value, page_size: pageSize.value })
    page.value = pageData.value.page
    pageSize.value = pageData.value.page_size
  } finally {
    loading.value = false
  }
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

function runHealthCheck() {
  ElMessage.success('健康检查任务入口已预留')
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
