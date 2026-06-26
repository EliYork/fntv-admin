<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-subtitle">配置保存到 admin.db，飞牛数据库路径仅展示容器内路径</p>
      </div>
      <el-button :icon="Refresh" @click="loadStatus">刷新状态</el-button>
    </div>

    <div class="table-panel section">
      <div class="panel-title">数据库状态</div>
      <el-descriptions v-if="status" :column="1" border>
        <el-descriptions-item label="飞牛数据库">{{ status.fntv.ok ? '正常' : '异常' }}</el-descriptions-item>
        <el-descriptions-item label="只读连接">{{ status.fntv.readonly ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="admin.db">{{ status.admin.exists ? '已初始化' : '未创建' }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error" label="错误">{{ status.fntv.error }}</el-descriptions-item>
      </el-descriptions>
      <EmptyState v-else description="正在等待数据库状态" />
    </div>

    <div class="table-panel">
      <div class="panel-title">主题</div>
      <div class="settings-row">
        <el-radio-group v-model="theme">
          <el-radio-button label="system">跟随系统</el-radio-button>
          <el-radio-button label="light">浅色</el-radio-button>
          <el-radio-button label="dark">深色</el-radio-button>
        </el-radio-group>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { fetchDatabaseStatus, type DatabaseStatus } from '../api/system'
import EmptyState from '../components/EmptyState.vue'

const status = ref<DatabaseStatus | null>(null)
const theme = ref('system')

async function loadStatus() {
  status.value = await fetchDatabaseStatus()
}

onMounted(loadStatus)
</script>

<style scoped>
.settings-row {
  padding: 16px;
}
</style>

