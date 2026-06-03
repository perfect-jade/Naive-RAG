import api from './index'

export interface Industry {
  id: string
  name: string
  slug: string
  description: string
  doc_count: number
  chunk_count: number
  chunk_size: number
  chunk_overlap: number
  created_at: string
  updated_at: string
}

export const industryApi = {
  list() {
    return api.get('/industries')
  },
  detail(slug: string) {
    return api.get(`/industries/${slug}`)
  },
  create(data: { name: string; description?: string }) {
    return api.post('/industries', data)
  },
  update(slug: string, data: { name?: string; description?: string; chunk_size?: number; chunk_overlap?: number }) {
    return api.put(`/industries/${slug}`, data)
  },
  delete(slug: string) {
    return api.delete(`/industries/${slug}`)
  },
  getChunkConfig(slug: string) {
    return api.get(`/industries/${slug}/chunk-config`)
  },
}