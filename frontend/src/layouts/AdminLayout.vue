<template>
  <el-container class="admin-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <el-aside class="admin-aside desktop-aside" width="232px">
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
          <el-button class="mobile-menu-button" text :icon="Menu" aria-label="打开导航菜单" @click="mobileNavVisible = true" />
          <el-tooltip :content="`最近检查：${refreshedAt}`" placement="bottom">
            <span class="database-status" :class="`is-${databaseStatusType}`">
              <i aria-hidden="true"></i>{{ databaseStatusLabel }}
            </span>
          </el-tooltip>
        </div>
        <div class="user-row">
          <el-button
            class="topbar-icon-button"
            text
            :icon="darkMode ? Sunny : Moon"
            :aria-label="darkMode ? '切换到浅色主题' : '切换到深色主题'"
            :title="darkMode ? '切换到浅色主题' : '切换到深色主题'"
            @click="darkMode = !darkMode"
          />
          <el-tag v-if="auth.isLocalNoAuth" size="small" type="warning" effect="light">本地模式</el-tag>
          <el-dropdown trigger="click" @command="handleUserCommand">
            <el-button class="user-menu-button" text>
              <el-icon><User /></el-icon>
              <span>{{ auth.user?.username || 'admin' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ auth.isLocalNoAuth ? '本地免登录访问' : '管理员账号' }}</el-dropdown-item>
                <el-dropdown-item v-if="!auth.isLocalNoAuth" command="logout" divided :icon="SwitchButton">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main id="main-content" class="main-view" tabindex="-1">
        <div class="page-container"><router-view /></div>
      </el-main>
    </el-container>

    <el-drawer v-model="mobileNavVisible" class="mobile-nav-drawer" direction="ltr" size="min(82vw, 300px)" :with-header="false">
      <div class="mobile-drawer-header">
        <div class="brand mobile-brand">fntv-admin</div>
        <el-button text :icon="Close" aria-label="关闭导航菜单" @click="mobileNavVisible = false" />
      </div>
      <el-menu :default-active="route.path" class="nav-menu" @select="handleMobileMenuSelect">
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>

    <el-drawer v-model="drawerVisible" title="详情" size="360px">
      <p class="drawer-text">详情抽屉已预留，用户、媒体和历史详情会在后续迭代接入。</p>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Close, DataAnalysis, Document, Film, HomeFilled, Menu, Monitor, Moon, Setting, Sunny, SwitchButton, User } from '@element-plus/icons-vue'
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
const mobileNavVisible = ref(false)
let statusTimer: number | undefined
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

async function handleUserCommand(command: string) {
  if (command === 'logout') await handleLogout()
}

async function handleMenuSelect(path: string) {
  if (path === route.path) {
    await router.replace({ path, query: { ...route.query, refresh: String(Date.now()) } })
    return
  }
  await router.push(path)
}

async function handleMobileMenuSelect(path: string) {
  mobileNavVisible.value = false
  await handleMenuSelect(path)
}

onMounted(() => {
  refreshDatabaseStatus()
  // 停留页面期间定时做轻量状态检查，驱动后端 TTL 判断是否该自动刷新快照
  statusTimer = window.setInterval(refreshDatabaseStatus, 60_000)
})

onUnmounted(() => {
  if (statusTimer) window.clearInterval(statusTimer)
})
</script>

<style scoped>
.admin-shell {
  height: 100vh;
  overflow: hidden;
}

.skip-link {
  position: fixed;
  z-index: 5000;
  top: 8px;
  left: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--app-accent);
  color: #fff;
  transform: translateY(-150%);
}

.skip-link:focus {
  transform: translateY(0);
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

.mobile-menu-button {
  display: none;
}

.database-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--app-muted-strong);
  font-size: 13px;
  white-space: nowrap;
}

.database-status i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
}

.database-status.is-success i {
  background: #16a34a;
}

.database-status.is-danger i {
  background: #dc2626;
}

.topbar-icon-button,
.user-menu-button {
  min-width: 36px;
  min-height: 36px;
}

.user-menu-button {
  gap: 6px;
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

.page-container {
  width: min(1440px, 100%);
  margin: 0 auto;
}

:global(.mobile-nav-drawer .el-drawer__body) {
  padding: 0;
  background: var(--app-sidebar-bg);
}

.mobile-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--app-border);
  padding-right: 8px;
}

.mobile-drawer-header > .el-button {
  min-width: 44px;
  min-height: 44px;
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
    height: 100dvh;
    min-height: 100vh;
    overflow: hidden;
  }

  .desktop-aside {
    display: none;
  }

  .admin-content {
    height: 100dvh;
  }

  .main-view {
    height: calc(100dvh - 58px);
    overflow-y: auto;
    padding: 16px 14px;
  }

  .topbar {
    height: 58px;
    min-height: 58px;
    padding: 0 10px;
  }

  .mobile-menu-button {
    display: inline-flex;
    min-width: 44px;
    min-height: 44px;
  }

  .database-status {
    font-size: 0;
  }

  .database-status i {
    width: 10px;
    height: 10px;
  }

  .topbar-icon-button,
  .user-menu-button {
    min-width: 44px;
    min-height: 44px;
  }

  .user-menu-button span {
    display: none;
  }

}
</style>
