/**
 * Toast Notifications Component
 * Shows notifications as toast popups that auto-dismiss
 */

import { useEffect, useState } from 'react'
import { useUIStore } from '../stores/uiStore'
import { X, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react'

export default function ToastNotifications() {
  const { notifications, removeNotification } = useUIStore()
  const [visibleToasts, setVisibleToasts] = useState<string[]>([])

  // Track which notifications should be shown as toasts
  useEffect(() => {
    // Show new notifications as toasts
    const newToasts = notifications
      .filter(n => Date.now() - n.timestamp < 100) // Only show notifications added in last 100ms
      .map(n => n.id)
    
    if (newToasts.length > 0) {
      setVisibleToasts(prev => [...prev, ...newToasts].slice(-5)) // Keep last 5
    }
  }, [notifications])

  // Auto-dismiss toasts after 5 seconds
  useEffect(() => {
    if (visibleToasts.length === 0) return

    const timer = setTimeout(() => {
      setVisibleToasts(prev => prev.slice(1))
    }, 5000)

    return () => clearTimeout(timer)
  }, [visibleToasts])

  const dismissToast = (id: string) => {
    setVisibleToasts(prev => prev.filter(t => t !== id))
    removeNotification(id)
  }

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getStyles = (type: string) => {
    switch (type) {
      case 'success':
        return 'bg-green-500/10 border-green-500/50 text-green-700 dark:text-green-300'
      case 'error':
        return 'bg-red-500/10 border-red-500/50 text-red-700 dark:text-red-300'
      case 'warning':
        return 'bg-yellow-500/10 border-yellow-500/50 text-yellow-700 dark:text-yellow-300'
      default:
        return 'bg-blue-500/10 border-blue-500/50 text-blue-700 dark:text-blue-300'
    }
  }

  if (visibleToasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      {visibleToasts.map((toastId, index) => {
        const notification = notifications.find(n => n.id === toastId)
        if (!notification) return null

        return (
          <div
            key={notification.id}
            className={`
              pointer-events-auto
              flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-sm
              animate-in slide-in-from-right-5 fade-in duration-300
              max-w-sm
              ${getStyles(notification.type)}
            `}
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <div className="flex-shrink-0 mt-0.5">
              {getIcon(notification.type)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{notification.message}</p>
            </div>
            <button
              onClick={() => dismissToast(notification.id)}
              className="flex-shrink-0 p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
            >
              <X className="w-4 h-4 opacity-60 hover:opacity-100" />
            </button>
          </div>
        )
      })}
    </div>
  )
}

