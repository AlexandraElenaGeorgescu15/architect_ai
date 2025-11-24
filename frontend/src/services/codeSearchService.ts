import api from './api'

export interface SemanticSearchResult {
  content: string
  file_path: string
  score: number
  start_line?: number
  end_line?: number
  metadata: Record<string, unknown>
}

export interface SemanticSearchResponse {
  query: string
  results: SemanticSearchResult[]
  total: number
}

export interface SemanticSearchRequest {
  query: string
  limit?: number
  metadata_filter?: Record<string, unknown>
}

export async function semanticSearch(request: SemanticSearchRequest): Promise<SemanticSearchResponse> {
  const response = await api.post<SemanticSearchResponse>('/api/code-search/query', request)
  return response.data
}

