<template>
  <div class="pagination-footer">
    <el-pagination
      background
      :current-page="page"
      :page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      :disabled="disabled"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="emit('page-change', $event)"
      @size-change="emit('page-size-change', $event)"
    />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  total: number
  disabled?: boolean
}>()

const emit = defineEmits<{
  (event: 'page-change', value: number): void
  (event: 'page-size-change', value: number): void
}>()
</script>

<style scoped>
.pagination-footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
  border-top: 1px solid #edf0f5;
}

@media (max-width: 760px) {
  .pagination-footer {
    justify-content: flex-start;
    overflow-x: auto;
  }
}
</style>
