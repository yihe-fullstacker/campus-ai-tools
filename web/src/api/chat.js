/** 学习助手接口，对应后端 /api/v1/chat/*。 */
import { get, post } from './client'

export function fetchChatSessions() {
  return get('/chat/sessions')
}

export function createChatSession(title = null) {
  const query = title ? `?title=${encodeURIComponent(title)}` : ''
  return post(`/chat/sessions${query}`)
}

export function fetchChatMessages(sessionId) {
  return get(`/chat/sessions/${sessionId}/messages`)
}

export function sendChatMessage(sessionId, content, template = 'free') {
  return post(`/chat/sessions/${sessionId}/messages`, { content, template })
}
