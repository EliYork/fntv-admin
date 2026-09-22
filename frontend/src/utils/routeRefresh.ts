import { watch } from 'vue'
import { useRoute } from 'vue-router'

export function useRouteRefresh(refresh: () => void | Promise<void>) {
  const route = useRoute()
  const ownerPath = route.path
  watch(
    () => route.query.refresh,
    (value, oldValue) => {
      if (route.path === ownerPath && value && value !== oldValue) {
        void refresh()
      }
    }
  )
}
