/** 知识库管理接口（仅管理员），对应后端 /api/v1/kb/*。 */
import { get, post, request } from './client'

export function fetchKbItems({ status = '', page = 1, pageSize = 20 } = {}) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (status) params.set('status', status)
  return get(`/kb/items?${params.toString()}`)
}

export function createKbItem(payload) {
  return post('/kb/items', payload)
}

export function updateKbItem(itemId, payload) {
  return request(`/kb/items/${itemId}`, { method: 'PUT', body: payload })
}

export function retireKbItem(itemId) {
  return post(`/kb/items/${itemId}/retire`)
}

export function importKbItems(items) {
  return post('/kb/import', items)
}
