import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, Menu, X, Sparkles, Trash2, ChevronRight, ChevronLeft, Loader2, Layers } from 'lucide-react'
import { useUIStore } from '../../stores/uiStore'
import { useState, useRef, useEffect } from 'react'
import { Template, listTemplates, applyTemplate } from '../../services/templateService'
import ProjectIndicator from './ProjectIndicator'

export default function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { toggleSidebar, sidebarOpen, notifications, removeNotification, clearNotifications, addNotification } = useUIStore()
  const [showPanel, setShowPanel] = useState(false)
  const [activeTab, setActiveTab] = useState<'notifications' | 'templates'>('notifications')
  const panelRef = useRef<HTMLDivElement>(null)
  
  // Templates state
  const [templates, setTemplates] = useState<Template[]>([])
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [isApplying, setIsApplying] = useState<string | null>(null)
  
  // Click outside handler
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setShowPanel(false)
      }
    }

    if (showPanel) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showPanel])

  // Load templates when tab switches to templates
  useEffect(() => {
    if (showPanel && activeTab === 'templates' && templates.length === 0) {
      loadTemplates()
    }
  }, [showPanel, activeTab])

  const loadTemplates = async () => {
    setIsLoadingTemplates(true)
    try {
      const loaded = await listTemplates()
      setTemplates(loaded)
    } catch (error) {
      console.error('Failed to load templates:', error)
      addNotification('error', 'Failed to load templates')
    } finally {
      setIsLoadingTemplates(false)
    }
  }

  const handleApplyTemplate = async (templateId: string) => {
    setIsApplying(templateId)
    try {
      const response = await applyTemplate(templateId)
      addNotification('success', `Template "${response.template.name}" applied!`)
      setShowPanel(false)
      navigate('/studio', { state: { appliedTemplate: response } })
    } catch (error) {
      console.error('Failed to apply template:', error)
      addNotification('error', 'Failed to apply template')
    } finally {
      setIsApplying(null)
    }
  }

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/studio': return 'Studio'
      case '/intelligence': return 'Intelligence'
      case '/canvas': return 'Canvas'
      default: return 'Architect.AI'
    }
  }

  return (
    <header className="h-12 px-4 flex items-center justify-between flex-shrink-0 z-40 border-b border-border bg-card/50 backdrop-blur-sm">
      {/* Left: Title */}
      <div className="flex items-center gap-2">
        <button 
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg hover:bg-primary/10 text-muted-foreground hover:text-primary transition-all lg:hidden"
          aria-label="Toggle sidebar"
          title={sidebarOpen ? 'Close menu' : 'Open menu'}
        >
          {sidebarOpen ? (
            <ChevronLeft className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
        <h1 className="text-base font-bold text-foreground">{getPageTitle()}</h1>
      </div>

      {/* Center: Project Indicator - Shows all indexed projects */}
      <div className="hidden md:block mx-4">
        <ProjectIndicator />
      </div>

      <div className="flex-1" />

      {/* Right: Actions */}
      <div className="relative" ref={panelRef}>
        <div className="flex items-center gap-1">
          <button
            onClick={() => { setActiveTab('templates'); setShowPanel(!showPanel) }}
            className={`p-2 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all ${
              showPanel && activeTab === 'templates' ? 'bg-primary/10 text-primary' : ''
            }`}
            title="Templates"
          >
            <Sparkles className="w-4 h-4" />
          </button>
          <button 
            onClick={() => { setActiveTab('notifications'); setShowPanel(!showPanel) }}
            className={`relative p-2 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all ${
              showPanel && activeTab === 'notifications' ? 'bg-primary/10 text-primary' : ''
            }`}
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            {notifications.length > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </button>
        </div>
        
        {/* Dropdown Panel - Fixed positioning to escape parent overflow */
        showPanel && (
          <>
            {/* Backdrop for mobile/click-outside */}
            <div 
              className="fixed inset-0 z-[90] bg-transparent"
              onClick={() => setShowPanel(false)}
            />
            <div className="fixed right-4 top-14 w-[calc(100vw-2rem)] md:w-80 max-h-[80vh] flex flex-col rounded-xl shadow-2xl border border-border/50 bg-card/95 backdrop-blur-xl z-[100] overflow-hidden animate-in slide-in-from-top-2 duration-200">
              {/* Tabs */}
              <div className="flex border-b border-border/50 text-xs bg-muted/30">
                <button
                  onClick={() => setActiveTab('notifications')}
                  className={`flex-1 px-3 py-3 font-medium flex items-center justify-center gap-2 transition-colors ${
                    activeTab === 'notifications'
                      ? 'text-primary bg-background shadow-sm border-t-2 border-t-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Bell className="w-3.5 h-3.5" />
                  Notifications
                  {notifications.length > 0 && (
                    <span className="px-1.5 py-0.5 text-[10px] bg-red-500 text-white rounded-full shadow-sm">
                      {notifications.length}
                    </span>
                  )}
                </button>
                <button
                  onClick={() => setActiveTab('templates')}
                  className={`flex-1 px-3 py-3 font-medium flex items-center justify-center gap-2 transition-colors ${
                    activeTab === 'templates'
                      ? 'text-primary bg-background shadow-sm border-t-2 border-t-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Templates
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                {activeTab === 'notifications' ? (
                <div className="p-2">
                  {notifications.length > 0 && (
                    <div className="flex justify-end mb-2">
                      <button
                        onClick={clearNotifications}
                        className="text-[10px] text-muted-foreground hover:text-destructive flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-destructive/10"
                      >
                        <Trash2 className="w-3 h-3" />
                        Clear all
                      </button>
                    </div>
                  )}
                  {notifications.length === 0 ? (
                    <div className="py-6 text-center">
                      <Bell className="w-8 h-8 mx-auto mb-2 text-muted-foreground/40" />
                      <p className="text-xs text-muted-foreground">No notifications</p>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {notifications.slice(0, 8).map((n) => (
                        <div 
                          key={n.id}
                          className={`p-2 rounded-md border text-xs flex items-start gap-2 ${
                            n.type === 'success' ? 'bg-green-500/10 border-green-500/30' :
                            n.type === 'error' ? 'bg-red-500/10 border-red-500/30' :
                            n.type === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30' :
                            'bg-primary/10 border-primary/30'
                          }`}
                        >
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-foreground line-clamp-2">{n.message}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              {new Date(n.timestamp).toLocaleTimeString()}
                            </p>
                          </div>
                          <button
                            onClick={() => removeNotification(n.id)}
                            className="p-1 hover:bg-black/10 rounded flex-shrink-0"
                          >
                            <X className="w-3 h-3 text-muted-foreground" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-2">
                  {isLoadingTemplates ? (
                    <div className="py-6 text-center">
                      <Loader2 className="w-6 h-6 mx-auto mb-2 text-primary animate-spin" />
                      <p className="text-xs text-muted-foreground">Loading...</p>
                    </div>
                  ) : templates.length === 0 ? (
                    <div className="py-6 text-center">
                      <Sparkles className="w-8 h-8 mx-auto mb-2 text-muted-foreground/40" />
                      <p className="text-xs text-muted-foreground">No templates</p>
                      <button onClick={loadTemplates} className="text-[10px] text-primary hover:underline mt-1">
                        Retry
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {templates.map((t) => (
                        <button
                          key={t.id}
                          onClick={() => handleApplyTemplate(t.id)}
                          disabled={isApplying === t.id}
                          className="w-full text-left p-2 rounded-md border border-border hover:border-primary/50 hover:bg-primary/5 transition-all group disabled:opacity-50"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="font-medium text-xs text-foreground group-hover:text-primary truncate">
                                  {t.name}
                                </span>
                                <span className={`px-1 py-0.5 text-[9px] font-bold rounded ${
                                  t.complexity === 'high' ? 'bg-red-500/10 text-red-500' :
                                  t.complexity === 'medium' ? 'bg-yellow-500/10 text-yellow-600' :
                                  'bg-green-500/10 text-green-600'
                                }`}>
                                  {t.complexity.toUpperCase()}
                                </span>
                              </div>
                              <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">{t.description}</p>
                              <div className="flex items-center gap-1.5 mt-1 text-[10px] text-muted-foreground">
                                <Layers className="w-3 h-3" />
                                <span>{t.recommended_artifacts.length} artifacts</span>
                              </div>
                            </div>
                            {isApplying === t.id ? (
                              <Loader2 className="w-3.5 h-3.5 text-primary animate-spin flex-shrink-0" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary flex-shrink-0" />
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
          </>
        )}
      </div>
    </header>
  )
}
