import { createRouter, createWebHistory } from 'vue-router'

import { getToken } from '@/api/client'
import AppLayout from '@/components/AppLayout.vue'
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/register', name: 'register', component: RegisterView, meta: { public: true } },
  {
    path: '/',
    component: AppLayout,
    children: [{ path: '', name: 'home', component: HomeView }],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) {
    if (to.name === 'login' && getToken()) return { name: 'home' }
    return true
  }
  if (!getToken()) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

export default router
