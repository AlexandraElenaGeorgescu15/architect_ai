import { useState, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { Artifact } from '../types'
import { generateArtifact, GenerationRequest, GenerationResponse } from '../services/generationService'

interface QualityPrediction {
  label: string
  confidence: number
  score: number
  reasons: Record<string, number>
}

interface GenerationProgress {
  jobId: string
  progress: number
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  message?: string
  chunk?: string
  artifact?: Artifact
  error?: string
  qualityPrediction?: QualityPrediction
}

export function useGeneration() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const { addArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()

  // Listen for generation progress events
  useWebSocket('generation.progress', (data: unknown) => {
    const event = data as {
      job_id: string
      progress: number
      status?: string
      message?: string
      quality_prediction?: QualityPrediction
    }
    console.log('📡 [FRONTEND] Received generation.progress event:', {
      job_id: event.job_id,
      progress: event.progress,
      status: event.status,
      message: event.message,
      has_quality_prediction: !!event.quality_prediction
    })
    setProgress((prev) => ({
      ...(prev ?? { jobId: event.job_id, progress: 0, status: 'in_progress' }),
      jobId: event.job_id,
      progress: event.progress,
      status: (event.status as GenerationProgress['status']) || prev?.status || 'in_progress',
      message: event.message || prev?.message,
      qualityPrediction: event.quality_prediction || prev?.qualityPrediction,
    }))
  })

  // Listen for generation chunk events (streaming)
  useWebSocket('generation.chunk', (data: unknown) => {
    const event = data as { job_id: string; chunk: string }
    console.log('📡 [FRONTEND] Received generation.chunk event:', {
      job_id: event.job_id,
      chunk_length: event.chunk.length,
      chunk_preview: event.chunk.substring(0, 50) + '...'
    })
    setProgress((prev) => ({
      ...prev!,
      chunk: prev?.chunk ? prev.chunk + event.chunk : event.chunk,
    }))
  })

  // Listen for generation complete events
  useWebSocket('generation.complete', (data: unknown) => {
    const event = data as { job_id: string; artifact: Artifact; validation_score?: number; is_valid?: boolean }
    console.log('✅ [FRONTEND] Received generation.complete event:', {
      job_id: event.job_id,
      artifact_type: event.artifact?.type,
      artifact_id: event.artifact?.id,
      validation_score: event.validation_score,
      is_valid: event.is_valid,
      has_content: !!event.artifact?.content,
      content_length: event.artifact?.content?.length || 0
    })
    setProgress((prev) => ({
      ...prev!,
      status: 'completed',
      artifact: event.artifact,
    }))
    console.log('📦 [FRONTEND] Adding artifact to store:', event.artifact.id)
    addArtifact(event.artifact)
    setIsGenerating(false)
    console.log('🎉 [FRONTEND] Generation completed successfully, showing notification')
    addNotification('success', `Artifact "${event.artifact.type}" generated successfully!`)
    
    // Trigger celebration effect! 🎉
    window.dispatchEvent(new CustomEvent('celebrate-generation'))
  })

  // Listen for generation error events
  useWebSocket('generation.error', (data: unknown) => {
    const event = data as { job_id: string; error: string }
    console.error('❌ [FRONTEND] Received generation.error event:', {
      job_id: event.job_id,
      error: event.error
    })
    setProgress((prev) => ({
      ...prev!,
      status: 'failed',
      error: event.error,
    }))
    setIsGenerating(false)
    console.log('⚠️ [FRONTEND] Showing error notification')
    addNotification('error', `Generation failed: ${event.error}`)
  })

  const generate = useCallback(
    async (request: GenerationRequest): Promise<GenerationResponse> => {
      console.log('🚀 [FRONTEND] Starting generation request:', {
        artifact_type: request.artifact_type,
        has_meeting_notes: !!request.meeting_notes,
        meeting_notes_length: request.meeting_notes?.length || 0,
        folder_id: request.folder_id,
        context_id: request.context_id,
        options: request.options
      })
      setIsGenerating(true)
      setProgress({
        jobId: '',
        progress: 0,
        status: 'pending',
        message: 'Initializing generation...',
      })

      try {
        console.log('📤 [FRONTEND] Sending generation request to API...')
        const response = await generateArtifact(request)
        console.log('📥 [FRONTEND] Received generation response:', {
          job_id: response.job_id,
          status: response.status,
          has_artifact: !!response.artifact,
          artifact_type: response.artifact?.type
        })
        setProgress((prev) => ({
          ...prev!,
          jobId: response.job_id,
          status: response.status,
        }))

        // If artifact is immediately available, add it
        if (response.artifact) {
          console.log('✅ [FRONTEND] Artifact immediately available, adding to store:', response.artifact.id)
          addArtifact(response.artifact)
          setIsGenerating(false)
          addNotification('success', `Artifact "${response.artifact.type}" generated successfully!`)
          
          // Trigger celebration effect! 🎉
          window.dispatchEvent(new CustomEvent('celebrate-generation'))
        } else {
          console.log('⏳ [FRONTEND] Artifact not immediately available, waiting for WebSocket event (job_id:', response.job_id, ')')
        }

        return response
      } catch (error) {
        console.error('❌ [FRONTEND] Generation request failed:', error)
        setIsGenerating(false)
        const errorMessage = error instanceof Error ? error.message : 'Generation failed'
        addNotification('error', errorMessage)
        throw error
      }
    },
    [addArtifact, addNotification]
  )

  const clearProgress = useCallback(() => {
    setProgress(null)
    setIsGenerating(false)
  }, [])

  return {
    isGenerating,
    progress,
    generate,
    clearProgress,
  }
}

