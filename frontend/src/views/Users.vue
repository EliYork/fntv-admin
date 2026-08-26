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
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column prop="username" min-width="160">
          <template #header><SortHeader label="用户名" sort-key="username" :active-key="sortBy" :direction="sortOrder" @sort="applySort" /></template>
        </el-table-column>
        <el-table-column label="GUID" min-width="220">
          <template #default="{ row }">
            <span class="muted-guid">{{ row.guid }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="play_count" width="110">
          <template #header><SortHeader label="播放次数" sort-key="play_count" :active-key="sortBy" :direction="sortOrder" @sort="applySort" /></template>
        </el-table-column>
        <el-table-column prop="watch_seconds" width="120">
          <template #header><SortHeader label="观看时长" sort-key="watch_duration" :active-key="sortBy" :direction="sortOrder" @sort="applySort" /></template>
          <template #default="{ row }">{{ row.watch_duration }}</template>
        </el-table-column>
        <el-table-column prop="last_play_at" min-width="170">
          <template #header><SortHeader label="最近播放" sort-key="last_play_at" :active-key="sortBy" :direction="sortOrder" @sort="applySort" /></template>
          <template #default="{ row }">{{ formatApplicationDateTime(row.last_play_at) }}</template>
        </el-table-column>
        <el-table-column prop="last_login_at" min-width="170">
          <template #header><SortHeader label="最近登录" sort-key="last_login_at" :active-key="sortBy" :direction="sortOrder" @sort="applySort" /></template>
          <template #default="{ row }">{{ formatApplicationDateTime(row.last_login_at) }}</template>
        </el-table-column>
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
import { defineComponent, h, onMounted, ref } from 'vue'
import { ArrowDown, ArrowUp, Refresh, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchUsers, hideUser, type UserItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'
import PaginationFooter from '../components/PaginationFooter.vue'
import { useRouteRefresh } from '../utils/routeRefresh'
import { formatApplicationDateTime } from '../utils/applicationTime'

const keyword = ref('')
const showHidden = ref(false)
const page = ref(1)
const pageSize = ref(20)
const pageData = ref<PageData<UserItem> | null>(null)
const loading = ref(false)
type SortDirection = 'asc' | 'desc'
const sortBy = ref('')
const sortOrder = ref<SortDirection>('asc')

const SortHeader = defineComponent({
  props: {
    label: { type: String, required: true },
    sortKey: { type: String, required: true },
    activeKey: { type: String, required: true },
    direction: { type: String as () => SortDirection, required: true }
  },
  emits: { sort: (_key: string) => true },
  setup(props, { emit }) {
    return () => h('button', {
      type: 'button',
      class: ['sort-header', { 'is-active': props.activeKey === props.sortKey }],
      'aria-label': `${props.label}，${props.activeKey === props.sortKey ? (props.direction === 'asc' ? '当前升序，点击切换为降序' : '当前降序，点击切换为升序') : '点击排序'}`,
      onClick: () => emit('sort', props.sortKey)
    }, [
      h('span', props.label),
      props.activeKey === props.sortKey ? h(props.direction === 'asc' ? ArrowUp : ArrowDown, { class: 'sort-direction', 'aria-hidden': 'true' }) : null
    ])
  }
})

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

function applySort(key: string) {
  const defaultDirections: Record<string, SortDirection> = {
    username: 'asc',
    play_count: 'desc',
    watch_duration: 'desc',
    last_play_at: 'desc',
    last_login_at: 'desc'
  }
  if (!(key in defaultDirections)) return
  sortOrder.value = sortBy.value === key ? (sortOrder.value === 'asc' ? 'desc' : 'asc') : defaultDirections[key]
  sortBy.value = key
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

<style scoped>
:deep(.el-table th.el-table__cell) { padding: 0; }
.sort-header {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 5px;
  width: 100%;
  min-height: 44px;
  padding: 0 12px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  text-align: left;
}
.sort-header:hover, .sort-header.is-active { color: var(--app-accent); }
.sort-header:focus-visible { outline: 2px solid var(--app-accent); outline-offset: -3px; }
.sort-direction { width: 14px; height: 14px; flex: 0 0 auto; }
</style>
