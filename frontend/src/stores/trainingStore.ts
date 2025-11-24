import { create } from 'zustand'
import { TrainingJob } from '../types'
import { TrainingStatus } from '../services/trainingService'

interface TrainingStore {
  jobs: TrainingJob[]
  currentJob: TrainingJob | null
  isLoading: boolean
  error: string | null

  // Actions
  setJobs: (jobs: TrainingJob[]) => void
  addJob: (job: TrainingJob) => void
  updateJob: (id: string, updates: Partial<TrainingJob>) => void
  removeJob: (id: string) => void
  setCurrentJob: (job: TrainingJob | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void

  // Selectors
  getJobsByStatus: (status: TrainingStatus) => TrainingJob[]
  getJobById: (id: string) => TrainingJob | undefined
  getActiveJobs: () => TrainingJob[]
}

export const useTrainingStore = create<TrainingStore>((set, get) => ({
  jobs: [],
  currentJob: null,
  isLoading: false,
  error: null,

  setJobs: (jobs) => set({ jobs }),

  addJob: (job) =>
    set((state) => ({
      jobs: [...state.jobs, job],
    })),

  updateJob: (id, updates) =>
    set((state) => ({
      jobs: state.jobs.map((j) =>
        j.id === id ? { ...j, ...updates } : j
      ),
      currentJob:
        state.currentJob?.id === id
          ? { ...state.currentJob, ...updates }
          : state.currentJob,
    })),

  removeJob: (id) =>
    set((state) => ({
      jobs: state.jobs.filter((j) => j.id !== id),
      currentJob: state.currentJob?.id === id ? null : state.currentJob,
    })),

  setCurrentJob: (job) => set({ currentJob: job }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  getJobsByStatus: (status) => {
    return get().jobs.filter((j) => j.status === status)
  },

  getJobById: (id) => {
    return get().jobs.find((j) => j.id === id)
  },

  getActiveJobs: () => {
    return get().jobs.filter(
      (j) =>
        j.status === 'queued' ||
        j.status === 'preparing' ||
        j.status === 'training' ||
        j.status === 'converting'
    )
  },
}))

