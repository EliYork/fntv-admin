export interface AuthNavigationTarget {
  name?: string | symbol | null
  fullPath: string
  meta?: Record<string, unknown>
}

export interface AuthNavigationState {
  isAuthenticated: boolean
  accessDeniedMessage: string
  hasToken?: boolean
  ensureReady: () => Promise<boolean>
}

export async function resolveAuthNavigation(to: AuthNavigationTarget, auth: AuthNavigationState) {
  if (to.name === 'login') {
    await auth.ensureReady()
    if (auth.isAuthenticated) return { path: '/dashboard' }
    return true
  }
  if (to.meta?.public) return true

  const allowed = await auth.ensureReady()
  if (allowed) return true
  if (auth.accessDeniedMessage && auth.hasToken) return false

  return {
    path: '/login',
    query: {
      redirect: to.fullPath,
    },
  }
}
