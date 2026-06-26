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
      <div class="panel-title">数据源</div>
      <el-descriptions v-if="status" :column="1" border>
        <el-descriptions-item label="源数据库路径">{{ status.fntv.source_path_container }}</el-descriptions-item>
        <el-descriptions-item label="源数据库存在">{{ status.fntv.source_exists ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="源数据库可读">{{ status.fntv.source_readable ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="只读配置">{{ status.fntv.source_readonly_configured ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="源库直读">{{ sourceDirectLabel }}</el-descriptions-item>
      </el-descriptions>
      <EmptyState v-else description="正在等待数据库状态" />
    </div>

    <div v-if="status" class="table-panel section">
      <div class="panel-title">快照</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="快照路径">{{ status.fntv.snapshot_path_container }}</el-descriptions-item>
        <el-descriptions-item label="快照目录存在">{{ status.fntv.snapshot_dir_exists ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="快照目录可写">{{ status.fntv.snapshot_dir_writable ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="快照文件存在">{{ status.fntv.snapshot_exists ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="快照状态">
          <el-tag :type="status.fntv.snapshot_ok ? 'success' : 'danger'" size="small">
            {{ status.fntv.snapshot_ok ? '正常' : '异常' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="最近刷新">{{ snapshotRefreshLabel }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.snapshot_error" label="快照错误">{{ status.fntv.snapshot_error }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.snapshot_error_type" label="错误类型">{{ status.fntv.snapshot_error_type }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.snapshot_error_message" label="错误详情">{{ status.fntv.snapshot_error_message }}</el-descriptions-item>
        <el-descriptions-item label="当前数据源">
          <el-tag :type="activeDatabaseTag" size="small">{{ activeDatabaseLabel }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div class="sub-section">
        <el-button type="primary" size="small" :loading="refreshing" @click="doRefresh">刷新快照</el-button>
      </div>
    </div>

    <div v-if="status" class="table-panel section">
      <div class="panel-title">诊断结果</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="schema 探测">
          <el-tag :type="status.fntv.ok ? 'success' : 'danger'" size="small">
            {{ status.fntv.ok ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error" label="错误代码">{{ status.fntv.error }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error_type" label="错误类型">{{ status.fntv.error_type }}</el-descriptions-item>
        <el-descriptions-item v-if="status.fntv.error_message" label="错误描述">{{ status.fntv.error_message }}</el-descriptions-item>
        <el-descriptions-item label="admin.db">{{ status.admin.exists ? '已初始化' : '未创建' }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-if="status.fntv.source_direct_ok === false && status.fntv.snapshot_ok && status.fntv.ok"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top: 12px"
      >
        <template #title>
          源库直读失败，但快照读取成功。这通常是因为飞牛数据库处于 WAL 模式或目录权限限制，不影响正常使用。
        </template>
      </el-alert>

      <el-alert
        v-if="status.fntv.source_direct_ok === false && !status.fntv.snapshot_ok"
        type="error"
        show-icon
        :closable="false"
        style="margin-top: 12px"
      >
        <template #title>
          源库直读失败，快照也不可用。请检查挂载路径和权限，或尝试手动刷新快照。
        </template>
      </el-alert>

      <el-alert
        v-if="status.fntv.source_direct_ok === true && !status.fntv.snapshot_ok"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top: 12px"
      >
        <template #title>
          快照创建失败，但源库直读正常。当前使用源库只读直连，不影响基本功能。快照错误：{{ status.fntv.snapshot_error_message || status.fntv.snapshot_error }}
        </template>
      </el-alert>
    </div>

    <div v-if="status && status.fntv.ok" class="table-panel section">
      <div class="panel-title">飞牛数据库表结构</div>
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

    <div v-if="status && !status.fntv.ok" class="table-panel section">
      <div class="panel-title">飞牛数据库表结构</div>
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

    <el-dialog v-model="copyDialogVisible" title="手动复制诊断信息" width="560px">
      <el-input v-model="copyText" type="textarea" :rows="16" readonly />
      <template #footer>
        <el-button @click="copyDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchDatabaseStatus, refreshSnapshot, type DatabaseStatus } from '../api/system'
import EmptyState from '../components/EmptyState.vue'

const status = ref<DatabaseStatus | null>(null)
const theme = ref('system')
const refreshing = ref(false)
const copyDialogVisible = ref(false)
const copyText = ref('')

const capabilityLabels: Record<string, string> = {
  can_read_users: '读取用户列表',
  can_read_items: '读取媒体列表',
  can_read_play_history: '读取播放记录',
  can_join_user_names: '关联用户名',
  can_join_item_titles: '关联媒体标题',
  can_calculate_progress: '计算播放进度',
}

const sourceDirectLabel = computed(() => {
  if (!status.value) return '-'
  const v = status.value.fntv.source_direct_ok
  if (v === null) return '未检测'
  return v ? '成功' : '失败（使用快照）'
})

const snapshotRefreshLabel = computed(() => {
  if (!status.value) return '-'
  const ts = status.value.fntv.snapshot_last_refresh_at
  if (!ts) return '未刷新'
  return new Date(ts * 1000).toLocaleString()
})

const activeDatabaseLabel = computed(() => {
  if (!status.value) return '-'
  const v = status.value.fntv.active_database
  if (v === 'snapshot') return '快照'
  if (v === 'source') return '源库直连（降级）'
  return '未连接'
})

const activeDatabaseTag = computed(() => {
  if (!status.value) return 'info'
  const v = status.value.fntv.active_database
  if (v === 'snapshot') return 'success'
  if (v === 'source') return 'warning'
  return 'danger'
})

function hasCapability(key: string): boolean {
  return !!status.value?.fntv.capabilities?.[key]
}

async function loadStatus() {
  status.value = await fetchDatabaseStatus()
}

async function doRefresh() {
  refreshing.value = true
  try {
    const result = await refreshSnapshot()
    if (result.ok) {
      ElMessage.success('快照刷新成功')
    } else {
      ElMessage.error(`快照刷新失败: ${result.error}`)
    }
  } catch {
    ElMessage.error('快照刷新请求失败')
  } finally {
    refreshing.value = false
    await loadStatus()
  }
}

function buildDiagnosticsJson(): string {
  if (!status.value) return '{}'
  const diag = {
    fntv: {
      ok: status.value.fntv.ok,
      source_exists: status.value.fntv.source_exists,
      source_readable: status.value.fntv.source_readable,
      source_direct_ok: status.value.fntv.source_direct_ok,
      active_database: status.value.fntv.active_database,
      fallback_to_source: status.value.fntv.fallback_to_source,
      snapshot_exists: status.value.fntv.snapshot_exists,
      snapshot_dir_exists: status.value.fntv.snapshot_dir_exists,
      snapshot_dir_writable: status.value.fntv.snapshot_dir_writable,
      snapshot_ok: status.value.fntv.snapshot_ok,
      snapshot_error: status.value.fntv.snapshot_error ?? null,
      snapshot_error_type: status.value.fntv.snapshot_error_type ?? null,
      snapshot_error_message: status.value.fntv.snapshot_error_message ?? null,
      snapshot_last_refresh_at: status.value.fntv.snapshot_last_refresh_at,
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
  return JSON.stringify(diag, null, 2)
}

function copyDiagnostics() {
  const text = buildDiagnosticsJson()
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    navigator.clipboard.writeText(text).then(() => {
      ElMessage.success('诊断信息已复制到剪贴板')
    }).catch(() => {
      copyText.value = text
      copyDialogVisible.value = true
    })
  } else {
    copyText.value = text
    copyDialogVisible.value = true
  }
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
