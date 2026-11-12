/** 用户自带模型配置接口，对应后端 /api/v1/llm-configs/*。 */
import { get, post, request } from './client'

export function fetchPresets() {
  return get('/llm-configs/presets', { auth: false })
}

export function fetchConfigs() {
  return get('/llm-configs')
}

export function createConfig(payload) {
  return post('/llm-configs', payload)
}

export function updateConfig(id, payload) {
  return request(`/llm-configs/${id}`, { method: 'PUT', body: payload })
}

export function activateConfig(id) {
  return post(`/llm-configs/${id}/activate`)
}

export function deleteConfig(id) {
  return request(`/llm-configs/${id}`, { method: 'DELETE' })
}

export function testConfig(payload) {
  return post('/llm-configs/test', payload)
}
