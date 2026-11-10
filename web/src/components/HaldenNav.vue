<template>
  <header class="nav" ref="rootEl">
    <RouterLink class="brand" to="/">
      <svg viewBox="0 0 22 22" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="11" fill="#5b7cf0" />
        <path
          d="M5 10.2c2.3-1.6 4.7-1.6 7 0s4.7 1.6 7 0"
          stroke="#fff"
          stroke-width="1.8"
          stroke-linecap="round"
          fill="none"
        />
        <path
          d="M5 14.2c2.3-1.6 4.7-1.6 7 0s4.7 1.6 7 0"
          stroke="#fff"
          stroke-width="1.8"
          stroke-linecap="round"
          fill="none"
        />
      </svg>
      CampusAI
    </RouterLink>

    <nav class="links">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/qa">校园问答</RouterLink>
      <RouterLink to="/chat">学习助手</RouterLink>
      <RouterLink to="/documents">资料解析</RouterLink>
      <RouterLink to="/search">资源搜索</RouterLink>
    </nav>

    <div class="right">
      <template v-if="auth.user">
        <span class="who">{{ auth.user.identity }}</span>
        <button class="login" type="button" @click="handleLogout">退出</button>
      </template>
      <button v-else class="login" type="button" @click="openLogin">登录</button>
      <div class="navcta">
        <button class="btn" type="button" @click="openLogin">
          <span class="lbl">免费试用</span>
          <span class="dot">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M4.5 2.5 8 6l-3.5 3.5"
                stroke="#0b1d3a"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { openAuth } from '@/state/ui'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const rootEl = ref(null)

defineExpose({ root: rootEl })

function openLogin() {
  openAuth()
}

async function handleLogout() {
  await auth.logout()
  router.push('/')
}
</script>
