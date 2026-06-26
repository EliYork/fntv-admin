<template>
  <div class="empty-panel">
    <el-empty :description="description" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  description: string
}>()
</script>

