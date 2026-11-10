import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '@/api/client'
import { openAuth } from '@/state/ui'
import LandingView from '@/views/LandingView.vue'
import ModuleView from '@/views/ModuleView.vue'

/**
 * 路由约定
 * - `/` 是落地页（公开）；
 * - 功能模块路由需要登录，未登录时弹出登录模态框并回到落地页；
 * - 登录与注册不再占用独立页面，统一由模态框承载。
 */
const routes = [
  { path: '/', name: 'landing', component: LandingView },
  { path: '/qa', name: 'qa', component: ModuleView, meta: { requiresAuth: true, module: 'qa' } },
  { path: '/chat', name: 'chat', component: ModuleView, meta: { requiresAuth: true, module: 'chat' } },
  {
    path: '/documents',
    name: 'documents',
    component: ModuleView,
    meta: { requiresAuth: true, module: 'documents' },
  },
  {
    path: '/search',
    name: 'search',
    component: ModuleView,
    meta: { requiresAuth: true, module: 'search' },
  },
  { path: '/kb', name: 'kb', component: ModuleView, meta: { requiresAuth: true, module: 'kb' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !getToken()) {
    openAuth(to.fullPath)
    return { name: 'landing' }
  }
  return true
})

export default router
