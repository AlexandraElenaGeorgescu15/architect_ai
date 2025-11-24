import api, { extractData } from './api'
import { Model } from '../types'
import { ArtifactType } from './generationService'

export interface ModelRouting {
  artifact_type: ArtifactType
  model_id: string
  provider: 'ollama' | 'huggingface' | 'cloud'
  priority: number
}

export interface RoutingConfig {
  default_model: string
  routing: ModelRouting[]
}

/**
 * List all available models.
 */
export async function listModels(): Promise<Model[]> {
  const response = await api.get<Model[]>('/api/models/')
  return extractData(response)
}

/**
 * Get model by ID.
 */
export async function getModel(modelId: string): Promise<Model> {
  const response = await api.get<Model>(`/api/models/${modelId}`)
  return extractData(response)
}

/**
 * Download a model.
 */
export async function downloadModel(modelId: string): Promise<{ success: boolean; message: string }> {
  const response = await api.post<{ success: boolean; message: string }>(
    `/api/models/${modelId}/download`
  )
  return extractData(response)
}

/**
 * Get current routing configuration.
 */
export async function getRouting(): Promise<RoutingConfig> {
  const response = await api.get<RoutingConfig>('/api/models/routing')
  return extractData(response)
}

/**
 * Update routing configuration.
 */
export async function updateRouting(config: RoutingConfig): Promise<RoutingConfig> {
  const response = await api.put<RoutingConfig>('/api/models/routing', config)
  return extractData(response)
}

/**
 * Get model statistics.
 */
export async function getModelStats(): Promise<{
  total_models: number
  by_provider: Record<string, number>
  by_status: Record<string, number>
}> {
  const response = await api.get('/api/models/stats')
  return extractData(response)
}

