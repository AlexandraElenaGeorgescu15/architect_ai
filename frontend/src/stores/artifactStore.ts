import { create } from 'zustand'
import { Artifact } from '../types'
import { ArtifactType } from '../services/generationService'

interface ArtifactStore {
  artifacts: Artifact[]
  currentArtifact: Artifact | null
  isLoading: boolean
  error: string | null

  // Actions
  setArtifacts: (artifacts: Artifact[]) => void
  addArtifact: (artifact: Artifact) => void
  updateArtifact: (id: string, updates: Partial<Artifact>) => void
  removeArtifact: (id: string) => void
  setCurrentArtifact: (artifact: Artifact | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void

  // Selectors
  getArtifactsByType: (type: ArtifactType) => Artifact[]
  getArtifactById: (id: string) => Artifact | undefined
}

export const useArtifactStore = create<ArtifactStore>((set, get) => ({
  artifacts: [],
  currentArtifact: null,
  isLoading: false,
  error: null,

  setArtifacts: (artifacts) => set({ artifacts }),

  addArtifact: (artifact) =>
    set((state) => ({
      artifacts: [...state.artifacts, artifact],
    })),

  updateArtifact: (id, updates) =>
    set((state) => ({
      artifacts: state.artifacts.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      ),
      currentArtifact:
        state.currentArtifact?.id === id
          ? { ...state.currentArtifact, ...updates }
          : state.currentArtifact,
    })),

  removeArtifact: (id) =>
    set((state) => ({
      artifacts: state.artifacts.filter((a) => a.id !== id),
      currentArtifact:
        state.currentArtifact?.id === id ? null : state.currentArtifact,
    })),

  setCurrentArtifact: (artifact) => set({ currentArtifact: artifact }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  getArtifactsByType: (type) => {
    return get().artifacts.filter((a) => a.type === type)
  },

  getArtifactById: (id) => {
    return get().artifacts.find((a) => a.id === id)
  },
}))

