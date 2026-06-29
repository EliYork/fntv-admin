<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">媒体库</h1>
        <p class="page-subtitle">媒体备注和隐藏状态仅写入 admin.db</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索媒体标题" style="width: 280px" clearable @clear="applyFilters" @keyup.enter="applyFilters" />
      <el-select v-model="mediaType" placeholder="媒体类型" clearable style="width: 180px" @change="applyFilters" @clear="applyFilters">
        <el-option label="全部" value="" />
        <el-option label="电影" value="Movie" />
        <el-option label="剧集" value="Series" />
        <el-option label="季" value="Season" />
        <el-option label="单集" value="Episode" />
      </el-select>
      <el-button :icon="Search" type="primary" :loading="loading" @click="applyFilters">筛选</el-button>
    </div>
    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column label="标题" min-width="260">
          <template #default="{ row }">
            <span>{{ row.title || '-' }}</span>
            <div v-if="row.title === row.guid" class="muted-guid">{{ row.guid }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">{{ mediaTypeLabel(row.media_type) }}</template>
        </el-table-column>
        <el-table-column prop="runtime" label="时长" width="110" />
        <el-table-column prop="parent" label="父级" min-width="160" />
        <el-table-column prop="play_count" label="播放次数" width="110" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text @click="toggleHidden(row.guid, !row.hidden)">
              {{ row.hidden ? '恢复' : '隐藏' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else description="暂无媒体数据或未识别媒体表" />
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
import { fetchMedia, hideMedia, type MediaItem } from '../api/modules'
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

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchMedia({ page: page.value, page_size: pageSize.value, keyword: keyword.value, media_type: mediaType.value })
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

async function toggleHidden(guid: string, hidden: boolean) {
  await hideMedia(guid, hidden)
  ElMessage.success(hidden ? '已隐藏媒体' : '已恢复媒体')
  page.value = 1
  await loadData()
}

function mediaTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    Movie: '电影',
    Series: '剧集',
    TV: '剧集',
    Season: '季',
    Episode: '单集',
    Video: '视频',
    Directory: '目录',
    MediaDB: '媒体库'
  }
  return labels[type] || type || '未知'
}

onMounted(loadData)
useRouteRefresh(loadData)
</script>
