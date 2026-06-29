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
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useThemeStore, type ThemeMode } from '../stores/theme'
import { useRouteRefresh } from '../utils/routeRefresh'

const theme = useThemeStore()
const loading = ref(false)
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

async function refreshSettings() {
  loading.value = true
  try {
    theme.reload()
  } finally {
    loading.value = false
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
</style>
