import api from './index'

export interface ChatMessage {
  role: string
  content: string
}

export interface ChatSession {
  id: string
  title: string
  industry: string
  industry_name: string
  message_count: number
  created_at: string
  updated_at: string
}

export const chatApi = {
  route(query: string) {
    return api.post('/chat/route', { query })
  },
  createSession() {
    return api.post('/chat/history')
  },
  getHistory() {
    return api.get('/chat/history')
  },
  getSessionMessages(sessionId: string) {
    return api.get(`/chat/history/${sessionId}`)
  },
  deleteSession(sessionId: string) {
    return api.delete(`/chat/history/${sessionId}`)
  },
}