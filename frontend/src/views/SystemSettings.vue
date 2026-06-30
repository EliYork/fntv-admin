<template>
  <section>
    <div class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <p class="page-subtitle">主题偏好保存在本地浏览器，诊断信息已移到系统诊断页</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="refreshSettings">刷新设置</el-button>
    </div>

    <div class="table-panel section">
      <div class="panel-title">主题</div>
      <div class="settings-row">
        <el-radio-group v-model="themeMode">
          <el-radio-button label="system">跟随系统</el-radio-button>
          <el-radio-button label="light">浅色</el-radio-button>
          <el-radio-button label="dark">深色</el-radio-button>
        </el-radio-group>
        <span class="theme-current">当前：{{ currentThemeLabel }}</span>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title">访问控制</div>
      <div class="settings-stack" v-loading="authPolicyLoading">
        <el-alert
          title="本地免登录仅建议在可信内网使用；如果通过公网、DDNS 或反向代理访问，请保持外部访问需要登录或直接禁止外部访问。"
          type="warning"
          show-icon
          :closable="false"
        />
        <div class="settings-row">
          <span class="setting-label">本地访问</span>
          <el-radio-group v-model="localAuthRequired">
            <el-radio-button :label="true">需要登录</el-radio-button>
            <el-radio-button :label="false">免登录</el-radio-button>
          </el-radio-group>
        </div>
        <div class="settings-row">
          <span class="setting-label">外部访问</span>
          <el-radio-group v-model="remoteAccessPolicy">
            <el-radio-button label="login">需要登录</el-radio-button>
            <el-radio-button label="deny">禁止访问</el-radio-button>
          </el-radio-group>
        </div>
        <div class="settings-note">
          <div>{{ accessControlSummary }}</div>
          <div>当前请求：{{ authPolicy?.is_local_request ? '本地访问' : '外部访问或未知' }}</div>
          <div>代理头：{{ authPolicy?.trust_proxy_headers ? '已信任 X-Forwarded-For / X-Real-IP' : '未信任代理头' }}</div>
        </div>
        <div class="settings-actions">
          <el-button type="primary" :loading="authPolicySaving" @click="saveAuthPolicy">保存访问控制</el-button>
        </div>
      </div>
    </div>

    <div class="table-panel section">
      <div class="panel-title">数据读取</div>
      <div class="settings-stack">
        <el-alert
          title="快照读取是可选增强。快照只写入 /data/cache，失败时自动回退源库只读直连。"
          type="info"
          show-icon
          :closable="false"
        />
        <div class="settings-row">
          <span class="setting-label">快照读取</span>
          <el-switch v-model="snapshotEnabled" active-text="启用" inactive-text="关闭" />
        </div>
        <div class="settings-actions">
          <el-button type="primary" :loading="snapshotSaving" @click="saveSnapshotSetting">保存数据读取设置</el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { fetchAppSettings, fetchAuthPolicy, updateAuthPolicy, updateSnapshotSetting, type AuthPolicy, type RemoteAccessPolicy } from '../api/auth'
import { useThemeStore, type ThemeMode } from '../stores/theme'
import { useAuthStore } from '../stores/auth'
import { useRouteRefresh } from '../utils/routeRefresh'

const theme = useThemeStore()
const auth = useAuthStore()
const loading = ref(false)
const authPolicyLoading = ref(false)
const authPolicySaving = ref(false)
const authPolicy = ref<AuthPolicy | null>(null)
const localAuthRequired = ref(true)
const remoteAccessPolicy = ref<RemoteAccessPolicy>('login')
const snapshotEnabled = ref(false)
const snapshotSaving = ref(false)
theme.init()

const themeMode = computed({
  get: () => theme.mode,
  set: (value: ThemeMode) => theme.setMode(value)
})

const currentThemeLabel = computed(() => {
  if (theme.mode === 'system') {
    return theme.resolved === 'dark' ? '跟随系统（深色）' : '跟随系统（浅色）'
  }
  return theme.mode === 'dark' ? '深色' : '浅色'
})

const accessControlSummary = computed(() => {
  if (localAuthRequired.value && remoteAccessPolicy.value === 'login') {
    return '当前本地和外部访问均需要登录。'
  }
  if (!localAuthRequired.value && remoteAccessPolicy.value === 'login') {
    return '当前本地访问免登录，外部访问需要登录。'
  }
  if (localAuthRequired.value && remoteAccessPolicy.value === 'deny') {
    return '当前本地访问需要登录，外部访问禁止访问。'
  }
  return '当前本地访问免登录，外部访问禁止访问。'
})

async function refreshSettings() {
  loading.value = true
  try {
    theme.reload()
    await Promise.all([loadAuthPolicy(), loadAppSettings()])
  } finally {
    loading.value = false
  }
}

async function loadAppSettings() {
  const appSettings = await fetchAppSettings()
  snapshotEnabled.value = String(appSettings.snapshot_enabled || 'false').toLowerCase() === 'true'
}

async function loadAuthPolicy() {
  authPolicyLoading.value = true
  try {
    authPolicy.value = await fetchAuthPolicy()
    localAuthRequired.value = authPolicy.value.local_auth_required
    remoteAccessPolicy.value = authPolicy.value.remote_access_policy
  } finally {
    authPolicyLoading.value = false
  }
}

async function saveAuthPolicy() {
  authPolicySaving.value = true
  try {
    authPolicy.value = await updateAuthPolicy({
      local_auth_required: localAuthRequired.value,
      remote_access_policy: remoteAccessPolicy.value
    })
    await auth.loadMe(true)
    ElMessage.success('访问控制已更新')
  } finally {
    authPolicySaving.value = false
  }
}

async function saveSnapshotSetting() {
  snapshotSaving.value = true
  try {
    const result = await updateSnapshotSetting(snapshotEnabled.value)
    snapshotEnabled.value = result.snapshot_enabled
    ElMessage.success('数据读取设置已更新')
  } finally {
    snapshotSaving.value = false
  }
}

onMounted(refreshSettings)
useRouteRefresh(refreshSettings)
</script>

<style scoped>
.settings-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 14px;
  padding: 16px;
}

.theme-current {
  color: var(--app-muted);
}

.settings-stack {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.setting-label {
  width: 80px;
  color: var(--app-title);
  font-weight: 600;
}

.settings-note {
  display: grid;
  gap: 4px;
  color: var(--app-muted);
  font-size: 13px;
}

.settings-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
