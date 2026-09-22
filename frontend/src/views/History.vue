<template>
  <HistoryFeed ref="historyFeed" heading="完整观看历史" heading-tag="h1" :filter-user="filterUser" />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import HistoryFeed from '../components/HistoryFeed.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const route = useRoute()
const filterUser = ref('')
watch(() => [route.path, route.query.user], () => {
  if (route.path === '/history') filterUser.value = typeof route.query.user === 'string' ? route.query.user : ''
}, { immediate: true })
const historyFeed = ref<InstanceType<typeof HistoryFeed> | null>(null)
useRouteRefresh(() => historyFeed.value?.refresh())
</script>
