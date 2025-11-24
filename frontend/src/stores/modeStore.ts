import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type AppMode = 'dev' | 'pm'

interface ModeStore {
  mode: AppMode
  setMode: (mode: AppMode) => void
}

export const useModeStore = create<ModeStore>()(
  persist(
    (set) => ({
      mode: 'dev',
      setMode: (mode) => set({ mode }),
    }),
    {
      name: 'architect-ai-mode',
    }
  )
)

