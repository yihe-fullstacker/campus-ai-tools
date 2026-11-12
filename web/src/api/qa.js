/** 校园问答接口，对应后端 /api/v1/qa/*。 */
import { get, post } from './client'

export function fetchQaSessions() {
  return get('/qa/sessions')
}

export function fetchQaMessages(sessionId) {
  return get(`/qa/messages/${sessionId}`)
}

export function askQuestion(question, sessionId = null) {
  return post('/qa/ask', { question, session_id: sessionId })
}
