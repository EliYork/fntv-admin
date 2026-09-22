import { onMounted, onUnmounted } from 'vue'

/** Poll only the visible page; schedule after completion to avoid overlapping polls. */
export function useAutoRefresh(refresh: () => Promise<unknown>, busy: () => boolean, intervalMs = 60_000) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let stopped = false
  async function tick() {
    try {
      if (document.visibilityState === 'visible' && !busy()) await refresh()
    } catch { /* The owning view displays its local error and retains successful data. */ }
    finally { if (!stopped) timer = setTimeout(tick, intervalMs) }
  }
  onMounted(() => { timer = setTimeout(tick, intervalMs) })
  onUnmounted(() => { stopped = true; clearTimeout(timer) })
}
