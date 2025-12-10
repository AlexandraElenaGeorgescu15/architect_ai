import api, { extractData } from './api'
import { TrainingJob } from '../types'
import { ArtifactType } from './generationService'

export type TrainingStatus =
  | 'queued'
  | 'preparing'
  | 'training'
  | 'converting'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface TrainingTriggerRequest {
  artifact_type?: ArtifactType
  force?: boolean
}

export interface TrainingQueue {
  queued: TrainingJob[]
  in_progress: TrainingJob[]
  completed: TrainingJob[]
  failed: TrainingJob[]
}

/**
 * List all training jobs.
 */
export async function listTrainingJobs(
  status?: TrainingStatus,
  artifactType?: ArtifactType
): Promise<TrainingJob[]> {
  const params = new URLSearchParams()
  if (status) params.append('status', status)
  if (artifactType) params.append('artifact_type', artifactType)

  const response = await api.get<TrainingJob[]>(
    `/api/training/jobs?${params.toString()}`
  )
  return extractData(response)
}

/**
 * Get training job by ID.
 */
export async function getTrainingJob(jobId: string): Promise<TrainingJob> {
  const response = await api.get<TrainingJob>(`/api/training/jobs/${jobId}`)
  return extractData(response)
}

/**
 * Trigger a training job.
 * Returns the full TrainingJob object from the backend.
 */
export async function triggerTraining(
  request?: TrainingTriggerRequest
): Promise<TrainingJob> {
  const response = await api.post<TrainingJob>(
    '/api/training/trigger',
    request || {}
  )
  return extractData(response)
}

/**
 * Get training queue.
 */
export async function getTrainingQueue(): Promise<TrainingQueue> {
  const response = await api.get<TrainingQueue>('/api/training/queue')
  return extractData(response)
}

/**
 * Cancel a training job.
 */
export async function cancelTrainingJob(jobId: string): Promise<{ success: boolean; message: string }> {
  const response = await api.post<{ success: boolean; message: string }>(
    `/api/training/jobs/${jobId}/cancel`
  )
  return extractData(response)
}

/**
 * Get training statistics.
 */
export async function getTrainingStats(): Promise<{
  total_jobs: number
  by_status: Record<TrainingStatus, number>
  avg_duration?: number
}> {
  const response = await api.get('/api/training/stats')
  return extractData(response)
}

