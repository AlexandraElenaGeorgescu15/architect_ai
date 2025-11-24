/**
 * Synthetic Data Service - Frontend client for synthetic dataset generation
 */

import axios from 'axios'

const API_BASE = '/api/synthetic-data'

export interface SyntheticGenerationRequest {
  artifact_type: string
  target_count: number
  model_backend?: 'auto' | 'gemini' | 'grok' | 'phi-local'
  complexity?: 'Simple' | 'Mixed' | 'Complex'
  auto_integrate?: boolean
}

export interface SyntheticGenerationResponse {
  success: boolean
  artifact_type: string
  generated_count: number
  target_count: number
  backend_used: string
  integrated: boolean
  examples_preview: Array<{
    instruction: string
    input: string
    output: string
    category: string
    difficulty: string
  }>
  errors: string[]
}

export interface BackendInfo {
  id: string
  name: string
  type: 'api' | 'local'
  free: boolean
  quota: string
  available: boolean
}

export interface SyntheticStats {
  artifact_type: string
  real_examples: number
  synthetic_examples: number
  total_examples: number
  synthetic_percentage: number
  ready_for_training: boolean
}

/**
 * Generate synthetic training examples
 */
export async function generateSyntheticData(
  request: SyntheticGenerationRequest
): Promise<SyntheticGenerationResponse> {
  const response = await axios.post<SyntheticGenerationResponse>(
    `${API_BASE}/generate`,
    request
  )
  return response.data
}

/**
 * List available generation backends
 */
export async function listBackends(): Promise<BackendInfo[]> {
  const response = await axios.get<BackendInfo[]>(`${API_BASE}/backends`)
  return response.data
}

/**
 * Get synthetic vs real stats for an artifact type
 */
export async function getStats(artifactType: string): Promise<SyntheticStats> {
  const response = await axios.get<SyntheticStats>(
    `${API_BASE}/stats/${artifactType}`
  )
  return response.data
}

/**
 * Get stats for all artifact types
 */
export async function getAllStats(): Promise<Record<string, SyntheticStats>> {
  const response = await axios.get<Record<string, SyntheticStats>>(
    `${API_BASE}/stats`
  )
  return response.data
}

/**
 * Clear synthetic examples for an artifact type
 */
export async function clearSynthetic(artifactType: string): Promise<{
  success: boolean
  artifact_type: string
  removed_count: number
  remaining_count: number
}> {
  const response = await axios.delete(`${API_BASE}/clear/${artifactType}`)
  return response.data
}

