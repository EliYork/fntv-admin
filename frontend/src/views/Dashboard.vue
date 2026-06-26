<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">飞牛影视数据概览和最近播放活动</p>
      </div>
      <el-button :icon="Refresh" @click="loadData">刷新</el-button>
    </div>

    <div v-if="overview?.error" class="error-panel">{{ overview.error }}</div>

    <div class="metrics section">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </div>
    </div>

    <div class="table-panel">
      <div class="panel-title">最近活动</div>
      <el-table v-if="activities.length" :data="activities" height="360">
        <el-table-column prop="user" label="用户" min-width="140" />
        <el-table-column prop="title" label="媒体" min-width="220" />
        <el-table-column prop="played_at" label="播放时间" min-width="160" />
        <el-table-column prop="progress" label="进度" width="120" />
      </el-table>
      <EmptyState v-else description="暂无播放活动或未识别播放记录表" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { fetchDashboardOverview, fetchRecentActivities, type DashboardOverview, type HistoryItem } from '../api/modules'
import EmptyState from '../components/EmptyState.vue'

const overview = ref<DashboardOverview | null>(null)
const activities = ref<HistoryItem[]>([])

const metrics = computed(() => [
  { label: '总用户数', value: overview.value?.total_users ?? 0 },
  { label: '总媒体数', value: overview.value?.total_media ?? 0 },
  { label: '播放记录', value: overview.value?.total_play_records ?? 0 },
  { label: '今日播放', value: overview.value?.today_plays ?? 0 }
])

async function loadData() {
  overview.value = await fetchDashboardOverview()
  activities.value = await fetchRecentActivities()
}

onMounted(loadData)
</script>

