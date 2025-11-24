import { create } from 'zustand'
import { Model } from '../types'
import { RoutingConfig } from '../services/modelService'

interface ModelStore {
  models: Model[]
  routing: RoutingConfig | null
  isLoading: boolean
  error: string | null

  // Actions
  setModels: (models: Model[]) => void
  addModel: (model: Model) => void
  updateModel: (id: string, updates: Partial<Model>) => void
  setRouting: (routing: RoutingConfig) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void

  // Async actions
  fetchModels: () => Promise<void>

  // Selectors
  getModelById: (id: string) => Model | undefined
  getModelsByProvider: (provider: string) => Model[]
  getModelsByStatus: (status: string) => Model[]
}

export const useModelStore = create<ModelStore>((set, get) => ({
  models: [],
  routing: null,
  isLoading: false,
  error: null,

  setModels: (models) => set({ models }),

  addModel: (model) =>
    set((state) => ({
      models: [...state.models, model],
    })),

  updateModel: (id, updates) =>
    set((state) => ({
      models: state.models.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),

  setRouting: (routing) => set({ routing }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  getModelById: (id) => {
    return get().models.find((m) => m.id === id)
  },

  getModelsByProvider: (provider) => {
    return get().models.filter((m) => m.provider === provider)
  },

  getModelsByStatus: (status) => {
    return get().models.filter((m) => m.status === status)
  },

  fetchModels: async () => {
    try {
      set({ isLoading: true, error: null })
      const { api } = await import('../services/api')
      const response = await api.get('/api/models/')
      set({ models: response.data, isLoading: false })
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch models', isLoading: false })
    }
  },
}))

