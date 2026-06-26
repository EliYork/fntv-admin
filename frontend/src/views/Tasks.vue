<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">任务中心</h1>
        <p class="page-subtitle">任务记录将写入 admin.db，不触碰飞牛数据库</p>
      </div>
      <el-button :icon="Refresh" @click="runHealthCheck">健康检查</el-button>
    </div>
    <div class="table-panel">
      <div class="panel-title">任务列表</div>
      <EmptyState description="暂无任务记录" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import EmptyState from '../components/EmptyState.vue'

function runHealthCheck() {
  ElMessage.success('健康检查任务入口已预留')
}
</script>
