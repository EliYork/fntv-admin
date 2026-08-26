<template>
  <el-tooltip
    v-bind="$attrs"
    :disabled="disabled || !hoverCapable"
    :show-after="showAfter"
    :hide-after="hideAfter"
    :enterable="false"
    :persistent="false"
    effect="light"
    transition=""
  >
    <slot />
  </el-tooltip>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

withDefaults(defineProps<{
  disabled?: boolean
  showAfter?: number
  hideAfter?: number
}>(), {
  disabled: false,
  showAfter: 70,
  hideAfter: 0
})

const hoverCapable = ref(true)
let hoverQuery: MediaQueryList | null = null

function updateHoverCapability(event?: MediaQueryListEvent): void {
  hoverCapable.value = event?.matches ?? hoverQuery?.matches ?? true
}

onMounted(() => {
  hoverQuery = window.matchMedia('(hover: hover) and (pointer: fine)')
  updateHoverCapability()
  hoverQuery.addEventListener('change', updateHoverCapability)
})

onUnmounted(() => hoverQuery?.removeEventListener('change', updateHoverCapability))
</script>
