import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '@/api/client'
import { openAuth } from '@/state/ui'
import ApiSettingsView from '@/views/ApiSettingsView.vue'
import ChatView from '@/views/ChatView.vue'
import DocumentsView from '@/views/DocumentsView.vue'
import KbView from '@/views/KbView.vue'
import LandingView from '@/views/LandingView.vue'
import QaView from '@/views/QaView.vue'
import SearchView from '@/views/SearchView.vue'

/**
 * 路由约定
 * - `/` 是落地页（公开）；
 * - 功能模块路由需要登录，未登录时弹出登录模态框并回到落地页；
 * - 登录与注册不再占用独立页面，统一由模态框承载。
 */
const routes = [
  { path: '/', name: 'landing', component: LandingView },
  { path: '/qa', name: 'qa', component: QaView, meta: { requiresAuth: true } },
  { path: '/chat', name: 'chat', component: ChatView, meta: { requiresAuth: true } },
  { path: '/documents', name: 'documents', component: DocumentsView, meta: { requiresAuth: true } },
  { path: '/search', name: 'search', component: SearchView, meta: { requiresAuth: true } },
  { path: '/kb', name: 'kb', component: KbView, meta: { requiresAuth: true } },
  {
    path: '/settings/api',
    name: 'api-settings',
    component: ApiSettingsView,
    meta: { requiresAuth: true },
  },
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
