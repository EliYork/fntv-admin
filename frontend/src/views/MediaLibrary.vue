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
      <el-input v-model="keyword" placeholder="搜索媒体标题" style="width: 280px" clearable @keyup.enter="loadData" />
      <el-select v-model="mediaType" placeholder="媒体类型" clearable style="width: 160px">
        <el-option label="全部" value="" />
        <el-option label="电影" value="movie" />
        <el-option label="剧集" value="episode" />
      </el-select>
    </div>
    <div v-if="pageData?.error" class="error-panel">{{ pageData.error }}</div>
    <div class="table-panel">
      <el-table v-if="pageData?.items.length" v-loading="loading" :data="pageData.items">
        <el-table-column prop="title" label="标题" min-width="220" />
        <el-table-column prop="media_type" label="类型" width="110" />
        <el-table-column prop="runtime" label="时长" width="110" />
        <el-table-column prop="parent" label="父级" min-width="160" />
        <el-table-column prop="play_count" label="播放次数" width="110" />
        <el-table-column prop="note" label="备注" min-width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" text @click="toggleHidden(row.guid, !row.hidden)">
              {{ row.hidden ? '恢复' : '隐藏' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else description="暂无媒体数据或未识别媒体表" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchMedia, hideMedia, type MediaItem } from '../api/modules'
import type { PageData } from '../types/api'
import EmptyState from '../components/EmptyState.vue'

const keyword = ref('')
const mediaType = ref('')
const pageData = ref<PageData<MediaItem> | null>(null)
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    pageData.value = await fetchMedia({ page: 1, page_size: 20, keyword: keyword.value, media_type: mediaType.value })
  } finally {
    loading.value = false
  }
}

async function toggleHidden(guid: string, hidden: boolean) {
  await hideMedia(guid, hidden)
  ElMessage.success(hidden ? '已隐藏媒体' : '已恢复媒体')
  await loadData()
}

onMounted(loadData)
</script>
