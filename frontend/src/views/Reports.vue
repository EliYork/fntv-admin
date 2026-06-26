<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">报表中心</h1>
        <p class="page-subtitle">基础报表入口已预留，复杂统计将在稳定表结构适配后接入</p>
      </div>
    </div>
    <div class="metrics section">
      <div v-for="item in reports" :key="item" class="metric-card">
        <div class="metric-label">{{ item }}</div>
        <div class="metric-value">0</div>
      </div>
    </div>
    <div class="table-panel">
      <div class="panel-title">报表数据</div>
      <EmptyState description="暂无报表缓存或飞牛数据库表结构尚未适配" />
    </div>
  </section>
</template>

<script setup lang="ts">
import EmptyState from '../components/EmptyState.vue'

const reports = ['每日趋势', '用户排行', '媒体排行', '分辨率统计']
</script>

