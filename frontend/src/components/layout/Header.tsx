import { useLocation } from 'react-router-dom'
import { Bell, Menu, X } from 'lucide-react'
import { useUIStore } from '../../stores/uiStore'
import { useState } from 'react'

export default function Header() {
  const location = useLocation()
  const { toggleSidebar, notifications } = useUIStore()
  const [showNotifications, setShowNotifications] = useState(false)

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/studio': return 'Studio'
      case '/intelligence': return 'Intelligence Center'
      case '/canvas': return 'Canvas'
      default: return 'Architect.AI'
    }
  }

  return (
    <header 
      className="h-20 px-8 flex items-center justify-between flex-shrink-0 z-40 border-b border-border backdrop-blur-md bg-card"
    >
      {/* Left: Page Title & Breadcrumbs */}
      <div className="flex items-center gap-4">
        <button 
          onClick={toggleSidebar}
          className="p-2.5 rounded-xl hover:bg-primary/10 text-muted-foreground hover:text-primary transition-all duration-300 lg:hidden shadow-sm hover:shadow-md"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-6 h-6" />
        </button>
        
        <div className="flex flex-col animate-fade-in-left">
          <h1 className="text-2xl font-black tracking-tight text-foreground flex items-center gap-2">
            {getPageTitle()}
          </h1>
          <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
            <span className="opacity-50">ARCHITECT.AI</span>
            <span className="opacity-30">/</span>
            <span className="text-primary uppercase tracking-wider font-bold">{location.pathname.substring(1)}</span>
          </div>
        </div>
      </div>

      {/* Center: Spacer */}
      <div className="flex-1"></div>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-3 relative">
        {/* Notifications */}
        <div className="relative">
          <button 
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2.5 rounded-xl glass-button text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all duration-300 group shadow-sm hover:shadow-md"
            aria-label="Notifications"
          >
            <Bell className="w-5 h-5 group-hover:scale-110 transition-transform duration-300" />
            {notifications.length > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-accent rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
            )}
          </button>
          
          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 glass-panel rounded-xl shadow-floating border border-border/50 p-4 z-50 animate-scale-in bg-card max-h-96 overflow-y-auto custom-scrollbar">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-foreground">Notifications</h3>
                <button onClick={() => setShowNotifications(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-3">
                {notifications.length === 0 ? (
                  <div className="p-3 rounded-lg bg-background/50">
                    <p className="text-sm text-muted-foreground text-center">No notifications</p>
                  </div>
                ) : (
                  notifications.slice(0, 10).map((notification, index) => (
                    <div 
                      key={index}
                      className={`p-3 rounded-lg border ${
                        notification.type === 'success' 
                          ? 'bg-green-500/10 border-green-500/30' 
                          : notification.type === 'error'
                          ? 'bg-red-500/10 border-red-500/30'
                          : notification.type === 'warning'
                          ? 'bg-yellow-500/10 border-yellow-500/30'
                          : 'bg-primary/10 border-primary/30'
                      }`}
                    >
                      <p className="text-sm font-medium text-foreground">{notification.message}</p>
                      {notification.timestamp && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(notification.timestamp).toLocaleTimeString()}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
