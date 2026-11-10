/** 登录态 store：令牌持久化在 localStorage，用户信息保存在内存。 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
} from '@/api/auth'
import { clearToken, getToken, setToken } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(getToken())
  const user = ref(null)
  const isAuthenticated = computed(() => Boolean(token.value))

  function applySession(payload) {
    token.value = payload.token
    setToken(payload.token)
    user.value = payload.user
  }

  function resetSession() {
    token.value = null
    user.value = null
    clearToken()
  }

  async function login(identity, password) {
    const payload = await loginRequest(identity, password)
    applySession(payload)
    return payload
  }

  async function register(identity, password) {
    const payload = await registerRequest(identity, password)
    applySession(payload)
    return payload
  }

  async function fetchUser() {
    const payload = await fetchCurrentUser()
    user.value = payload
    return payload
  }

  async function logout() {
    try {
      await logoutRequest()
    } finally {
      resetSession()
    }
  }

  return { token, user, isAuthenticated, login, register, fetchUser, logout, resetSession }
})
