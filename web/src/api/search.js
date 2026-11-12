/** 统一搜索接口，对应后端 /api/v1/search。 */
import { get } from './client'

export function searchResources({ q, scope = 'all', type = '', page = 1, pageSize = 20 }) {
  const params = new URLSearchParams({ q, scope, page: String(page), page_size: String(pageSize) })
  if (type) params.set('type', type)
  return get(`/search?${params.toString()}`)
}
