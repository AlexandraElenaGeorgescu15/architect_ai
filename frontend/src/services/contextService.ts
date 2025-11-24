import api, { extractData } from './api'
import { Context, ContextResponse } from '../types'

export interface ContextBuildRequest {
  meeting_notes?: string
  folder_id?: string
  repo_id?: string
  include_rag?: boolean
  include_kg?: boolean
  include_patterns?: boolean
  include_ml_features?: boolean
  max_rag_chunks?: number
  kg_depth?: number
  artifact_type?: string
}

export interface ContextStats {
  total_contexts: number
  avg_chunks: number
  avg_kg_nodes: number
}

/**
 * Build context from meeting notes and repository.
 */
export async function buildContext(request: ContextBuildRequest): Promise<ContextResponse> {
  const response = await api.post<ContextResponse>('/api/context/build', request)
  return extractData(response)
}

/**
 * Get context by ID.
 */
export async function getContext(contextId: string): Promise<Context> {
  const response = await api.get<Context>(`/api/context/${contextId}`)
  return extractData(response)
}

/**
 * Get context statistics.
 */
export async function getContextStats(): Promise<ContextStats> {
  const response = await api.get<ContextStats>('/api/context/stats')
  return extractData(response)
}

