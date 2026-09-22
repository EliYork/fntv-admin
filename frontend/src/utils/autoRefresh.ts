import { onActivated, onDeactivated, onMounted, onUnmounted } from 'vue'

/** Cached pages stop polling until activated again. */
export function useAutoRefresh(refresh: () => Promise<unknown>, busy: () => boolean, intervalMs = 60_000) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let active = false
  let running = false
  function schedule() { if (active && !timer && !running) timer = setTimeout(tick, intervalMs) }
  async function tick() {
    timer = undefined
    running = true
    try {
      if (active && document.visibilityState === 'visible' && !busy()) await refresh()
    } catch { /* The owning view retains successful data and its local error. */ }
    finally { running = false; schedule() }
  }
  function start() { active = true; schedule() }
  function stop() { active = false; clearTimeout(timer); timer = undefined }
  onMounted(start)
  onActivated(start)
  onDeactivated(stop)
  onUnmounted(stop)
}
