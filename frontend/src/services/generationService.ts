import api, { extractData } from './api'
import { Artifact } from '../types'

export type ArtifactType =
  // Mermaid diagrams (Fully Parsable to Canvas - 7 types)
  | 'mermaid_flowchart'
  | 'mermaid_erd'
  | 'mermaid_class'
  | 'mermaid_state'
  | 'mermaid_sequence'
  | 'mermaid_architecture'
  | 'mermaid_api_sequence'
  // Mermaid diagrams (Recognized & Validated - 6 types)
  | 'mermaid_gantt'
  | 'mermaid_pie'
  | 'mermaid_journey'
  | 'mermaid_git_graph'
  | 'mermaid_mindmap'
  | 'mermaid_timeline'
  // C4 Diagrams
  | 'mermaid_c4_context'
  | 'mermaid_c4_container'
  | 'mermaid_c4_component'
  | 'mermaid_c4_deployment'
  // Other Mermaid
  | 'mermaid_data_flow'
  | 'mermaid_user_flow'
  | 'mermaid_component'
  | 'mermaid_system_overview'
  | 'mermaid_uml'
  // HTML diagrams (one for each Mermaid type)
  | 'html_flowchart'
  | 'html_erd'
  | 'html_class'
  | 'html_state'
  | 'html_sequence'
  | 'html_architecture'
  | 'html_api_sequence'
  | 'html_gantt'
  | 'html_pie'
  | 'html_journey'
  | 'html_git_graph'
  | 'html_mindmap'
  | 'html_timeline'
  | 'html_c4_context'
  | 'html_c4_container'
  | 'html_c4_component'
  | 'html_c4_deployment'
  | 'html_data_flow'
  | 'html_user_flow'
  | 'html_component'
  | 'html_system_overview'
  | 'html_uml'
  // Code artifacts
  | 'code_prototype'
  | 'dev_visual_prototype'
  | 'api_docs'
  // PM artifacts
  | 'jira'
  | 'workflows'
  | 'backlog'
  | 'personas'
  | 'estimations'
  | 'feature_scoring'

export interface GenerationRequest {
  context_id?: string
  meeting_notes?: string
  folder_id?: string
  artifact_type: ArtifactType
  options?: {
    max_retries?: number
    use_validation?: boolean
    temperature?: number
  }
}

export interface GenerationResponse {
  success: boolean
  job_id: string
  artifact_id?: string
  artifact?: Artifact
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  message?: string
}

export interface BulkGenerationItem extends GenerationRequest {}

export interface BulkGenerationResult {
  job_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  artifact?: Artifact
  error?: string
}

export interface GenerationJob {
  job_id: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  artifact_id?: string
  progress?: number
  created_at: string
  completed_at?: string
}

/**
 * Generate an artifact (non-streaming).
 */
export async function generateArtifact(request: GenerationRequest): Promise<GenerationResponse> {
  const response = await api.post<GenerationResponse>('/api/generation/generate', request)
  return extractData(response)
}

export async function bulkGenerate(items: BulkGenerationItem[]): Promise<BulkGenerationResult[]> {
  const response = await api.post<BulkGenerationResult[]>('/api/generation/bulk', { items })
  return response.data
}

/**
 * Stream artifact generation (returns EventSource or WebSocket).
 */
export function streamGeneration(
  request: GenerationRequest,
  onChunk: (chunk: string) => void,
  onComplete: (artifact: Artifact) => void,
  onError: (error: Error) => void
): EventSource {
  // For now, use EventSource if backend supports SSE
  // Otherwise, WebSocket will be used via websocketService
  const eventSource = new EventSource(
    `${api.defaults.baseURL}/api/generation/stream?context_id=${request.context_id}&artifact_type=${request.artifact_type}`
  )

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'chunk') {
      onChunk(data.content)
    } else if (data.type === 'complete') {
      onComplete(data.artifact)
      eventSource.close()
    }
  }

  eventSource.onerror = (error) => {
    onError(new Error('Stream connection error'))
    eventSource.close()
  }

  return eventSource
}

/**
 * Get generation job status.
 */
export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  const response = await api.get<GenerationJob>(`/api/generation/jobs/${jobId}`)
  return extractData(response)
}

/**
 * List all artifacts.
 */
export async function listArtifacts(): Promise<Artifact[]> {
  const response = await api.get<Artifact[]>('/api/generation/artifacts')
  return extractData(response)
}

/**
 * Get artifact by ID.
 */
export async function getArtifact(artifactId: string): Promise<Artifact> {
  const response = await api.get<Artifact>(`/api/generation/artifacts/${artifactId}`)
  return extractData(response)
}

/**
 * Regenerate an artifact.
 */
export async function regenerateArtifact(
  artifactId: string,
  options?: GenerationRequest['options']
): Promise<GenerationResponse> {
  const response = await api.post<GenerationResponse>(
    `/api/generation/artifacts/${artifactId}/regenerate`,
    { options }
  )
  return extractData(response)
}

/**
 * Update an artifact's content.
 */
export async function updateArtifact(
  artifactId: string,
  content: string,
  metadata?: Record<string, any>
): Promise<{ success: boolean; artifact_id: string; message: string }> {
  const response = await api.put<{ success: boolean; artifact_id: string; message: string }>(
    `/api/generation/artifacts/${artifactId}`,
    { content, metadata }
  )
  return extractData(response)
}

