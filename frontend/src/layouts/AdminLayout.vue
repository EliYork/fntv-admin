<template>
  <div class="admin-shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>

    <header class="topbar">
      <button class="brand-button" type="button" aria-label="返回数据中心首页" @click="goToDashboard">
        <span class="brand-mark" aria-hidden="true"></span>
        <span class="brand-name">飞牛影视</span>
        <span class="brand-suffix">数据中心</span>
      </button>

      <div class="topbar-actions">
        <AppTooltip v-if="route.path === '/dashboard' && dashboardFreshness" :content="dashboardFreshness.partial ? '部分数据可能来自上次成功更新' : '当前页面展示数据最后一次成功更新的时间'" placement="bottom">
          <time class="data-freshness" :datetime="new Date(dashboardFreshness.updatedAt).toISOString()">
            <span class="freshness-full">数据更新于 {{ formattedDashboardFreshness }}</span>
            <span class="freshness-compact">更新 {{ formattedDashboardFreshness.slice(11) }}</span>
            <span class="freshness-tiny">{{ formattedDashboardFreshness.slice(11) }}</span>
          </time>
        </AppTooltip>
        <AppTooltip :content="`最近检查：${refreshedAt}`" placement="bottom">
          <span class="database-status" :class="`is-${databaseStatusType}`" role="status">
            <i aria-hidden="true"></i>
            <span class="status-full">{{ databaseStatusLabel }}</span>
            <span class="status-compact">{{ databaseStatusCompactLabel }}</span>
          </span>
        </AppTooltip>

        <el-button class="toolbar-button refresh-button" text :icon="Refresh" aria-label="刷新当前页面数据" @click="refreshCurrentPage">
          <span class="button-label">刷新</span>
        </el-button>
        <el-button
          class="toolbar-button"
          text
          :icon="Setting"
          aria-label="打开功能与设置"
          :aria-expanded="drawerVisible"
          @click="drawerVisible = true"
        />
        <el-button
          class="toolbar-button"
          text
          :icon="darkMode ? Sunny : Moon"
          :aria-label="darkMode ? '切换到浅色主题' : '切换到深色主题'"
          :aria-pressed="darkMode"
          @click="darkMode = !darkMode"
        />

        <el-dropdown trigger="click" @command="handleUserCommand">
          <el-button class="user-menu-button" text aria-label="打开用户菜单">
            <span class="user-avatar" aria-hidden="true">{{ userInitial }}</span>
            <span class="username">{{ auth.user?.username || 'admin' }}</span>
            <el-icon aria-hidden="true"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled>{{ auth.isLocalNoAuth ? '本地免登录访问' : '管理员账号' }}</el-dropdown-item>
              <el-dropdown-item v-if="!auth.isLocalNoAuth" command="logout" divided :icon="SwitchButton">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <main id="main-content" class="main-view" tabindex="-1">
      <div class="page-container"><router-view /></div>
    </main>

    <el-drawer v-model="drawerVisible" class="settings-drawer" title="功能与设置" size="min(92vw, 390px)">
      <nav class="drawer-navigation" aria-label="后台功能导航">
        <section v-for="group in navigationGroups" :key="group.label" class="navigation-group">
          <h2>{{ group.label }}</h2>
          <button
            v-for="item in group.items"
            :key="item.path"
            class="navigation-item"
            :class="{ 'is-active': route.path === item.path }"
            type="button"
            @click="navigateTo(item.path)"
          >
            <el-icon aria-hidden="true"><component :is="item.icon" /></el-icon>
            <span>
              <strong>{{ item.label }}</strong>
              <small>{{ item.description }}</small>
            </span>
            <el-icon class="navigation-arrow" aria-hidden="true"><ArrowRight /></el-icon>
          </button>
        </section>
      </nav>
      <p class="drawer-footnote">低频管理功能集中于此，主页保留日常观察所需的数据。</p>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  ArrowRight,
  DataAnalysis,
  Document,
  Film,
  HomeFilled,
  Monitor,
  Moon,
  Refresh,
  Setting,
  Sunny,
  SwitchButton,
  User
} from '@element-plus/icons-vue'
import { fetchDatabaseStatus } from '../api/system'
import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'
import { formatInstant } from '../utils/applicationTime'
import { readSuccessfulData } from '../utils/successfulDataCache'
import AppTooltip from '../components/AppTooltip.vue'

interface DashboardFreshness {
  updatedAt: number
  applicationTimezone: string
  partial: boolean
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const theme = useThemeStore()
const databaseChecking = ref(true)
const databaseOk = ref(false)
const refreshedAt = ref('-')
const dashboardFreshness = ref<DashboardFreshness | null>(null)
const drawerVisible = ref(false)
let statusTimer: number | undefined
theme.init()

const darkMode = computed({
  get: () => theme.resolved === 'dark',
  set: (enabled: boolean) => theme.setMode(enabled ? 'dark' : 'light')
})

const userInitial = computed(() => (auth.user?.username || 'A').trim().charAt(0).toUpperCase())
const formattedDashboardFreshness = computed(() => {
  const freshness = dashboardFreshness.value
  return freshness ? formatInstant(freshness.updatedAt, freshness.applicationTimezone) : '—'
})

const navigationGroups = [
  {
    label: '查看',
    items: [
      { path: '/dashboard', label: '数据中心', description: '主要统计与连续观看历史', icon: HomeFilled },
      { path: '/history', label: '观看历史', description: '独立浏览完整播放记录', icon: Document },
      { path: '/reports', label: '报表中心', description: '低频分布与高级统计', icon: DataAnalysis }
    ]
  },
  {
    label: '管理',
    items: [
      { path: '/users', label: '用户管理', description: '别名、备注与隐藏设置', icon: User },
      { path: '/media', label: '媒体库', description: '媒体资料与增强信息', icon: Film }
    ]
  },
  {
    label: '系统',
    items: [
      { path: '/settings', label: '系统设置', description: '访问策略与数据设置', icon: Setting },
      { path: '/diagnostics', label: '系统诊断', description: '数据库、Schema 与运行状态', icon: Monitor }
    ]
  }
]

const databaseStatusType = computed(() => {
  if (databaseChecking.value) return 'info'
  return databaseOk.value ? 'success' : 'danger'
})

const databaseStatusLabel = computed(() => {
  if (databaseChecking.value) return '数据库检查中'
  return databaseOk.value ? '飞牛数据库正常' : '飞牛数据库异常'
})

const databaseStatusCompactLabel = computed(() => {
  if (databaseChecking.value) return '检查'
  return databaseOk.value ? '正常' : '异常'
})

async function refreshDatabaseStatus() {
  try {
    const status = await fetchDatabaseStatus()
    databaseOk.value = status.fntv.availability === 'available'
  } catch {
    databaseOk.value = false
  } finally {
    databaseChecking.value = false
    refreshedAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  }
}

async function goToDashboard() {
  if (route.path === '/dashboard') {
    await refreshCurrentPage()
    return
  }
  await router.push('/dashboard')
}

async function refreshCurrentPage() {
  await refreshDatabaseStatus()
  await router.replace({ path: route.path, query: { ...route.query, refresh: String(Date.now()) } })
}

async function navigateTo(path: string) {
  drawerVisible.value = false
  if (route.path === path) {
    await refreshCurrentPage()
    return
  }
  await router.push(path)
}

async function handleLogout() {
  await auth.logout()
  await router.push('/login')
}

async function handleUserCommand(command: string) {
  if (command === 'logout') await handleLogout()
}

function updateDashboardFreshness(event: Event): void {
  const detail = (event as CustomEvent<DashboardFreshness>).detail
  if (detail && typeof detail.updatedAt === 'number') dashboardFreshness.value = detail
}

onMounted(() => {
  dashboardFreshness.value = readSuccessfulData<DashboardFreshness>('fntv.dashboard.v1.freshness')?.data || null
  window.addEventListener('fntv-dashboard-freshness', updateDashboardFreshness)
  void refreshDatabaseStatus()
  statusTimer = window.setInterval(refreshDatabaseStatus, 60_000)
})

onUnmounted(() => {
  window.removeEventListener('fntv-dashboard-freshness', updateDashboardFreshness)
  if (statusTimer) window.clearInterval(statusTimer)
})
</script>

<style scoped>
.admin-shell {
  display: grid;
  grid-template-rows: 64px minmax(0, 1fr);
  height: 100vh;
  overflow: hidden;
  background: var(--app-bg);
}

.skip-link {
  position: fixed;
  z-index: 5000;
  top: 8px;
  left: 8px;
  padding: 9px 13px;
  border-radius: 8px;
  background: var(--app-accent);
  color: var(--app-on-accent);
  transform: translateY(-160%);
}

.skip-link:focus { transform: translateY(0); }

.topbar {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 clamp(16px, 3vw, 44px);
  border-bottom: 1px solid var(--app-border-soft);
  background: color-mix(in srgb, var(--app-surface) 94%, transparent);
}

.brand-button {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  min-height: 44px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--app-title);
  cursor: pointer;
  font: inherit;
}

.brand-mark {
  width: 9px;
  height: 28px;
  margin-right: 12px;
  border-radius: 2px;
  background: var(--app-accent);
}

.brand-name { font-size: 16px; font-weight: 720; letter-spacing: 0.02em; }
.brand-suffix { margin-left: 9px; padding-left: 9px; border-left: 1px solid var(--app-border); color: var(--app-muted); font-size: 13px; }

.topbar-actions { display: flex; align-items: center; justify-content: flex-end; gap: 4px; min-width: 0; }
.data-freshness { margin-right: 10px; color: var(--app-muted); font-size: 11px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.freshness-compact, .freshness-tiny { display: none; }

.database-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  margin-right: 8px;
  color: var(--app-muted-strong);
  font-size: 12px;
  white-space: nowrap;
}

.database-status i { width: 7px; height: 7px; border-radius: 50%; background: var(--app-muted); }
.status-compact { display: none; }
.database-status.is-success i { background: var(--app-success); }
.database-status.is-danger i { background: var(--app-danger); }
.toolbar-button, .user-menu-button { min-width: 44px; min-height: 44px; }
.refresh-button { gap: 6px; }
.user-menu-button { gap: 7px; margin-left: 2px; }

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--app-surface-strong);
  color: var(--app-title);
  font-size: 12px;
  font-weight: 700;
}

.username { max-width: 120px; overflow: hidden; text-overflow: ellipsis; }

.main-view {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  padding: clamp(22px, 3.2vw, 48px) clamp(16px, 3vw, 44px) 72px;
  outline: none;
}

.page-container { width: min(1540px, 100%); margin: 0 auto; }
.drawer-navigation { display: grid; gap: 28px; }
.navigation-group { display: grid; gap: 6px; }
.navigation-group h2 { margin: 0 0 5px; color: var(--app-muted); font-size: 11px; font-weight: 650; letter-spacing: 0.12em; }

.navigation-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) 18px;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 58px;
  padding: 9px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--app-text);
  cursor: pointer;
  text-align: left;
  transition: background-color 160ms ease, color 160ms ease;
}

.navigation-item:hover, .navigation-item.is-active { background: var(--app-surface-soft); }
.navigation-item.is-active { color: var(--app-accent); }
.navigation-item span { display: grid; gap: 2px; min-width: 0; }
.navigation-item strong { color: var(--app-title); font-size: 14px; font-weight: 650; }
.navigation-item small { overflow: hidden; color: var(--app-muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.navigation-arrow { color: var(--app-muted); }
.drawer-footnote { margin: 32px 10px 0; color: var(--app-muted); font-size: 12px; line-height: 1.7; }
:global(.settings-drawer .el-drawer__header) { margin-bottom: 12px; color: var(--app-title); }
:global(.settings-drawer .el-drawer__body) { padding-top: 8px; }

@media (max-width: 760px) {
  .admin-shell { grid-template-rows: 58px minmax(0, 1fr); height: 100dvh; min-height: 100vh; }
  .topbar { gap: 10px; padding: 0 10px 0 14px; }
  .brand-mark { height: 24px; margin-right: 9px; }
  .brand-suffix, .status-full, .button-label, .username, .user-menu-button > :deep(.el-icon), .freshness-full { display: none; }
  .freshness-compact { display: inline; }
  .data-freshness { margin-right: 2px; font-size: 10px; }
  .status-compact { display: inline; }
  .database-status { min-width: 44px; margin-right: 0; justify-content: center; gap: 5px; font-size: 10px; }
  .database-status i { width: 9px; height: 9px; }
  .topbar-actions { gap: 0; }
  .refresh-button { gap: 0; }
  .user-menu-button { padding: 6px; }
  .main-view { padding: 22px 14px 56px; }
}

@media (max-width: 430px) {
  .brand-name { font-size: 14px; }
  .freshness-compact { display: none; }
  .freshness-tiny { display: inline; }
  .data-freshness { position: absolute; bottom: 3px; left: 38px; margin-right: 0; line-height: 1; }
  .toolbar-button, .user-menu-button { min-width: 44px; width: 44px; padding-right: 6px; padding-left: 6px; }
}
</style>
