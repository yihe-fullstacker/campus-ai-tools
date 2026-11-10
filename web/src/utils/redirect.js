/**
 * 登录后跳转目标的安全处理。
 *
 * 只接受以单个 "/" 开头的同源路径：
 * - "//evil.com" 这类协议相对 URL 会被浏览器当作站外地址，必须拒绝；
 * - "https://evil.com" 这类绝对 URL 同样拒绝；
 * - 含反斜杠的路径一并拒绝，避免部分浏览器把 "\/" 解析成协议相对地址。
 */
export function safeRedirect(target, fallback = '/') {
  if (typeof target !== 'string') return fallback
  const trimmed = target.trim()
  if (!trimmed.startsWith('/')) return fallback
  if (trimmed.startsWith('//')) return fallback
  if (trimmed.includes('\\')) return fallback
  return trimmed
}
