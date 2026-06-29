<template>
  <el-container class="admin-shell">
    <el-aside class="admin-aside" width="232px">
      <div class="brand">fntv-admin</div>
      <el-menu :default-active="route.path" class="nav-menu" @select="handleMenuSelect">
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="admin-content">
      <el-header class="topbar">
        <div class="status-row">
          <el-tag :type="databaseStatusType" effect="light">
            {{ databaseStatusLabel }}
          </el-tag>
          <span class="refresh-time">刷新：{{ refreshedAt }}</span>
        </div>
        <div class="user-row">
          <el-switch v-model="darkMode" inline-prompt active-text="暗" inactive-text="亮" />
          <el-tag v-if="auth.isLocalNoAuth" size="small" type="warning" effect="light">本地模式</el-tag>
          <span>{{ auth.user?.username || 'admin' }}</span>
          <el-button v-if="!auth.isLocalNoAuth" size="small" :icon="SwitchButton" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main-view">
        <router-view />
      </el-main>
    </el-container>

    <el-drawer v-model="drawerVisible" title="详情" size="360px">
      <p class="drawer-text">详情抽屉已预留，用户、媒体和历史详情会在后续迭代接入。</p>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataAnalysis, Document, Film, HomeFilled, Monitor, Setting, SwitchButton, User } from '@element-plus/icons-vue'
import { fetchDatabaseStatus } from '../api/system'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const theme = useThemeStore()
const databaseChecking = ref(true)
const databaseOk = ref(false)
const refreshedAt = ref('-')
const drawerVisible = ref(false)
theme.init()

const darkMode = computed({
  get: () => theme.resolved === 'dark',
  set: (enabled: boolean) => theme.setMode(enabled ? 'dark' : 'light')
})

const navItems = [
  { path: '/dashboard', label: '仪表盘', icon: HomeFilled },
  { path: '/history', label: '观看历史', icon: Document },
  { path: '/users', label: '用户管理', icon: User },
  { path: '/media', label: '媒体库', icon: Film },
  { path: '/reports', label: '报表中心', icon: DataAnalysis },
  { path: '/settings', label: '系统设置', icon: Setting },
  { path: '/diagnostics', label: '系统诊断', icon: Monitor }
]

const databaseStatusType = computed(() => {
  if (databaseChecking.value) return 'info'
  if (databaseOk.value) return 'success'
  return 'danger'
})

const databaseStatusLabel = computed(() => {
  if (databaseChecking.value) return '检查中'
  if (databaseOk.value) return '飞牛数据库正常'
  return '飞牛数据库异常'
})

async function refreshDatabaseStatus() {
  try {
    const status = await fetchDatabaseStatus()
    databaseOk.value = status.fntv.availability === 'available'
  } catch {
    databaseOk.value = false
  } finally {
    databaseChecking.value = false
    refreshedAt.value = new Date().toLocaleTimeString()
  }
}

async function handleLogout() {
  await auth.logout()
  await router.push('/login')
}

async function handleMenuSelect(path: string) {
  if (path === route.path) {
    await router.replace({ path, query: { ...route.query, refresh: String(Date.now()) } })
    return
  }
  await router.push(path)
}

onMounted(refreshDatabaseStatus)
</script>

<style scoped>
.admin-shell {
  height: 100vh;
  overflow: hidden;
}

.admin-aside {
  height: 100vh;
  flex-shrink: 0;
  border-right: 1px solid var(--app-border);
  background: var(--app-sidebar-bg);
}

.admin-content {
  height: 100vh;
  min-width: 0;
}

.brand {
  height: 58px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 750;
  color: var(--app-accent);
}

.nav-menu {
  border-right: 0;
  background: transparent;
}

.topbar {
  height: 58px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--app-border);
  background: var(--app-surface);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.status-row,
.user-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.refresh-time,
.drawer-text {
  color: var(--app-muted);
}

.main-view {
  height: calc(100vh - 58px);
  overflow-y: auto;
  padding: 22px;
  background: var(--app-bg);
}

:global([data-theme='dark']) .topbar,
:global([data-theme='dark']) .admin-aside {
  border-color: var(--app-border);
}

:global([data-theme='dark']) .brand {
  color: var(--app-accent);
}

:global([data-theme='dark']) .main-view {
  background: var(--app-bg);
}

:global([data-theme='dark']) .nav-menu :deep(.el-menu-item) {
  color: var(--app-text);
}

:global([data-theme='dark']) .nav-menu :deep(.el-menu-item.is-active) {
  color: var(--app-accent);
}

@media (max-width: 760px) {
  .admin-shell {
    display: block;
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .admin-aside {
    width: 100% !important;
    height: auto;
    min-height: auto;
  }

  .admin-content,
  .main-view {
    height: auto;
  }

  .main-view {
    overflow: visible;
  }

  .topbar {
    height: auto;
    min-height: 58px;
    flex-wrap: wrap;
    padding: 10px 14px;
  }
}
</style>
