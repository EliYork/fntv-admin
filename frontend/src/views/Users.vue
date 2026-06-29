<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-subtitle">用户展示增强信息写入 admin.db，不修改飞牛用户表</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名" style="width: 260px" clearable @clear="applyFilters" @keyup.enter="applyFilters" />
      <el-button :icon="Search" type="primary" :loading="loading" @click="applyFilters">搜索</el-button>
      <el-switch v-model="showHidden" active-text="显示隐藏用户" @change="applyFilters" />
    </div>
    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items" @sort-change="handleSortChange">
        <el-table-column prop="username" label="用户名" min-width="160" sortable="custom" />
        <el-table-column label="GUID" min-width="220">
          <template #default="{ row }">
            <span class="muted-guid">{{ row.guid }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="play_count" label="播放次数" width="110" sortable="custom" />
        <el-table-column prop="watch_seconds" label="观看时长" width="120" sortable="custom">
          <template #default="{ row }">{{ row.watch_duration }}</template>
        </el-table-column>
        <el-table-column prop="last_play_at" label="最近播放" min-width="150" sortable="custom" />
        <el-table-column prop="last_login_at" label="最近登录" min-width="150" sortable="custom" />
        <el-table-column prop="note" label="备注" min-width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text @click="toggleHidden(row.guid, !row.hidden)">
              {{ row.hidden ? '恢复' : '隐藏' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else description="暂无用户数据或未识别用户表" />
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
import { Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchUsers, hideUser, type UserItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const keyword = ref('')
const showHidden = ref(false)
const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<UserItem> | null>(null)
const loading = ref(false)
const sortBy = ref('')
const sortOrder = ref('')

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchUsers({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value,
      show_hidden: showHidden.value,
      sort_by: sortBy.value || undefined,
      sort_order: sortOrder.value || undefined
    })
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

function handleSortChange(event: { prop: string; order: 'ascending' | 'descending' | null }) {
  const sortMap: Record<string, string> = {
    username: 'username',
    play_count: 'play_count',
    watch_seconds: 'watch_duration',
    last_play_at: 'last_play_at',
    last_login_at: 'last_login_at'
  }
  sortBy.value = event.order && sortMap[event.prop] ? sortMap[event.prop] : ''
  sortOrder.value = event.order === 'descending' ? 'desc' : event.order === 'ascending' ? 'asc' : ''
  page.value = 1
  void loadData()
}

async function toggleHidden(guid: string, hidden: boolean) {
  await hideUser(guid, hidden)
  ElMessage.success(hidden ? '已隐藏用户' : '已恢复用户')
  page.value = 1
  await loadData()
}

onMounted(loadData)
useRouteRefresh(loadData)
</script>
