<template>
  <el-drawer :model-value="Boolean(user)" title="用户详情" size="min(94vw, 480px)" :before-close="closeDrawer" @update:model-value="!$event && emit('close')">
    <template v-if="user">
      <div class="profile-heading">
        <span class="profile-avatar" aria-hidden="true">{{ (user.display_name || user.username).slice(0, 1) }}</span>
        <div><h2>{{ user.display_name || user.username }}</h2><p>{{ user.username }}</p></div>
      </div>
      <div class="profile-metrics">
        <div><span>播放次数</span><strong>{{ user.play_count }}</strong></div>
        <div><span>观看时长</span><strong>{{ user.watch_duration }}</strong></div>
      </div>
      <dl class="profile-meta">
        <dt>最近播放</dt><dd>{{ formatApplicationDateTime(user.last_play_at) }}</dd>
        <dt>GUID</dt><dd class="user-guid">{{ user.guid }}</dd>
      </dl>
      <el-form label-position="top" class="profile-form" @submit.prevent="save">
        <el-form-item label="显示别名"><el-input v-model="displayName" maxlength="128" :disabled="saving" clearable /></el-form-item>
        <el-form-item label="备注"><el-input v-model="note" type="textarea" :rows="5" maxlength="2000" show-word-limit :disabled="saving" /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="saving">保存</el-button>
      </el-form>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { updateUserProfile, type UserItem } from '../api/modules'
import { formatApplicationDateTime } from '../utils/applicationTime'
const props = defineProps<{ user: UserItem | null }>()
const emit = defineEmits<{ close: []; saved: [user: UserItem] }>()
const displayName = ref('')
const note = ref('')
const saving = ref(false)
watch(() => props.user, (user) => { displayName.value = user?.display_name || ''; note.value = user?.note || '' })
function closeDrawer(done: () => void) { if (!saving.value) done() }
async function save() {
  if (!props.user || saving.value) return
  const user = props.user
  const profile = { display_name: displayName.value.trim(), note: note.value }
  saving.value = true
  try {
    await updateUserProfile(user.guid, profile)
    emit('saved', { ...user, ...profile })
    ElMessage.success('已保存用户信息')
  } catch { /* API client displays the save error; keep the draft for retry. */ }
  finally { saving.value = false }
}
</script>

<style scoped>
.profile-heading { display: flex; align-items: center; gap: 14px; margin-bottom: 24px; }
.profile-heading h2 { margin: 0; color: var(--app-title); font-size: 22px; overflow-wrap: anywhere; }
.profile-heading p { margin: 5px 0 0; color: var(--app-muted); }
.profile-avatar { display: grid; place-items: center; flex-shrink: 0; width: 48px; height: 48px; border-radius: 14px; background: var(--app-surface-soft); color: var(--app-accent); font-size: 22px; }
.profile-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 20px; border-radius: 12px; background: var(--app-surface-soft); }
.profile-metrics div { display: grid; gap: 8px; }
.profile-metrics span, .profile-meta dt { color: var(--app-muted); font-size: 12px; }
.profile-metrics strong { color: var(--app-title); font-size: 20px; font-variant-numeric: tabular-nums; }
.profile-meta { display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 14px; padding: 20px 0; border-bottom: 1px solid var(--app-border-soft); }
.profile-meta dd { margin: 0; font-size: 12px; }

.profile-form { margin-top: 24px; }
.user-guid { overflow-wrap: anywhere; }
</style>
