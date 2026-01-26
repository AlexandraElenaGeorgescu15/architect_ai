import { useState, useCallback, useRef, useEffect } from 'react'
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

// Generation timeout in milliseconds (3 minutes)
const GENERATION_TIMEOUT_MS = 180000
// Inactivity timeout - if no progress updates for this long, consider it stuck
const INACTIVITY_TIMEOUT_MS = 60000

export function useGeneration() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const { addArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()

  // Refs to track timeouts and last activity
  const generationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inactivityTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastActivityRef = useRef<number>(Date.now())

  // Clear all timeouts
  const clearTimeouts = useCallback(() => {
    if (generationTimeoutRef.current) {
      clearTimeout(generationTimeoutRef.current)
      generationTimeoutRef.current = null
    }
    if (inactivityTimeoutRef.current) {
      clearTimeout(inactivityTimeoutRef.current)
      inactivityTimeoutRef.current = null
    }
  }, [])

  // Reset inactivity timeout on any activity
  const resetInactivityTimeout = useCallback(() => {
    lastActivityRef.current = Date.now()
    if (inactivityTimeoutRef.current) {
      clearTimeout(inactivityTimeoutRef.current)
    }
    if (isGenerating) {
      inactivityTimeoutRef.current = setTimeout(() => {
        console.warn('⏰ [FRONTEND] Generation appears stuck - no updates for 60 seconds')
        setIsGenerating(false)
        setProgress(prev => prev ? {
          ...prev,
          status: 'failed',
          error: 'Generation timed out - no response received. Please try again.'
        } : null)
        addNotification('error', 'Generation timed out. Please try again.')
      }, INACTIVITY_TIMEOUT_MS)
    }
  }, [isGenerating, addNotification])

  // Clean up timeouts on unmount
  useEffect(() => {
    return () => clearTimeouts()
  }, [clearTimeouts])

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
    // Reset inactivity timeout on progress
    resetInactivityTimeout()
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
    // Clear all timeouts on completion
    clearTimeouts()
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

    // CRITICAL FIX: Trigger artifact reload to ensure UI updates
    // This ensures artifacts appear even if WebSocket event doesn't fully update the store
    console.log('🔄 [FRONTEND] Triggering artifact reload after generation')
    window.dispatchEvent(new CustomEvent('reload-artifacts'))
  })

  // Listen for generation error events
  useWebSocket('generation.error', (data: unknown) => {
    const event = data as { job_id: string; error: string }
    console.error('❌ [FRONTEND] Received generation.error event:', {
      job_id: event.job_id,
      error: event.error
    })
    // Clear all timeouts on error
    clearTimeouts()
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

      // Clear any existing timeouts
      clearTimeouts()

      setIsGenerating(true)
      setProgress({
        jobId: '',
        progress: 0,
        status: 'pending',
        message: 'Initializing generation...',
      })

      // Set up generation timeout (3 minutes max)
      generationTimeoutRef.current = setTimeout(() => {
        console.warn('⏰ [FRONTEND] Generation timeout reached (3 minutes)')
        clearTimeouts()
        setIsGenerating(false)
        setProgress(prev => prev ? {
          ...prev,
          status: 'failed',
          error: 'Generation timed out after 3 minutes. Please try again.'
        } : null)
        addNotification('error', 'Generation timed out. Please try again.')
      }, GENERATION_TIMEOUT_MS)

      // Set up inactivity timeout (1 minute of no updates)
      resetInactivityTimeout()

      try {
        console.log('📤 [FRONTEND] Sending generation request to API...')
        const response = await generateArtifact(request)
        console.log('📥 [FRONTEND] Received generation response:', {
          job_id: response.job_id,
          status: response.status,
          has_artifact: !!response.artifact,
          artifact_type: response.artifact?.type
        })

        // Reset inactivity timeout on response
        resetInactivityTimeout()

        setProgress((prev) => ({
          ...prev!,
          jobId: response.job_id,
          status: response.status,
        }))

        // If artifact is immediately available, add it
        if (response.artifact) {
          console.log('✅ [FRONTEND] Artifact immediately available, adding to store:', response.artifact.id)
          clearTimeouts()
          addArtifact(response.artifact)
          setIsGenerating(false)
          addNotification('success', `Artifact "${response.artifact.type}" generated successfully!`)

          // Trigger celebration effect! 🎉
          window.dispatchEvent(new CustomEvent('celebrate-generation'))

          // CRITICAL FIX: Also trigger reload-artifacts for immediate response case
          console.log('🔄 [FRONTEND] Triggering artifact reload after immediate generation')
          window.dispatchEvent(new CustomEvent('reload-artifacts'))
        } else {
          console.log('⏳ [FRONTEND] Artifact not immediately available, waiting for WebSocket event (job_id:', response.job_id, ')')
        }

        return response
      } catch (error) {
        console.error('❌ [FRONTEND] Generation request failed:', error)
        clearTimeouts()
        setIsGenerating(false)
        const errorMessage = error instanceof Error ? error.message : 'Generation failed'
        addNotification('error', errorMessage)
        throw error
      }
    },
    [addArtifact, addNotification, clearTimeouts, resetInactivityTimeout]
  )

  const clearProgress = useCallback(() => {
    clearTimeouts()
    setProgress(null)
    setIsGenerating(false)
  }, [clearTimeouts])

  // Force stop generation (manual cancel)
  const cancelGeneration = useCallback(async () => {
    console.log('🛑 [FRONTEND] Cancelling generation manually')
    clearTimeouts()

    // If we have a job ID, cancel it on the backend too
    if (progress?.jobId) {
      try {
        const { default: api } = await import('../services/api')
        await api.post(`/api/generation/jobs/${progress.jobId}/cancel`)
        console.log('🛑 [FRONTEND] Backend job cancelled successfully')
      } catch (error) {
        console.warn('⚠️ [FRONTEND] Failed to cancel backend job:', error)
        // Continue with local cancellation even if backend fails
      }
    }

    setIsGenerating(false)
    setProgress(prev => prev ? {
      ...prev,
      status: 'cancelled',
      error: 'Generation cancelled by user'
    } : null)
    addNotification('info', 'Generation cancelled')
  }, [clearTimeouts, addNotification, progress?.jobId])

  return {
    isGenerating,
    progress,
    generate,
    clearProgress,
    cancelGeneration,
  }
}

