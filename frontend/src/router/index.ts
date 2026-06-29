import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { resolveAuthNavigation } from './authGuard'

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
      { path: 'tasks', redirect: '/dashboard' },
      { path: 'logs', redirect: '/dashboard' },
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
  return resolveAuthNavigation(to, auth)
})

export default router
