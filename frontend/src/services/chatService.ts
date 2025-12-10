import api from './api'

// Use empty string to make requests relative to the current origin
// This allows Vite's proxy to intercept /api/* requests in development
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  message: string
  conversation_history?: ChatMessage[]
  include_project_context?: boolean
}

export interface ChatResponse {
  message: string
  model_used: string
  provider: string
  timestamp: string
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/api/chat/message', request)
  return response.data
}

export async function* streamChatMessage(request: ChatRequest): AsyncGenerator<string, void, unknown> {
  // Get auth token for streaming request
  const token = localStorage.getItem('access_token')
  
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(request),
  })

  if (!response.body) {
    throw new Error('No response body')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'chunk' && data.content) {
              yield data.content
            } else if (data.type === 'complete' && data.content) {
              yield data.content
              return
            } else if (data.type === 'error') {
              throw new Error(data.error || 'Chat error')
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

