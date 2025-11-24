import { create } from 'zustand'

interface UIStore {
  darkMode: boolean
  sidebarOpen: boolean
  notifications: Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
    timestamp: number
  }>

  // Actions
  toggleDarkMode: () => void
  setDarkMode: (enabled: boolean) => void
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  addNotification: (
    type: 'success' | 'error' | 'warning' | 'info',
    message: string
  ) => void
  removeNotification: (id: string) => void
  clearNotifications: () => void
}

export const useUIStore = create<UIStore>((set, get) => ({
  darkMode: localStorage.getItem('darkMode') === 'true',
  sidebarOpen: true,
  notifications: [],

  toggleDarkMode: () => {
    const newValue = !get().darkMode
    set({ darkMode: newValue })
    localStorage.setItem('darkMode', String(newValue))
    document.documentElement.classList.toggle('dark', newValue)
  },

  setDarkMode: (enabled) => {
    set({ darkMode: enabled })
    localStorage.setItem('darkMode', String(enabled))
    document.documentElement.classList.toggle('dark', enabled)
  },

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  addNotification: (type, message) => {
    const id = `${Date.now()}-${Math.random()}`
    set((state) => ({
      notifications: [
        ...state.notifications,
        {
          id,
          type,
          message,
          timestamp: Date.now(),
        },
      ],
    }))

    // Auto-remove after 5 seconds
    setTimeout(() => {
      get().removeNotification(id)
    }, 5000)
  },

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () => set({ notifications: [] }),
}))

