import api, { extractData } from './api'
import { Artifact } from '../types'

// Must match backend Literal["positive", "negative", "correction"]
export type FeedbackType = 'positive' | 'negative' | 'correction'

export interface FeedbackRequest {
  artifact_id: string
  score: number
  notes?: string
  feedback_type: FeedbackType
  corrected_content?: string
}

export interface FeedbackResponse {
  success: boolean
  feedback_id: string
  message: string
  training_stats?: {
    total_examples: number
    ready_for_training: boolean
    examples_needed: number
  }
}

export interface FeedbackHistoryItem {
  feedback_id: string
  artifact_id: string
  score: number
  feedback_type: FeedbackType
  notes?: string
  created_at: string
}

/**
 * Submit feedback on an artifact.
 */
export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  const response = await api.post<FeedbackResponse>('/api/feedback/', request)
  return extractData(response)
}

/**
 * Get feedback history.
 */
export async function getFeedbackHistory(): Promise<FeedbackHistoryItem[]> {
  const response = await api.get<FeedbackHistoryItem[]>('/api/feedback/history')
  return extractData(response)
}

/**
 * Get feedback statistics.
 */
export async function getFeedbackStats(): Promise<{
  total_feedback: number
  avg_score: number
  by_type: Record<FeedbackType, number>
}> {
  const response = await api.get('/api/feedback/stats')
  return extractData(response)
}

