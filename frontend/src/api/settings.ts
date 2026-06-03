import api from './index'

export interface ModelItem {
  id: string
  name: string
  description: string
  dimension?: number
}

export interface Settings {
  llm_model: string
  embedding_model: string
  api_key_configured: boolean
}

export const settingsApi = {
  get() {
    return api.get('/settings')
  },
  update(data: { llm_model?: string; embedding_model?: string; api_key?: string }) {
    return api.put('/settings', data)
  },
  getModels() {
    return api.get('/settings/models')
  },
  health() {
    return api.get('/health')
  },
}