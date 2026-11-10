import { beforeEach, describe, expect, it, vi } from 'vitest'

import { API_BASE_URL, ApiError, clearToken, request, setToken } from '../src/api/client'

function mockFetch(response) {
  const fetchMock = vi.fn().mockResolvedValue(response)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('拼接接口前缀并自动带上 Bearer 令牌', async () => {
    setToken('token-123')
    const fetchMock = mockFetch({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ id: 1, identity: '20240101' }),
    })

    const data = await request('/users/me')

    expect(data).toEqual({ id: 1, identity: '20240101' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_BASE_URL}/users/me`)
    expect(init.method).toBe('GET')
    expect(init.headers.Authorization).toBe('Bearer token-123')
  })

  it('未登录时不发送 Authorization 头', async () => {
    const fetchMock = mockFetch({ ok: true, status: 200, text: async () => '{}' })

    await request('/auth/login', { method: 'POST', body: { identity: 'a', password: 'b' } })

    const [, init] = fetchMock.mock.calls[0]
    expect(init.headers.Authorization).toBeUndefined()
    expect(init.body).toBe(JSON.stringify({ identity: 'a', password: 'b' }))
  })

  it('错误响应抛出带 code 与 message 的 ApiError', async () => {
    mockFetch({
      ok: false,
      status: 400,
      text: async () =>
        JSON.stringify({ code: 'AUTH_PASSWORD_WEAK', message: '密码需同时包含字母和数字。' }),
    })

    const error = await request('/auth/register', { method: 'POST', body: {} }).catch((err) => err)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(400)
    expect(error.code).toBe('AUTH_PASSWORD_WEAK')
    expect(error.message).toBe('密码需同时包含字母和数字。')
  })

  it('响应体不是 JSON 时也能给出可读错误', async () => {
    mockFetch({ ok: false, status: 502, text: async () => '<html>bad gateway</html>' })

    const error = await request('/qa/ask', { method: 'POST', body: {} }).catch((err) => err)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('HTTP_ERROR')
    expect(error.message).toContain('502')
  })

  it('网络异常转换为 NETWORK_ERROR', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const error = await request('/healthz').catch((err) => err)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('NETWORK_ERROR')
  })

  it('令牌存取与清除', () => {
    setToken('abc')
    expect(localStorage.getItem('campus_ai_token')).toBe('abc')
    clearToken()
    expect(localStorage.getItem('campus_ai_token')).toBeNull()
  })
})
