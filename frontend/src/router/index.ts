import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'history', name: 'history', component: () => import('../views/History.vue') },
      { path: 'users', name: 'users', component: () => import('../views/Users.vue') },
      { path: 'media', name: 'media', component: () => import('../views/MediaLibrary.vue') },
      { path: 'reports', name: 'reports', component: () => import('../views/Reports.vue') },
      { path: 'tasks', name: 'tasks', component: () => import('../views/Tasks.vue') },
      { path: 'logs', name: 'logs', component: () => import('../views/Logs.vue') },
      { path: 'settings', name: 'settings', component: () => import('../views/SystemSettings.vue') },
      { path: 'diagnostics', name: 'diagnostics', component: () => import('../views/Diagnostics.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.name === 'login') {
    await auth.ensureReady()
    if (auth.isAuthenticated) return { path: '/dashboard' }
    return true
  }
  if (to.meta.public) return true
  const allowed = await auth.ensureReady()
  if (!allowed) {
    return {
      path: '/login',
      query: {
        redirect: to.fullPath,
        forbidden: auth.accessDeniedMessage ? '1' : undefined
      }
    }
  }
  return true
})

export default router
