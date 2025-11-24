import { useState, useCallback } from 'react'
import { useWebSocket } from './useWebSocket'
import { useTrainingStore } from '../stores/trainingStore'
import { useUIStore } from '../stores/uiStore'
import { TrainingJob } from '../types'
import {
  triggerTraining,
  TrainingTriggerRequest,
  getTrainingJob,
  listTrainingJobs,
} from '../services/trainingService'

interface TrainingProgress {
  jobId: string
  progress: number
  status: TrainingJob['status']
  error?: string
}

export function useTraining() {
  const [isTraining, setIsTraining] = useState(false)
  const [progress, setProgress] = useState<TrainingProgress | null>(null)
  const { addJob, updateJob } = useTrainingStore()
  const { addNotification } = useUIStore()

  // Listen for training progress events
  useWebSocket('training.progress', (data: unknown) => {
    const event = data as { job_id: string; progress: number; status: string }
    setProgress((prev) => ({
      ...prev!,
      jobId: event.job_id,
      progress: event.progress,
      status: event.status as TrainingJob['status'],
    }))
    updateJob(event.job_id, {
      progress: event.progress,
      status: event.status as TrainingJob['status'],
    })
  })

  // Listen for training complete events
  useWebSocket('training.complete', (data: unknown) => {
    const event = data as { job_id: string; job: TrainingJob }
    setProgress((prev) => ({
      ...prev!,
      status: 'completed',
    }))
    updateJob(event.job_id, event.job)
    setIsTraining(false)
    addNotification('success', `Training job "${event.job_id}" completed successfully!`)
  })

  // Listen for training error events
  useWebSocket('training.error', (data: unknown) => {
    const event = data as { job_id: string; error: string }
    setProgress((prev) => ({
      ...prev!,
      status: 'failed',
      error: event.error,
    }))
    updateJob(event.job_id, { status: 'failed' })
    setIsTraining(false)
    addNotification('error', `Training failed: ${event.error}`)
  })

  const startTraining = useCallback(
    async (request?: TrainingTriggerRequest): Promise<string> => {
      setIsTraining(true)
      setProgress({
        jobId: '',
        progress: 0,
        status: 'queued',
      })

      try {
        const response = await triggerTraining(request)
        setProgress((prev) => ({
          ...prev!,
          jobId: response.job_id,
        }))

        // Fetch full job details
        const job = await getTrainingJob(response.job_id)
        addJob(job)

        return response.job_id
      } catch (error) {
        setIsTraining(false)
        const errorMessage = error instanceof Error ? error.message : 'Training trigger failed'
        addNotification('error', errorMessage)
        throw error
      }
    },
    [addJob, addNotification]
  )

  const refreshJobs = useCallback(async () => {
    try {
      const jobs = await listTrainingJobs()
      const { setJobs } = useTrainingStore.getState()
      setJobs(jobs)
    } catch (error) {
      // Failed to refresh training jobs - handle silently
    }
  }, [])

  const clearProgress = useCallback(() => {
    setProgress(null)
    setIsTraining(false)
  }, [])

  return {
    isTraining,
    progress,
    startTraining,
    refreshJobs,
    clearProgress,
  }
}

