/** 文档解析接口，对应后端 /api/v1/documents/*。 */
import { download, get, post, upload } from './client'

export function fetchDocuments() {
  return get('/documents')
}

export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return upload('/documents', formData)
}

export function fetchDocument(documentId) {
  return get(`/documents/${documentId}`)
}

export function fetchDocumentSummary(documentId) {
  return get(`/documents/${documentId}/summary`)
}

export function askDocument(documentId, question) {
  return post(`/documents/${documentId}/ask`, { question })
}

export function downloadDocumentSummary(documentId) {
  return download(`/documents/${documentId}/summary/export`, `summary-${documentId}.md`)
}
