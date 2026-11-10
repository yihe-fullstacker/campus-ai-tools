/**
 * 接口客户端：统一拼接前缀、注入 Bearer 令牌、归一化错误。
 *
 * 后端错误统一为 {"code": "<机器码>", "message": "<中文提示>"}，
 * 这里转换为 ApiError，页面只需展示 error.message 并按 error.code 分支。
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const TOKEN_KEY = 'campus_ai_token'

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function parseBody(response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export async function request(path, options = {}) {
  const { method = 'GET', body, headers = {}, auth = true } = options
  const finalHeaders = { Accept: 'application/json', ...headers }
  if (body !== undefined) finalHeaders['Content-Type'] = 'application/json'

  const token = getToken()
  if (auth && token) finalHeaders.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: finalHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', '网络连接失败，请检查网络后重试。')
  }

  const data = await parseBody(response)
  if (!response.ok) {
    throw new ApiError(
      response.status,
      (data && data.code) || 'HTTP_ERROR',
      (data && data.message) || `请求失败（HTTP ${response.status}）`,
    )
  }
  return data
}

export function get(path, options = {}) {
  return request(path, { ...options, method: 'GET' })
}

export function post(path, body, options = {}) {
  return request(path, { ...options, method: 'POST', body })
}
