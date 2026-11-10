<template>
  <div class="auth-page">
    <form class="auth-card" @submit.prevent="handleSubmit">
      <h1 class="auth-card__title">注册</h1>
      <p class="auth-card__subtitle">学号或邮箱二选一，注册后即可使用</p>

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
          autocomplete="new-password"
          placeholder="至少 8 位，含字母和数字"
        />
      </label>

      <label class="field">
        <span class="field__label">确认密码</span>
        <input
          v-model="confirmPassword"
          class="field__input"
          type="password"
          autocomplete="new-password"
          placeholder="请再次输入密码"
        />
      </label>

      <p v-if="errorMessage" class="alert alert--error">{{ errorMessage }}</p>

      <button class="btn btn--primary btn--block" type="submit" :disabled="submitting">
        {{ submitting ? '注册中…' : '注册' }}
      </button>

      <p class="auth-card__footer">
        已有账号？<RouterLink to="/login">去登录</RouterLink>
      </p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const identity = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function handleSubmit() {
  errorMessage.value = ''
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }
  submitting.value = true
  try {
    await auth.register(identity.value, password.value)
    router.push('/')
  } catch (error) {
    errorMessage.value = error.message || '注册失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>
