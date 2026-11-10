<template>
  <div class="layout">
    <header class="layout__header">
      <div class="layout__brand">
        <RouterLink to="/">校园综合 AI 平台</RouterLink>
      </div>
      <nav class="layout__nav">
        <RouterLink to="/">首页</RouterLink>
      </nav>
      <div class="layout__user">
        <template v-if="auth.user">
          <span class="layout__identity">{{ auth.user.identity }}</span>
          <button type="button" class="btn btn--ghost" @click="handleLogout">退出登录</button>
        </template>
        <template v-else>
          <RouterLink to="/login">登录</RouterLink>
          <RouterLink to="/register">注册</RouterLink>
        </template>
      </div>
    </header>

    <main class="layout__main">
      <RouterView />
    </main>

    <footer class="layout__footer">
      校园综合 AI 平台 · 面向西昌学院安宁校区学生
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>
