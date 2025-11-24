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
    setProgress((prev) => ({
      ...prev!,
      chunk: prev?.chunk ? prev.chunk + event.chunk : event.chunk,
    }))
  })

  // Listen for generation complete events
  useWebSocket('generation.complete', (data: unknown) => {
    const event = data as { job_id: string; artifact: Artifact }
    setProgress((prev) => ({
      ...prev!,
      status: 'completed',
      artifact: event.artifact,
    }))
    addArtifact(event.artifact)
    setIsGenerating(false)
    addNotification('success', `Artifact "${event.artifact.type}" generated successfully!`)
    
    // Trigger celebration effect! 🎉
    window.dispatchEvent(new CustomEvent('celebrate-generation'))
  })

  // Listen for generation error events
  useWebSocket('generation.error', (data: unknown) => {
    const event = data as { job_id: string; error: string }
    setProgress((prev) => ({
      ...prev!,
      status: 'failed',
      error: event.error,
    }))
    setIsGenerating(false)
    addNotification('error', `Generation failed: ${event.error}`)
  })

  const generate = useCallback(
    async (request: GenerationRequest): Promise<GenerationResponse> => {
      setIsGenerating(true)
      setProgress({
        jobId: '',
        progress: 0,
        status: 'pending',
        message: 'Initializing generation...',
      })

      try {
        const response = await generateArtifact(request)
        setProgress((prev) => ({
          ...prev!,
          jobId: response.job_id,
          status: response.status,
        }))

        // If artifact is immediately available, add it
        if (response.artifact) {
          addArtifact(response.artifact)
          setIsGenerating(false)
          addNotification('success', `Artifact "${response.artifact.type}" generated successfully!`)
          
          // Trigger celebration effect! 🎉
          window.dispatchEvent(new CustomEvent('celebrate-generation'))
        }

        return response
      } catch (error) {
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

