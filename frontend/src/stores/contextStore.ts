import { create } from 'zustand'
import { Context } from '../types'

interface ContextStore {
  contexts: Context[]
  currentContext: Context | null
  isLoading: boolean
  error: string | null

  // Actions
  setContexts: (contexts: Context[]) => void
  addContext: (context: Context) => void
  updateContext: (id: string, updates: Partial<Context>) => void
  removeContext: (id: string) => void
  setCurrentContext: (context: Context | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void

  // Selectors
  getContextById: (id: string) => Context | undefined
}

export const useContextStore = create<ContextStore>((set, get) => ({
  contexts: [],
  currentContext: null,
  isLoading: false,
  error: null,

  setContexts: (contexts) => set({ contexts }),

  addContext: (context) =>
    set((state) => ({
      contexts: [...state.contexts, context],
    })),

  updateContext: (id, updates) =>
    set((state) => ({
      contexts: state.contexts.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
      currentContext:
        state.currentContext?.id === id
          ? { ...state.currentContext, ...updates }
          : state.currentContext,
    })),

  removeContext: (id) =>
    set((state) => ({
      contexts: state.contexts.filter((c) => c.id !== id),
      currentContext: state.currentContext?.id === id ? null : state.currentContext,
    })),

  setCurrentContext: (context) => set({ currentContext: context }),

  setLoading: (loading) => set({ isLoading: loading }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  getContextById: (id) => {
    return get().contexts.find((c) => c.id === id)
  },
}))

