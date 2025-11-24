import api, { extractData } from './api'

export interface HuggingFaceModel {
  id: string
  name: string
  downloads: number
  likes: number
  tags: string[]
  task?: string
  description?: string
}

export interface HuggingFaceSearchResponse {
  success: boolean
  results: HuggingFaceModel[]
  count: number
}

export interface HuggingFaceDownloadResponse {
  success: boolean
  message: string
  model_id: string
  convert_to_ollama?: boolean
}

export interface DownloadedModel {
  id: string
  name: string
  downloaded_at: string
  path?: string
  converted_to_ollama?: boolean
}

/**
 * Search models on HuggingFace Hub.
 */
export async function searchHuggingFaceModels(
  query: string,
  task?: string,
  limit: number = 20
): Promise<HuggingFaceSearchResponse> {
  const params = new URLSearchParams({ query, limit: limit.toString() })
  if (task) params.append('task', task)
  
  const response = await api.get<HuggingFaceSearchResponse>(
    `/api/huggingface/search?${params.toString()}`
  )
  return extractData(response)
}

/**
 * Download a model from HuggingFace and optionally convert to Ollama.
 */
export async function downloadHuggingFaceModel(
  modelId: string,
  convertToOllama: boolean = true
): Promise<HuggingFaceDownloadResponse> {
  const response = await api.post<HuggingFaceDownloadResponse>(
    `/api/huggingface/download/${modelId}`,
    { convert_to_ollama: convertToOllama }
  )
  return extractData(response)
}

/**
 * List downloaded HuggingFace models.
 */
export async function listDownloadedHuggingFaceModels(): Promise<{
  success: boolean
  models: DownloadedModel[]
  count: number
}> {
  const response = await api.get('/api/huggingface/downloaded')
  return extractData(response)
}

/**
 * Get model information from HuggingFace.
 */
export async function getHuggingFaceModelInfo(modelId: string): Promise<{
  success: boolean
  model: HuggingFaceModel
}> {
  const response = await api.get(`/api/huggingface/info/${modelId}`)
  return extractData(response)
}

