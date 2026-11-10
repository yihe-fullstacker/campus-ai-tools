import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../src/stores/auth'

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.unstubAllGlobals()
  })

  it('登录成功后保存令牌与用户信息', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            token: 'token-abc',
            token_type: 'bearer',
            expires_at: '2026-11-17T00:00:00Z',
            user: { id: 1, identity: '20240101', role: 'student', created_at: '2026-11-10T00:00:00Z' },
          }),
      }),
    )

    const auth = useAuthStore()
    await auth.login('20240101', 'campus2024')

    expect(auth.token).toBe('token-abc')
    expect(auth.user.identity).toBe('20240101')
    expect(auth.isAuthenticated).toBe(true)
    expect(localStorage.getItem('campus_ai_token')).toBe('token-abc')
  })

  it('登录失败时抛出后端给出的中文提示', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({ code: 'AUTH_CREDENTIALS_INVALID', message: '学号/邮箱或密码不正确。' }),
      }),
    )

    const auth = useAuthStore()
    await expect(auth.login('20240101', 'wrong-password')).rejects.toThrow('学号/邮箱或密码不正确。')
    expect(auth.isAuthenticated).toBe(false)
  })

  it('登出后清空本地令牌', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 204, text: async () => '' }),
    )
    localStorage.setItem('campus_ai_token', 'token-abc')

    const auth = useAuthStore()
    await auth.logout()

    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('campus_ai_token')).toBeNull()
  })

  it('刷新后凭本地令牌恢复用户信息', async () => {
    localStorage.setItem('campus_ai_token', 'token-abc')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            id: 3,
            identity: '20240101',
            role: 'student',
            created_at: '2026-11-10T00:00:00Z',
          }),
      }),
    )

    const auth = useAuthStore()
    const user = await auth.restoreSession()

    expect(user.identity).toBe('20240101')
    expect(auth.user.identity).toBe('20240101')
    expect(auth.isAuthenticated).toBe(true)
  })

  it('没有令牌时不做任何请求', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const auth = useAuthStore()
    const user = await auth.restoreSession()

    expect(user).toBeNull()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('令牌失效时清除本地会话', async () => {
    localStorage.setItem('campus_ai_token', 'token-abc')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({ code: 'AUTH_TOKEN_EXPIRED', message: '登录已过期，请重新登录。' }),
      }),
    )

    const auth = useAuthStore()
    const user = await auth.restoreSession()

    expect(user).toBeNull()
    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
    expect(localStorage.getItem('campus_ai_token')).toBeNull()
  })
})
