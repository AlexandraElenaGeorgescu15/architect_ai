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
  error?: string
}

export interface DownloadStatusResponse {
  success: boolean
  status: 'not_started' | 'downloading' | 'completed' | 'failed'
  model_id: string
  progress: number
  error?: string
}

export interface DownloadedModel {
  id: string
  name: string
  downloaded_at: string
  path?: string
  converted_to_ollama?: boolean
}

/**
 * URL-encode a HuggingFace model ID for use in API paths.
 * Model IDs contain slashes (e.g., "codellama/CodeLlama-7b-Instruct-hf")
 * which need to be properly encoded for URL paths.
 */
function encodeModelId(modelId: string): string {
  // encodeURIComponent encodes slashes, but the backend uses {model_id:path}
  // which expects the raw path. We need to be careful here.
  // Actually, the backend uses FastAPI's path converter which handles slashes,
  // so we should NOT encode the slashes - just encode other special chars.
  return modelId.split('/').map(part => encodeURIComponent(part)).join('/')
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
 * This starts a background download - use getDownloadStatus to track progress.
 */
export async function downloadHuggingFaceModel(
  modelId: string,
  convertToOllama: boolean = true
): Promise<HuggingFaceDownloadResponse> {
  const encodedModelId = encodeModelId(modelId)
  const response = await api.post<HuggingFaceDownloadResponse>(
    `/api/huggingface/download/${encodedModelId}`,
    { convert_to_ollama: convertToOllama },
    { timeout: 30000 } // 30 second timeout for initial request (download runs in background)
  )
  return extractData(response)
}

/**
 * Get the download status for a model.
 */
export async function getDownloadStatus(
  modelId: string
): Promise<DownloadStatusResponse> {
  const encodedModelId = encodeModelId(modelId)
  const response = await api.get<DownloadStatusResponse>(
    `/api/huggingface/download/${encodedModelId}/status`
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
  const encodedModelId = encodeModelId(modelId)
  const response = await api.get(`/api/huggingface/info/${encodedModelId}`)
  return extractData(response)
}

