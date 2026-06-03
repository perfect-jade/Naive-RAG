import api from './index'

export interface KnowledgeDoc {
  id: string
  title: string
  source: string
  chunk_count: number
  tags: string[]
  created_at: string
}

export const knowledgeApi = {
  list(slug: string, page = 1, pageSize = 10) {
    return api.get(`/industries/${slug}/knowledge`, { params: { page, page_size: pageSize } })
  },
  insertText(slug: string, data: { title?: string; content: string; tags?: string[] }) {
    return api.post(`/industries/${slug}/knowledge/text`, data)
  },
  uploadFiles(slug: string, files: File[]) {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    return api.post(`/industries/${slug}/knowledge/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete(slug: string, docId: string) {
    return api.delete(`/industries/${slug}/knowledge/${docId}`)
  },
  getDocumentChunks(slug: string, docId: string) {
    return api.get(`/industries/${slug}/knowledge/${docId}/chunks`)
  },
  deleteChunk(slug: string, docId: string, chunkId: string) {
    return api.delete(`/industries/${slug}/knowledge/${docId}/chunks/${chunkId}`)
  },
}