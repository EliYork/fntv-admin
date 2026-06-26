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
        <el-descriptions-item v-if="status.fntv.error" label="错误代码">{{ status.fntv.error }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error_type" label="错误类型">{{ status.fntv.error_type }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error_message" label="错误描述">{{ status.fntv.error_message }}</el-descriptions-item>
      </el-descriptions>
      <EmptyState v-else description="正在等待数据库状态" />

      <el-alert
        v-if="status && status.fntv.readonly && !status.fntv.ok"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top: 12px"
      >
        <template #title>
          数据库已成功只读打开，挂载大概率正常。当前问题是飞牛数据库表结构与适配器不完全匹配。
        </template>
      </el-alert>
    </div>

    <div v-if="status && status.fntv.ok" class="table-panel section">
      <div class="panel-title">飞牛数据库诊断</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="检测到的表数量">{{ status.fntv.detected_table_count ?? 0 }}</el-descriptions-item>
        <el-descriptions-item label="用户表">{{ status.fntv.core_candidates?.user_table ?? '未识别' }}</el-descriptions-item>
        <el-descriptions-item label="媒体表">{{ status.fntv.core_candidates?.item_table ?? '未识别' }}</el-descriptions-item>
        <el-descriptions-item label="播放记录表">{{ status.fntv.core_candidates?.play_table ?? '未识别' }}</el-descriptions-item>
      </el-descriptions>

      <div class="sub-section">
        <div class="sub-title">核心表匹配状态</div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="用户表">
            <el-tag :type="status.fntv.required_tables_status?.user ? 'success' : 'danger'" size="small">
              {{ status.fntv.required_tables_status?.user ? '已匹配' : '未匹配' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="媒体表">
            <el-tag :type="status.fntv.required_tables_status?.item ? 'success' : 'danger'" size="small">
              {{ status.fntv.required_tables_status?.item ? '已匹配' : '未匹配' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="播放记录表">
            <el-tag :type="status.fntv.required_tables_status?.item_user_play ? 'success' : 'danger'" size="small">
              {{ status.fntv.required_tables_status?.item_user_play ? '已匹配' : '未匹配' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="sub-section">
        <div class="sub-title">功能支持</div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item v-for="(val, key) in capabilityLabels" :key="key" :label="val">
            <el-tag :type="hasCapability(key) ? 'success' : 'info'" size="small">
              {{ hasCapability(key) ? '支持' : '不支持' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="sub-section" v-if="status.fntv.detected_tables?.length">
        <div class="sub-title">检测到的表</div>
        <div class="table-list">
          <el-tag v-for="t in status.fntv.detected_tables" :key="t" size="small" class="table-tag">{{ t }}</el-tag>
        </div>
      </div>

      <div class="sub-section" v-if="status.fntv.detected_columns_by_table && Object.keys(status.fntv.detected_columns_by_table).length">
        <div class="sub-title">表字段详情</div>
        <el-collapse>
          <el-collapse-item v-for="(cols, tname) in status.fntv.detected_columns_by_table" :key="tname" :title="`${tname}（${cols.length} 个字段）`">
            <div class="column-list">
              <el-tag v-for="col in cols" :key="col" size="small" type="info" class="column-tag">{{ col }}</el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <div class="sub-section">
        <el-button size="small" @click="copyDiagnostics">复制诊断信息</el-button>
      </div>
    </div>

    <div v-if="status && !status.fntv.ok && status.fntv.readonly" class="table-panel section">
      <div class="panel-title">飞牛数据库诊断</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="检测到的表数量">{{ status.fntv.detected_table_count ?? 0 }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error_type" label="错误类型">{{ status.fntv.error_type }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error_message" label="错误描述">{{ status.fntv.error_message }}</el-descriptions-item>
      </el-descriptions>
      <div class="sub-section" v-if="status.fntv.detected_tables?.length">
        <div class="sub-title">检测到的表</div>
        <div class="table-list">
          <el-tag v-for="t in status.fntv.detected_tables" :key="t" size="small" class="table-tag">{{ t }}</el-tag>
        </div>
      </div>
      <div class="sub-section">
        <el-button size="small" @click="copyDiagnostics">复制诊断信息</el-button>
      </div>
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
import { ElMessage } from 'element-plus'
import { fetchDatabaseStatus, type DatabaseStatus } from '../api/system'
import EmptyState from '../components/EmptyState.vue'

const status = ref<DatabaseStatus | null>(null)
const theme = ref('system')

const capabilityLabels: Record<string, string> = {
  can_read_users: '读取用户列表',
  can_read_items: '读取媒体列表',
  can_read_play_history: '读取播放记录',
  can_join_user_names: '关联用户名',
  can_join_item_titles: '关联媒体标题',
  can_calculate_progress: '计算播放进度',
}

function hasCapability(key: string): boolean {
  return !!status.value?.fntv.capabilities?.[key]
}

async function loadStatus() {
  status.value = await fetchDatabaseStatus()
}

function copyDiagnostics() {
  if (!status.value) return
  const diag = {
    fntv: {
      ok: status.value.fntv.ok,
      exists: status.value.fntv.exists,
      readonly: status.value.fntv.readonly,
      error: status.value.fntv.error ?? null,
      error_type: status.value.fntv.error_type ?? null,
      error_message: status.value.fntv.error_message ?? null,
      detected_table_count: status.value.fntv.detected_table_count ?? 0,
      detected_tables: status.value.fntv.detected_tables ?? [],
      detected_columns_by_table: status.value.fntv.detected_columns_by_table ?? {},
      core_candidates: status.value.fntv.core_candidates ?? {},
      required_tables_status: status.value.fntv.required_tables_status ?? {},
      capabilities: status.value.fntv.capabilities ?? {},
    },
    admin: {
      exists: status.value.admin.exists,
      ok: status.value.admin.ok,
    },
  }
  navigator.clipboard.writeText(JSON.stringify(diag, null, 2)).then(() => {
    ElMessage.success('诊断信息已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败，请手动选择复制')
  })
}

onMounted(loadStatus)
</script>

<style scoped>
.settings-row {
  padding: 16px;
}
.sub-section {
  margin-top: 16px;
}
.sub-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 8px;
}
.table-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.table-tag {
  margin: 0;
}
.column-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.column-tag {
  margin: 0;
}
</style>
