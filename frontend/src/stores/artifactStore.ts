import { create } from 'zustand'
import { Artifact } from '../types'
import { ArtifactType } from '../services/generationService'

interface ArtifactStore {
  artifacts: Artifact[]
  currentArtifact: Artifact | null
  currentFolderId: string | null  // Current meeting notes folder context
  isLoading: boolean
  error: string | null

  // Actions
  setArtifacts: (artifacts: Artifact[]) => void
  addArtifact: (artifact: Artifact) => void
  updateArtifact: (id: string, updates: Partial<Artifact>) => void
  removeArtifact: (id: string) => void
  setCurrentArtifact: (artifact: Artifact | null) => void
  setCurrentFolderId: (folderId: string | null) => void  // Set current folder context
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void

  // Selectors
  getArtifactsByType: (type: ArtifactType) => Artifact[]
  getArtifactById: (id: string) => Artifact | undefined
  getArtifactsByFolder: (folderId: string | null) => Artifact[]  // Filter by folder

  // Reset
  reset: () => void
}

export const useArtifactStore = create<ArtifactStore>((set, get) => ({
  artifacts: [],
  currentArtifact: null,
  currentFolderId: null,
  isLoading: false,
  error: null,

  setArtifacts: (artifacts) => set({ artifacts }),

  // FIX: Replace existing artifact with same ID instead of creating duplicates
  // This ensures stable ID scheme works correctly (artifact_type as ID)
  addArtifact: (artifact) =>
    set((state) => {
      const existingIndex = state.artifacts.findIndex(a => a.id === artifact.id)
      if (existingIndex >= 0) {
        // Replace existing artifact (update in place)
        const newArtifacts = [...state.artifacts]
        newArtifacts[existingIndex] = artifact
        console.log(`📦 [ARTIFACT_STORE] Updated existing artifact: ${artifact.id}`)
        return { artifacts: newArtifacts }
      }
      // Add new artifact
      console.log(`📦 [ARTIFACT_STORE] Added new artifact: ${artifact.id}`)
      return { artifacts: [...state.artifacts, artifact] }
    }),

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
  
  setCurrentFolderId: (folderId) => set({ currentFolderId: folderId }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  getArtifactsByType: (type) => {
    return get()
      .artifacts
      .filter((a) => a.type === type)
      .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
  },

  getArtifactById: (id) => {
    return get().artifacts.find((a) => a.id === id)
  },

  // Filter artifacts by folder ID
  getArtifactsByFolder: (folderId) => {
    const artifacts = get().artifacts
    if (!folderId) {
      // If no folder specified, return all artifacts
      return artifacts.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
    }
    return artifacts
      .filter((a) => (a as any).folder_id === folderId)
      .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
  },

  // Reset store to initial state (call on cleanup/logout)
  reset: () => set({
    artifacts: [],
    currentArtifact: null,
    currentFolderId: null,
    isLoading: false,
    error: null,
  }),
}))

