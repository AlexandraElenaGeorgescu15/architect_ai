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
  sidebarOpen: localStorage.getItem('sidebarOpen') !== 'false', // Default to open
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

  toggleSidebar: () => {
    const newValue = !get().sidebarOpen
    set({ sidebarOpen: newValue })
    localStorage.setItem('sidebarOpen', String(newValue))
  },

  setSidebarOpen: (open) => {
    set({ sidebarOpen: open })
    localStorage.setItem('sidebarOpen', String(open))
  },

  addNotification: (type, message) => {
    const id = `${Date.now()}-${Math.random()}`
    set((state) => ({
      notifications: [
        {
          id,
          type,
          message,
          timestamp: Date.now(),
        },
        ...state.notifications, 
      ],
    }))
  },

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () => set({ notifications: [] }),
}))

