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
        if (!line.startsWith('data: ')) continue

        try {
          const data = JSON.parse(line.slice(6))

          // For streaming we build up the response from incremental "chunk" events.
          // Some backends also send a final "complete" event that includes the full
          // content again. If we yielded that here, the assistant reply would appear
          // duplicated (chunks + full content). To avoid this, we treat "complete"
          // as a control signal and DO NOT yield its content.
          if (data.type === 'chunk' && data.content) {
            yield data.content
          } else if (data.type === 'complete') {
            // Stop the stream without appending the full content again
            return
          } else if (data.type === 'error') {
            throw new Error(data.error || 'Chat error')
          }
        } catch {
          // Skip invalid JSON lines without breaking the stream
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

