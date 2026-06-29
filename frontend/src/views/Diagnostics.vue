<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">系统诊断</h1>
        <p class="page-subtitle">查看数据库状态、schema 识别和只读直连诊断信息</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadStatus">刷新</el-button>
        <el-button :icon="CopyDocument" :loading="copying" @click="copyDiagnostics">复制诊断信息</el-button>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title">数据源</div>
      <el-descriptions v-if="status" :column="1" border>
        <el-descriptions-item label="整体状态">
          <el-tag :type="databaseAvailabilityTag" size="small">{{ databaseAvailabilityLabel }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="源数据库路径">{{ status.fntv.source_path_container }}</el-descriptions-item>
        <el-descriptions-item label="源数据库存在">{{ status.fntv.source_exists ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="源数据库可读">{{ status.fntv.source_readable ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="只读配置">{{ status.fntv.source_readonly_configured ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="源库直读">{{ sourceDirectLabel }}</el-descriptions-item>
      </el-descriptions>
      <EmptyState v-else description="正在等待数据库状态" />
    </div>

    <div class="table-panel section">
      <div class="panel-title">登录态诊断</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="认证已初始化">{{ auth.checked ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="浏览器保存 Token">{{ auth.hasToken ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="当前用户">{{ auth.user?.username ?? '未加载' }}</el-descriptions-item>
        <el-descriptions-item label="认证模式">{{ auth.user?.auth_mode ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="本地请求">{{ auth.user?.is_local_request === undefined ? '-' : auth.user.is_local_request ? '是' : '否' }}</el-descriptions-item>
        <el-descriptions-item label="本地访问策略">{{ auth.user?.local_auth_required === undefined ? '-' : auth.user.local_auth_required ? '需要登录' : '免登录' }}</el-descriptions-item>
        <el-descriptions-item label="外部访问策略">{{ auth.user?.remote_access_policy === 'deny' ? '禁止访问' : auth.user?.remote_access_policy === 'login' ? '需要登录' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近认证错误接口">{{ auth.lastAuthErrorEndpoint || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最近认证错误状态">{{ auth.lastAuthErrorStatus ?? '-' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <div v-if="status" class="table-panel section">
      <div class="panel-title">快照</div>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="快照状态">
          <el-tag type="info" size="small">已禁用</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="当前数据源">
          <el-tag :type="activeDatabaseTag" size="small">{{ activeDatabaseLabel }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
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
        v-if="status.fntv.availability === 'unavailable'"
        type="error"
        show-icon
        :closable="false"
        style="margin-top: 12px"
      >
        <template #title>
          源库只读直连失败。请检查 `/fntv/trimmedia.db` 挂载路径和权限。
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

    <el-dialog v-model="copyDialogVisible" title="手动复制诊断信息" width="560px" @opened="selectCopyText">
      <p style="margin-bottom: 8px; color: #e6a23c; font-size: 13px;">浏览器限制了自动复制，请按 Ctrl+C 手动复制</p>
      <el-input ref="copyTextareaRef" v-model="copyText" type="textarea" :rows="16" readonly />
      <template #footer>
        <el-button @click="copyDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CopyDocument, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchDatabaseStatusDetail, type DatabaseStatus } from '../api/system'
import EmptyState from '../components/EmptyState.vue'
import { useRouteRefresh } from '../utils/routeRefresh'
import { useAuthStore } from '../stores/auth'

const status = ref<DatabaseStatus | null>(null)
const loading = ref(false)
const copying = ref(false)
const copyDialogVisible = ref(false)
const copyText = ref('')
const copyTextareaRef = ref<InstanceType<typeof import('element-plus')['ElInput']> | null>(null)
const auth = useAuthStore()

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
  if (v) return '成功'
  return '失败'
})

const databaseAvailabilityLabel = computed(() => {
  if (!status.value) return '-'
  if (status.value.fntv.availability === 'available') return '飞牛数据库正常'
  return '飞牛数据库异常'
})

const databaseAvailabilityTag = computed(() => {
  if (!status.value) return 'info'
  if (status.value.fntv.availability === 'available') return 'success'
  return 'danger'
})

const activeDatabaseLabel = computed(() => {
  if (!status.value) return '-'
  const v = status.value.fntv.active_database
  if (v === 'source') return '源库只读直连'
  return '未连接'
})

const activeDatabaseTag = computed(() => {
  if (!status.value) return 'info'
  const v = status.value.fntv.active_database
  if (v === 'source') return 'success'
  return 'danger'
})

function hasCapability(key: string): boolean {
  return !!status.value?.fntv.capabilities?.[key]
}

async function loadStatus() {
  loading.value = true
  try {
    status.value = await fetchDatabaseStatusDetail()
  } finally {
    loading.value = false
  }
}

function buildDiagnosticsJson(source: DatabaseStatus | null = status.value): string {
  if (!source) return '{}'
  const diag = {
    fntv: {
      ok: source.fntv.ok,
      source_exists: source.fntv.source_exists,
      source_readable: source.fntv.source_readable,
      source_direct_ok: source.fntv.source_direct_ok,
      active_database: source.fntv.active_database,
      active_db_path: source.fntv.active_db_path ?? null,
      availability: source.fntv.availability ?? null,
      snapshot_enabled: source.fntv.snapshot_enabled ?? false,
      error: source.fntv.error ?? null,
      error_type: source.fntv.error_type ?? null,
      error_message: source.fntv.error_message ?? null,
      detected_table_count: source.fntv.detected_table_count ?? 0,
      detected_tables: source.fntv.detected_tables ?? [],
      detected_columns_by_table: source.fntv.detected_columns_by_table ?? {},
      core_candidates: source.fntv.core_candidates ?? {},
      required_tables_status: source.fntv.required_tables_status ?? {},
      capabilities: source.fntv.capabilities ?? {},
    },
    admin: {
      exists: source.admin.exists,
      ok: source.admin.ok,
    },
  }
  return JSON.stringify(diag, null, 2)
}

async function copyDiagnostics() {
  copying.value = true
  try {
    const source = status.value || await fetchDatabaseStatusDetail()
    status.value = source
    const text = buildDiagnosticsJson(source)
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('已复制诊断信息')
      } catch {
        copyText.value = text
        copyDialogVisible.value = true
        ElMessage.warning('浏览器限制了自动复制，请按 Ctrl+C 手动复制')
      }
    } else {
      copyText.value = text
      copyDialogVisible.value = true
      ElMessage.warning('浏览器限制了自动复制，请按 Ctrl+C 手动复制')
    }
  } finally {
    copying.value = false
  }
}

function selectCopyText() {
  setTimeout(() => {
    const textarea = copyTextareaRef.value?.$el?.querySelector('textarea')
    if (textarea) {
      textarea.focus()
      textarea.select()
    }
  }, 50)
}

onMounted(loadStatus)
useRouteRefresh(loadStatus)
</script>

<style scoped>
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
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
