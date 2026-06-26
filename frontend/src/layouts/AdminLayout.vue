<template>
  <el-container class="admin-shell">
    <el-aside class="admin-aside" width="232px">
      <div class="brand">fntv-admin</div>
      <el-menu :default-active="route.path" router class="nav-menu">
        <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="status-row">
          <el-tag :type="databaseOk ? 'success' : 'danger'" effect="light">
            {{ databaseOk ? '飞牛数据库正常' : '飞牛数据库异常' }}
          </el-tag>
          <span class="refresh-time">刷新：{{ refreshedAt }}</span>
        </div>
        <div class="user-row">
          <el-switch v-model="darkMode" inline-prompt active-text="暗" inactive-text="亮" />
          <span>{{ auth.user?.username || 'admin' }}</span>
          <el-button size="small" :icon="SwitchButton" @click="handleLogout">退出</el-button>
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataAnalysis, Document, Files, Film, HomeFilled, Setting, SwitchButton, User, Tickets } from '@element-plus/icons-vue'
import { fetchDatabaseStatus } from '../api/system'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const databaseOk = ref(false)
const refreshedAt = ref('-')
const darkMode = ref(localStorage.getItem('fntv_theme') === 'dark')
const drawerVisible = ref(false)

const navItems = [
  { path: '/dashboard', label: '仪表盘', icon: HomeFilled },
  { path: '/history', label: '观看历史', icon: Document },
  { path: '/users', label: '用户管理', icon: User },
  { path: '/media', label: '媒体库', icon: Film },
  { path: '/reports', label: '报表中心', icon: DataAnalysis },
  { path: '/tasks', label: '任务中心', icon: Tickets },
  { path: '/logs', label: '日志中心', icon: Files },
  { path: '/settings', label: '系统设置', icon: Setting }
]

async function refreshDatabaseStatus() {
  try {
    const status = await fetchDatabaseStatus()
    databaseOk.value = status.fntv.ok
  } catch {
    databaseOk.value = false
  } finally {
    refreshedAt.value = new Date().toLocaleTimeString()
  }
}

async function handleLogout() {
  await auth.logout()
  await router.push('/login')
}

const asideBackground = computed(() => (darkMode.value ? '#182033' : '#ffffff'))

onMounted(refreshDatabaseStatus)

watch(
  darkMode,
  (enabled) => {
    localStorage.setItem('fntv_theme', enabled ? 'dark' : 'light')
    document.documentElement.dataset.theme = enabled ? 'dark' : 'light'
  },
  { immediate: true }
)
</script>

<style scoped>
.admin-shell {
  min-height: 100vh;
}

.admin-aside {
  border-right: 1px solid #dde3ee;
  background: v-bind(asideBackground);
}

.brand {
  height: 58px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 18px;
  font-weight: 750;
  color: #2563eb;
}

.nav-menu {
  border-right: 0;
  background: transparent;
}

.topbar {
  height: 58px;
  border-bottom: 1px solid #dde3ee;
  background: #fff;
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
  color: #6b7280;
}

.main-view {
  padding: 22px;
  background: #f5f7fb;
}

:global([data-theme='dark']) .topbar,
:global([data-theme='dark']) .admin-aside {
  border-color: #30394d;
  background: #182033;
}

:global([data-theme='dark']) .brand {
  color: #8fb4ff;
}

:global([data-theme='dark']) .main-view {
  background: #111827;
}

:global([data-theme='dark']) .nav-menu :deep(.el-menu-item) {
  color: #d5dbea;
}

:global([data-theme='dark']) .nav-menu :deep(.el-menu-item.is-active) {
  color: #8fb4ff;
}

@media (max-width: 760px) {
  .admin-shell {
    display: block;
  }

  .admin-aside {
    width: 100% !important;
    min-height: auto;
  }

  .topbar {
    height: auto;
    min-height: 58px;
    flex-wrap: wrap;
    padding: 10px 14px;
  }
}
</style>
