import api, { getBackendUrl } from './api'

// Get the backend URL dynamically - this respects the user's custom backend setting (ngrok, etc.)
function getApiBaseUrl(): string {
  // First check for custom backend URL (set by user in BackendSettings)
  const customUrl = getBackendUrl()
  if (customUrl) return customUrl
  
  // Fall back to environment variable or empty string for relative URLs
  return import.meta.env.VITE_API_URL || ''
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  message: string
  conversation_history?: ChatMessage[]
  include_project_context?: boolean
  session_id?: string  // For persistent context across messages
  write_mode?: boolean  // Enable write tools in agentic mode
}

// Session management for conversation persistence
const CHAT_SESSION_KEY = 'architect_ai_chat_session'
const CHAT_MESSAGES_KEY = 'architect_ai_chat_messages'

export function getOrCreateSessionId(): string {
  let sessionId = localStorage.getItem(CHAT_SESSION_KEY)
  if (!sessionId) {
    sessionId = `chat_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
    localStorage.setItem(CHAT_SESSION_KEY, sessionId)
  }
  return sessionId
}

export function clearChatSession(): void {
  localStorage.removeItem(CHAT_SESSION_KEY)
  localStorage.removeItem(CHAT_MESSAGES_KEY)
}

export function saveConversationToStorage(messages: ChatMessage[]): void {
  try {
    // Keep last 50 messages in storage
    const toSave = messages.slice(-50)
    localStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(toSave))
  } catch (e) {
    console.warn('Could not save chat messages to storage:', e)
  }
}

export function loadConversationFromStorage(): ChatMessage[] {
  try {
    const saved = localStorage.getItem(CHAT_MESSAGES_KEY)
    if (saved) {
      return JSON.parse(saved)
    }
  } catch (e) {
    console.warn('Could not load chat messages from storage:', e)
  }
  return []
}

export interface ChatResponse {
  message: string
  model_used: string
  provider: string
  timestamp: string
}

export interface ComponentInfo {
  name: string
  type: string
  description: string
  file_path: string
}

export interface ProjectSummary {
  project_name: string
  indexed_files: number
  tech_stack: string[]
  main_components: ComponentInfo[]
  patterns_detected: string[]
  knowledge_graph_stats: {
    nodes: number
    edges: number
    components: number
  }
  recent_files: string[]
  last_indexed: string | null
  greeting_message: string
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/api/chat/message', request)
  return response.data
}

/**
 * Fetch project summary for contextual chat greeting.
 * Returns information about indexed files, components, patterns, and KG stats.
 */
export async function getProjectSummary(): Promise<ProjectSummary> {
  const response = await api.get<ProjectSummary>('/api/chat/summary')
  return response.data
}

/**
 * Stream chat message with optional agentic and write modes.
 * In agentic mode, the AI can autonomously search the codebase.
 * In write mode (requires agentic), the AI can modify artifacts.
 */
export async function* streamChatMessage(
  request: ChatRequest,
  agenticMode: boolean = false,
  writeMode: boolean = false
): AsyncGenerator<{ type: string; content: string; tool?: string; is_write_tool?: boolean }, void, unknown> {
  // Get auth token for streaming request
  const token = localStorage.getItem('access_token')
  
  // Get the backend URL dynamically (respects custom backend settings)
  const baseUrl = getApiBaseUrl()
  
  // Use agentic endpoint if enabled
  const endpoint = agenticMode ? '/api/chat/agent/stream' : '/api/chat/stream'
  
  // Include write_mode in request if agentic mode and write mode are both enabled
  const requestWithWriteMode = {
    ...request,
    write_mode: agenticMode && writeMode
  }
  
  const response = await fetch(`${baseUrl}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // Required for ngrok free tier - bypasses the browser warning page
      'ngrok-skip-browser-warning': 'true',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(requestWithWriteMode),
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

          // Handle different event types
          if (data.type === 'status') {
            // Tool status update (agentic mode) - yield with type info
            yield { type: 'status', content: data.content, tool: data.tool }
          } else if (data.type === 'chunk' && data.content) {
            // Regular content chunk
            yield { type: 'chunk', content: data.content }
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

