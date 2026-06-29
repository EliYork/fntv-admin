import { watch } from 'vue'
import { useRoute } from 'vue-router'

export function useRouteRefresh(refresh: () => void | Promise<void>) {
  const route = useRoute()
  watch(
    () => route.query.refresh,
    (value, oldValue) => {
      if (value && value !== oldValue) {
        void refresh()
      }
    }
  )
}
