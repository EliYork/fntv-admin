import { onUnmounted, ref, shallowRef } from 'vue'
import type { PageData } from '../types/api'

/** Commit only the latest successful response; failures never erase visible rows. */
export function useRetainedPage<T>(fetchPage: () => Promise<PageData<T>>) {
  const pageData = shallowRef<PageData<T> | null>(null)
  const loading = ref(false)
  const errorMessage = ref('')
  let version = 0
  async function loadData() {
    const requestedVersion = ++version
    loading.value = true
    try {
      const data = await fetchPage()
      if (requestedVersion !== version) return
      if (data.error) throw new Error('page-unavailable')
      pageData.value = data
      errorMessage.value = ''
      return data
    } catch {
      if (requestedVersion === version) errorMessage.value = pageData.value
        ? '更新失败，暂时显示上次结果，将自动重试'
        : '暂时无法加载，将自动重试'
    } finally {
      if (requestedVersion === version) loading.value = false
    }
  }
  onUnmounted(() => { version += 1 })
  return { pageData, loading, errorMessage, loadData }
}
