<template>
  <div class="auth-page">
    <form class="auth-card" @submit.prevent="handleSubmit">
      <h1 class="auth-card__title">登录</h1>
      <p class="auth-card__subtitle">使用学号或邮箱登录</p>

      <label class="field">
        <span class="field__label">学号 / 邮箱</span>
        <input
          v-model.trim="identity"
          class="field__input"
          type="text"
          autocomplete="username"
          placeholder="请输入学号或邮箱"
        />
      </label>

      <label class="field">
        <span class="field__label">密码</span>
        <input
          v-model="password"
          class="field__input"
          type="password"
          autocomplete="current-password"
          placeholder="请输入密码"
        />
      </label>

      <p v-if="errorMessage" class="alert alert--error">{{ errorMessage }}</p>

      <button class="btn btn--primary btn--block" type="submit" :disabled="submitting">
        {{ submitting ? '登录中…' : '登录' }}
      </button>

      <p class="auth-card__footer">
        还没有账号？<RouterLink to="/register">立即注册</RouterLink>
      </p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { safeRedirect } from '@/utils/redirect'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const identity = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function handleSubmit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    await auth.login(identity.value, password.value)
    router.push(safeRedirect(route.query.redirect, '/'))
  } catch (error) {
    errorMessage.value = error.message || '登录失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>
