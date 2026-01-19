import { create } from 'zustand'

interface DiagramState {
  // Error state for diagram rendering
  error: string | null
  // Validation results from diagram parsing
  validation: {
    isValid: boolean
    errors: string[]
    warnings: string[]
  } | null
  // Track which content produced the last error (for preventing duplicate error reports)
  lastErrorContent: string | null
  // UI state
  isRepairing: boolean
  zoom: number

  // Actions
  setError: (error: string | null) => void
  setValidation: (validation: DiagramState['validation']) => void
  setLastErrorContent: (content: string | null) => void
  setIsRepairing: (isRepairing: boolean) => void
  setZoom: (zoom: number) => void
  zoomIn: () => void
  zoomOut: () => void
  resetZoom: () => void

  /**
   * Reset all transient diagram state.
   * Call this when:
   * - Navigating away from Studio
   * - Switching between diagrams
   * - Before loading a new diagram
   */
  resetState: () => void
}

const initialState = {
  error: null,
  validation: null,
  lastErrorContent: null,
  isRepairing: false,
  zoom: 1,
}

export const useDiagramStore = create<DiagramState>((set, get) => ({
  ...initialState,

  setError: (error) => set({ error }),

  setValidation: (validation) => set({ validation }),

  setLastErrorContent: (content) => set({ lastErrorContent: content }),

  setIsRepairing: (isRepairing) => set({ isRepairing }),

  setZoom: (zoom) => set({ zoom: Math.max(0.1, Math.min(5, zoom)) }),

  zoomIn: () => {
    const { zoom } = get()
    // Dynamic step: smaller steps at low zoom, larger at high zoom
    const step = zoom < 0.5 ? 0.05 : zoom < 1.5 ? 0.1 : 0.25
    set({ zoom: Math.min(zoom + step, 5) })
  },

  zoomOut: () => {
    const { zoom } = get()
    // Dynamic step: smaller steps at low zoom, larger at high zoom
    const step = zoom <= 0.5 ? 0.05 : zoom <= 1.5 ? 0.1 : 0.25
    set({ zoom: Math.max(zoom - step, 0.1) })
  },

  resetZoom: () => set({ zoom: 1 }),

  resetState: () => {
    set({
      error: null,
      validation: null,
      lastErrorContent: null,
      isRepairing: false,
      // Note: We intentionally don't reset zoom - it's a user preference
    })
  },
}))

