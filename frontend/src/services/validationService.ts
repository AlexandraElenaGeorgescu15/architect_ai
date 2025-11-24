import api, { extractData } from './api'
import { ArtifactType } from './generationService'

export interface ValidationRequest {
  artifact_type: ArtifactType
  content: string
  meeting_notes?: string
}

export interface ValidationResult {
  is_valid: boolean
  score: number
  errors: string[]
  warnings: string[]
  suggestions: string[]
  details?: Record<string, unknown>
}

/**
 * Validate an artifact.
 */
export async function validateArtifact(request: ValidationRequest): Promise<ValidationResult> {
  const response = await api.post<ValidationResult>('/api/validation/validate', request)
  return extractData(response)
}

/**
 * Validate multiple artifacts in batch.
 */
export async function validateBatch(
  requests: ValidationRequest[]
): Promise<ValidationResult[]> {
  const response = await api.post<ValidationResult[]>('/api/validation/validate-batch', {
    artifacts: requests,
  })
  return extractData(response)
}

/**
 * Get validation statistics.
 */
export async function getValidationStats(): Promise<{
  total_validations: number
  avg_score: number
  pass_rate: number
}> {
  const response = await api.get('/api/validation/stats')
  return extractData(response)
}

