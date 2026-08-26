<template>
  <HistoryFeed ref="historyFeed" heading="完整观看历史" heading-tag="h1" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import HistoryFeed from '../components/HistoryFeed.vue'
import { useRouteRefresh } from '../utils/routeRefresh'

const historyFeed = ref<InstanceType<typeof HistoryFeed> | null>(null)
useRouteRefresh(() => historyFeed.value?.refresh())
</script>
