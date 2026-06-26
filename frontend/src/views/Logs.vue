<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">日志中心</h1>
        <p class="page-subtitle">日志读取范围限定在 /data/logs</p>
      </div>
      <el-button :icon="Delete">清理旧日志</el-button>
    </div>
    <div class="toolbar">
      <el-select v-model="level" placeholder="日志等级" style="width: 160px">
        <el-option label="全部" value="" />
        <el-option label="INFO" value="INFO" />
        <el-option label="ERROR" value="ERROR" />
      </el-select>
    </div>
    <div class="table-panel">
      <div class="panel-title">运行日志</div>
      <EmptyState description="暂无可展示日志" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import EmptyState from '../components/EmptyState.vue'

const level = ref('')
</script>

