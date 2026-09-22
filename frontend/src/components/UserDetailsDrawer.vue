<template>
  <el-drawer :model-value="Boolean(user)" title="用户详情" size="min(94vw, 480px)" :before-close="closeDrawer" @update:model-value="!$event && emit('close')">
    <template v-if="user">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ user.username }}</el-descriptions-item>
        <el-descriptions-item label="GUID"><span class="user-guid">{{ user.guid }}</span></el-descriptions-item>
        <el-descriptions-item label="播放次数">{{ user.play_count }}</el-descriptions-item>
        <el-descriptions-item label="观看时长">{{ user.watch_duration }}</el-descriptions-item>
        <el-descriptions-item label="最近播放">{{ formatApplicationDateTime(user.last_play_at) }}</el-descriptions-item>
      </el-descriptions>
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
.profile-form { margin-top: 24px; }
.user-guid { overflow-wrap: anywhere; }
</style>
