<template>
  <Teleport to="body">
    <div v-if="ui.authOpen" class="modal" @click.self="close">
      <div class="modal__card" role="dialog" aria-modal="true" aria-label="登录 CampusAI">
        <button class="modal__close" type="button" aria-label="关闭" @click="close">×</button>

        <h2 class="modal__title">欢迎回到 CampusAI</h2>
        <p class="modal__subtitle">登录后即可使用校园问答、学习助手与资料解析</p>

        <div class="modal__tabs">
          <button
            class="modal__tab"
            :class="{ 'is-active': mode === 'login' }"
            type="button"
            @click="mode = 'login'"
          >
            登录
          </button>
          <button
            class="modal__tab"
            :class="{ 'is-active': mode === 'register' }"
            type="button"
            @click="mode = 'register'"
          >
            注册
          </button>
        </div>

        <form @submit.prevent="submit">
          <label class="modal__field">
            <span class="modal__label">学号 / 邮箱</span>
            <input
              v-model.trim="identity"
              class="modal__input"
              type="text"
              autocomplete="username"
              placeholder="请输入学号或邮箱"
            />
          </label>

          <label class="modal__field">
            <span class="modal__label">密码</span>
            <input
              v-model="password"
              class="modal__input"
              type="password"
              :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
              placeholder="至少 8 位，含字母和数字"
            />
          </label>

          <label v-if="mode === 'register'" class="modal__field">
            <span class="modal__label">确认密码</span>
            <input
              v-model="confirmPassword"
              class="modal__input"
              type="password"
              autocomplete="new-password"
              placeholder="请再次输入密码"
            />
          </label>

          <p v-if="errorMessage" class="modal__error">{{ errorMessage }}</p>

          <button class="btn" style="width: 100%" type="submit" :disabled="submitting">
            {{ submitting ? '处理中…' : mode === 'login' ? '登录' : '注册并开始' }}
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
        </form>

        <p class="modal__hint">学号或邮箱二选一，注册即可开始使用</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { closeAuth, ui } from '@/state/ui'
import { safeRedirect } from '@/utils/redirect'

const auth = useAuthStore()
const router = useRouter()

const mode = ref('login')
const identity = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const submitting = ref(false)

function close() {
  closeAuth()
}

function onKeydown(event) {
  if (event.key === 'Escape' && ui.authOpen) close()
}

watch(
  () => ui.authOpen,
  (open) => {
    if (open) {
      errorMessage.value = ''
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})

async function submit() {
  errorMessage.value = ''
  if (mode.value === 'register' && password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }
  submitting.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(identity.value, password.value)
    } else {
      await auth.register(identity.value, password.value)
    }
    const redirect = safeRedirect(ui.authRedirect, '/')
    close()
    router.push(redirect)
  } catch (error) {
    errorMessage.value = error.message || '操作失败，请稍后重试。'
  } finally {
    submitting.value = false
  }
}
</script>
