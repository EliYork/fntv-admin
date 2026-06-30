<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">仪表盘</h1>
        <p class="page-subtitle">飞牛影视数据概览和最近播放活动</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <div v-if="overview?.error" class="error-panel">{{ overview.error }}</div>

    <div class="metrics section">
      <div v-for="item in metrics" :key="item.label" class="metric-card">
        <div class="metric-label">{{ item.label }}</div>
        <div class="metric-value">{{ item.value }}</div>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title panel-title-row">
        <span>播放热点</span>
        <span class="panel-note">首页展示最近 90 天播放活跃度，可切换查看一周时段习惯。</span>
      </div>
      <div class="panel-body dashboard-heatmap-body" v-loading="loading">
        <div v-if="heatmapError" class="inline-warning">{{ heatmapError }}</div>
        <PlaybackHeatmap :date-items="trendItems" :weekly-items="weeklyItems" :modes="['date', 'weekhour']" weekday-range-label="最近 90 天，按星期与小时聚合" />
      </div>
    </div>

    <div class="table-panel">
      <div class="panel-title panel-title-row">
        <span>更多</span>
        <el-button size="small" text :icon="showMore ? ArrowUp : ArrowDown" @click="showMore = !showMore">
          {{ showMore ? '收起' : '展开' }}
        </el-button>
      </div>
      <div v-if="showMore" class="dashboard-more">
        <section class="more-section">
          <div class="more-section-title">
            <span>最近活跃观看</span>
            <span class="panel-note">根据最近 5 分钟播放记录推断，非实时会话。</span>
          </div>
          <el-table v-if="activeWatches.length" v-loading="loading" :data="activeWatches">
            <el-table-column prop="username" label="用户" min-width="150" />
            <el-table-column prop="display_title" label="媒体" min-width="260" />
            <el-table-column prop="last_updated_at" label="最近更新" min-width="160" />
            <el-table-column prop="progress" label="进度" width="130" />
            <el-table-column prop="resolution" label="分辨率" width="110" />
          </el-table>
          <EmptyState v-else description="暂无最近活跃观看" />
        </section>

        <section class="more-section">
          <div class="more-section-title">
            <span>最近 20 条活动</span>
            <el-button size="small" text :icon="ArrowRight" @click="router.push('/history')">查看更多</el-button>
          </div>
          <el-table v-if="activities.length" v-loading="loading" :data="activities">
            <el-table-column label="用户" min-width="160">
              <template #default="{ row }">
                <span>{{ row.username || row.user || '-' }}</span>
                <div v-if="row.username === row.user_guid" class="muted-guid">{{ row.user_guid }}</div>
              </template>
            </el-table-column>
            <el-table-column label="媒体" min-width="260">
              <template #default="{ row }">
                <span>{{ row.display_title || row.title || '-' }}</span>
                <div v-if="row.display_title === row.item_guid" class="muted-guid">{{ row.item_guid }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="played_at" label="播放时间" min-width="160" />
            <el-table-column prop="progress" label="进度" width="120" />
          </el-table>
          <EmptyState v-else description="暂无播放活动或未识别播放记录表" />
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, ArrowRight, ArrowUp, Refresh } from '@element-plus/icons-vue'
import {
  fetchActiveWatches,
  fetchDashboardOverview,
  fetchRecentActivities,
  fetchReportPlayTrend,
  fetchReportWeeklyHourlyDistribution,
  type ActiveWatchItem,
  type DashboardOverview,
  type HistoryItem,
  type PlayTrendItem,
  type WeeklyHourlyDistributionItem
} from '../api/modules'
import EmptyState from '../components/EmptyState.vue'
import PlaybackHeatmap from '../components/PlaybackHeatmap.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const router = useRouter()
const overview = ref<DashboardOverview | null>(null)
const activities = ref<HistoryItem[]>([])
const activeWatches = ref<ActiveWatchItem[]>([])
const trendItems = ref<PlayTrendItem[]>([])
const weeklyItems = ref<WeeklyHourlyDistributionItem[]>([])
const heatmapError = ref('')
const showMore = ref(false)
const loading = ref(false)

const metrics = computed(() => [
  { label: '总用户数', value: overview.value?.total_users ?? 0 },
  { label: '总媒体数', value: overview.value?.total_media ?? 0 },
  { label: '播放记录', value: overview.value?.total_play_records ?? 0 },
  { label: '今日播放', value: overview.value?.today_plays ?? 0 }
])

async function loadData() {
  loading.value = true
  heatmapError.value = ''
  try {
    overview.value = await fetchDashboardOverview()
    const [active, recent, trend, weekly] = await Promise.allSettled([
      fetchActiveWatches(300),
      fetchRecentActivities(20),
      fetchReportPlayTrend(90),
      fetchReportWeeklyHourlyDistribution(90)
    ])
    activeWatches.value = active.status === 'fulfilled' ? active.value : []
    activities.value = recent.status === 'fulfilled' ? recent.value : []
    trendItems.value = trend.status === 'fulfilled' ? trend.value : []
    weeklyItems.value = weekly.status === 'fulfilled' ? weekly.value : []
    if (trend.status === 'rejected' || weekly.status === 'rejected') {
      heatmapError.value = '播放热点加载失败，其他首页数据不受影响'
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
useRouteRefresh(loadData)
</script>

<style scoped>
.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-note {
  color: var(--app-muted);
  font-size: 12px;
  font-weight: 400;
}

.panel-body {
  padding: 14px 16px;
}

.dashboard-heatmap-body {
  min-height: 250px;
}

.dashboard-more {
  display: grid;
  gap: 18px;
  padding: 14px 16px 18px;
}

.more-section {
  min-width: 0;
}

.more-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-weight: 650;
  color: var(--app-title);
}

.inline-warning {
  margin-bottom: 10px;
  padding: 9px 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 13px;
}

[data-theme='dark'] .inline-warning {
  border-color: #7c2d12;
  background: #2f1d12;
  color: #fdba74;
}

@media (max-width: 640px) {
  .more-section-title {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
