import api from './api'

export type PhaseStatus =
  | 'pending'
  | 'running'
  | 'complete'
  | 'error'
  | 'skipped'

export interface SystemPhaseStatus {
  name: string
  title?: string
  status: PhaseStatus
  message?: string
  progress?: number
  details?: Record<string, unknown>
  last_updated?: string
}

export interface SystemHealthResponse {
  status: string
  service: string
  version: string
  ready: boolean
  overall_status?: string
  message?: string
  last_updated?: string
  phases?: Record<string, SystemPhaseStatus>
  cache?: Record<string, unknown>
  metrics?: {
    counters: number
    gauges: number
    timers: number
  }
}

export async function fetchSystemHealth(): Promise<SystemHealthResponse> {
  const response = await api.get<SystemHealthResponse>('/api/health')

  // Validate response - Vercel might return index.html (string) for 404s
  if (typeof response.data === 'string' || !response.data || typeof response.data !== 'object') {
    throw new Error('Invalid backend response (received HTML or empty)')
  }

  return response.data
}

