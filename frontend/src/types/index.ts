// API Response Types
export interface ApiResponse<T> {
  data: T
  message?: string
  error?: string
}

// Artifact Types
export interface Artifact {
  id: string
  type: string
  content: string
  score?: number
  created_at: string
  updated_at: string
}

// Context Types
export interface Context {
  id: string
  rag_chunks?: string[]
  knowledge_graph?: Record<string, unknown>
  patterns?: Record<string, unknown>
  assembled_context?: string
  created_at: string
}

export interface ContextResponse {
  success: boolean
  context_id: string
  assembled_context: string
  rag_chunks?: string[]
  knowledge_graph?: Record<string, unknown>
  patterns?: Record<string, unknown>
  message?: string
}

// Model Types
export interface Model {
  id: string
  name: string
  provider: 'ollama' | 'huggingface' | 'cloud'
  status: 'available' | 'downloading' | 'unavailable'
  created_at: string
}

// Training Job Types
export interface TrainingJob {
  id: string
  status: 'queued' | 'preparing' | 'training' | 'converting' | 'completed' | 'failed' | 'cancelled'
  progress?: number
  artifact_type?: string
  created_at: string
  completed_at?: string
}

// WebSocket Event Types
export interface WebSocketEvent {
  type: string
  data: unknown
  timestamp: string
}

