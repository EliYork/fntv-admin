<template>
  <main class="login-page">
    <section class="login-panel">
      <h1>fntv-admin</h1>
      <p>{{ initialized ? '登录飞牛影视增强管理后台' : '首次启动，创建管理员账号' }}</p>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-button type="primary" class="submit-button" :loading="loading" @click="submit">
          {{ initialized ? '登录' : '创建管理员' }}
        </el-button>
      </el-form>

      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchAuthStatus, initAdmin } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const initialized = ref(true)
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '' })

async function loadStatus() {
  try {
    const status = await fetchAuthStatus()
    initialized.value = status.admin_initialized
  } catch {
    initialized.value = true
  }
}

async function submit() {
  if (!form.username.trim()) {
    error.value = '请输入用户名'
    return
  }
  if (!initialized.value && form.password.length < 8) {
    error.value = '管理员密码至少需要 8 位'
    return
  }
  if (initialized.value && !form.password) {
    error.value = '请输入密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    if (!initialized.value) {
      await initAdmin(form.username, form.password)
      initialized.value = true
    }
    await auth.login(form.username, form.password)
    await router.push((route.query.redirect as string) || '/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '操作失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(180deg, #edf4ff 0%, #f8fafc 50%, #f5f7fb 100%);
}

.login-panel {
  width: min(420px, 100%);
  border: 1px solid #dde3ee;
  border-radius: 8px;
  background: #fff;
  padding: 28px;
}

h1 {
  margin: 0;
  font-size: 28px;
}

p {
  margin: 8px 0 22px;
  color: #687182;
}

.submit-button {
  width: 100%;
  margin-bottom: 14px;
}
</style>
