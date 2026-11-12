/** 业务模块接口：问答、助手、文档、搜索、知识库。 */
import { get, post, request } from './client'

// --- 校园问答 ---
export function askCampusQuestion(question, sessionId) {
  return post('/qa/ask', { question, session_id: sessionId ?? null })
}

export function fetchQaSessions() {
  return get('/qa/sessions')
}

export function fetchQaMessages(sessionId) {
  return get(`/qa/messages/${sessionId}`)
}

// --- 学习助手 ---
export function fetchChatSessions() {
  return get('/chat/sessions')
}

export function createChatSession(title) {
  const query = title ? `?title=${encodeURIComponent(title)}` : ''
  return post(`/chat/sessions${query}`)
}

export function fetchChatMessages(sessionId) {
  return get(`/chat/sessions/${sessionId}/messages`)
}

export function sendChatMessage(sessionId, content, template) {
  return post(`/chat/sessions/${sessionId}/messages`, { content, template: template || null })
}

// --- 文档 ---
export function fetchDocuments() {
  return get('/documents')
}

export function fetchDocumentDetail(id) {
  return get(`/documents/${id}`)
}

export function fetchDocumentSummary(id) {
  return get(`/documents/${id}/summary`)
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const token = localStorage.getItem('campus_ai_token')
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  const response = await fetch(`${base}/documents`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  })
  const text = await response.text()
  const data = text ? JSON.parse(text) : null
  if (!response.ok) {
    const error = new Error((data && data.message) || `上传失败（HTTP ${response.status}）`)
    error.code = (data && data.code) || 'HTTP_ERROR'
    throw error
  }
  return data
}

export function askDocument(id, question) {
  return post(`/documents/${id}/ask`, { question })
}

// --- 搜索 ---
export function searchAll(q, scope = 'all', type = null, page = 1) {
  const params = new URLSearchParams({ q, scope, page: String(page) })
  if (type) params.set('type', type)
  return get(`/search?${params.toString()}`)
}

// --- 知识库（管理员） ---
export function fetchKbItems(status = null, page = 1) {
  const params = new URLSearchParams({ page: String(page) })
  if (status) params.set('status', status)
  return get(`/kb/items?${params.toString()}`)
}

export function createKbItem(payload) {
  return post('/kb/items', payload)
}

export function updateKbItem(id, payload) {
  return request(`/kb/items/${id}`, { method: 'PUT', body: payload })
}

export function retireKbItem(id) {
  return post(`/kb/items/${id}/retire`)
}
