import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, X, Sparkles, Trash2, ChevronRight, ChevronLeft, Loader2, Layers, Lightbulb, GitBranch, FileText, Zap, AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import { useUIStore } from '../../stores/uiStore'
import { useState, useRef, useEffect, useCallback } from 'react'
import { Template, listTemplates, applyTemplate } from '../../services/templateService'
import ProjectIndicator from './ProjectIndicator'
import FolderSelector from '../FolderSelector'
import api from '../../services/api'

// Assistant types
interface Suggestion {
  artifact_type: string
  reason: string
  priority: 'high' | 'medium' | 'low'
  context: string
}

interface StalenessReport {
  artifact_id: string
  artifact_type: string
  is_stale: boolean
  reason: string
  recommendation: string
}

interface ParsedMeetingNotes {
  feature_name: string
  feature_description: string
  entities: Array<{ name: string; fields: Array<{ name: string; type: string }>; confidence: number }>
  endpoints: Array<{ method: string; path: string; description: string; confidence: number }>
  ui_components: Array<{ component_type: string; description: string; fields: string[] }>
  suggestions: string[]
  parsing_confidence: number
}

export default function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { toggleSidebar, sidebarOpen, notifications, removeNotification, clearNotifications, addNotification } = useUIStore()
  const [showPanel, setShowPanel] = useState(false)
  const [activeTab, setActiveTab] = useState<'notifications' | 'templates' | 'assistant'>('notifications')
  const panelRef = useRef<HTMLDivElement>(null)
  
  // Templates state
  const [templates, setTemplates] = useState<Template[]>([])
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(false)
  const [isApplying, setIsApplying] = useState<string | null>(null)
  
  // Assistant state
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [stalenessReports, setStalenessReports] = useState<StalenessReport[]>([])
  const [parsedNotes, setParsedNotes] = useState<ParsedMeetingNotes | null>(null)
  const [notesToParse, setNotesToParse] = useState('')
  const [assistantLoading, setAssistantLoading] = useState(false)
  const [assistantSubTab, setAssistantSubTab] = useState<'suggestions' | 'health' | 'parser'>('suggestions')
  
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

  // Assistant functions
  const getSuggestions = useCallback(async () => {
    setAssistantLoading(true)
    try {
      const response = await api.post('/api/assistant/suggestions', {
        existing_artifact_types: [],
        max_suggestions: 5
      })
      setSuggestions(response.data.suggestions || [])
    } catch (err: any) {
      addNotification('error', 'Failed to get suggestions')
    } finally {
      setAssistantLoading(false)
    }
  }, [addNotification])

  const checkStaleness = useCallback(async () => {
    setAssistantLoading(true)
    try {
      const response = await api.get('/api/assistant/artifacts/stale')
      setStalenessReports(response.data.stale_artifacts || [])
    } catch (err: any) {
      addNotification('error', 'Failed to check staleness')
    } finally {
      setAssistantLoading(false)
    }
  }, [addNotification])

  const parseMeetingNotes = useCallback(async () => {
    if (!notesToParse.trim()) return
    setAssistantLoading(true)
    try {
      const response = await api.post('/api/assistant/meeting-notes/parse', {
        meeting_notes: notesToParse
      })
      setParsedNotes(response.data)
    } catch (err: any) {
      addNotification('error', 'Failed to parse meeting notes')
    } finally {
      setAssistantLoading(false)
    }
  }, [notesToParse, addNotification])

  const priorityColors: Record<string, string> = {
    high: 'text-red-400 bg-red-500/10 border-red-500/30',
    medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
    low: 'text-green-400 bg-green-500/10 border-green-500/30'
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

      {/* Center: Project Indicator + Folder Selector */}
      <div className="hidden md:flex items-center gap-3 mx-4">
        <ProjectIndicator />
        <div className="h-4 w-px bg-border" />
        <FolderSelector />
      </div>

      <div className="flex-1" />

      {/* Right: Actions */}
      <div className="relative" ref={panelRef}>
        <div className="flex items-center gap-1">
          <button
            onClick={() => { setActiveTab('assistant'); setShowPanel(!showPanel) }}
            className={`p-2 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/10 transition-all ${
              showPanel && activeTab === 'assistant' ? 'bg-primary/10 text-primary' : ''
            }`}
            title="Smart Assistant"
          >
            <Lightbulb className="w-4 h-4" />
          </button>
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
                  onClick={() => setActiveTab('assistant')}
                  className={`flex-1 px-2 py-3 font-medium flex items-center justify-center gap-1.5 transition-colors ${
                    activeTab === 'assistant'
                      ? 'text-primary bg-background shadow-sm border-t-2 border-t-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Lightbulb className="w-3.5 h-3.5" />
                  Assistant
                </button>
                <button
                  onClick={() => setActiveTab('templates')}
                  className={`flex-1 px-2 py-3 font-medium flex items-center justify-center gap-1.5 transition-colors ${
                    activeTab === 'templates'
                      ? 'text-primary bg-background shadow-sm border-t-2 border-t-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Templates
                </button>
                <button
                  onClick={() => setActiveTab('notifications')}
                  className={`flex-1 px-2 py-3 font-medium flex items-center justify-center gap-1.5 transition-colors ${
                    activeTab === 'notifications'
                      ? 'text-primary bg-background shadow-sm border-t-2 border-t-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  <Bell className="w-3.5 h-3.5" />
                  {notifications.length > 0 && (
                    <span className="px-1 py-0.5 text-[9px] bg-red-500 text-white rounded-full">
                      {notifications.length}
                    </span>
                  )}
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-1">
                {activeTab === 'assistant' ? (
                <div className="p-2 space-y-3">
                  {/* Assistant Sub-tabs */}
                  <div className="flex gap-1 text-[10px]">
                    {[
                      { id: 'suggestions' as const, label: 'Suggestions', icon: Zap },
                      { id: 'health' as const, label: 'Health', icon: GitBranch },
                      { id: 'parser' as const, label: 'Parser', icon: FileText }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setAssistantSubTab(tab.id)}
                        className={`flex items-center gap-1 px-2 py-1.5 rounded-md transition-all ${
                          assistantSubTab === tab.id
                            ? 'bg-primary/10 text-primary border border-primary/30'
                            : 'text-muted-foreground hover:bg-muted/50'
                        }`}
                      >
                        <tab.icon className="w-3 h-3" />
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Suggestions Sub-tab */}
                  {assistantSubTab === 'suggestions' && (
                    <div className="space-y-2">
                      <button
                        onClick={getSuggestions}
                        disabled={assistantLoading}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-medium transition-all"
                      >
                        {assistantLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Lightbulb className="w-3 h-3" />}
                        Get Smart Suggestions
                      </button>
                      {suggestions.length === 0 ? (
                        <p className="text-[10px] text-muted-foreground text-center py-3">
                          Click above to get AI-powered artifact suggestions
                        </p>
                      ) : (
                        <div className="space-y-1.5">
                          {suggestions.map((s, idx) => (
                            <div key={idx} className="p-2 bg-muted/30 rounded-lg border border-border text-xs">
                              <div className="flex items-center justify-between gap-2 mb-1">
                                <span className="font-medium text-foreground">
                                  {s.artifact_type.replace('mermaid_', '').replace('_', ' ')}
                                </span>
                                <span className={`px-1.5 py-0.5 text-[9px] rounded border ${priorityColors[s.priority]}`}>
                                  {s.priority}
                                </span>
                              </div>
                              <p className="text-muted-foreground text-[10px] line-clamp-2">{s.reason}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Health Sub-tab */}
                  {assistantSubTab === 'health' && (
                    <div className="space-y-2">
                      <button
                        onClick={checkStaleness}
                        disabled={assistantLoading}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-medium transition-all"
                      >
                        {assistantLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                        Check Artifact Health
                      </button>
                      {stalenessReports.length === 0 ? (
                        <div className="py-4 text-center">
                          <CheckCircle2 className="w-6 h-6 text-green-500 mx-auto mb-1" />
                          <p className="text-[10px] text-muted-foreground">All artifacts up to date!</p>
                        </div>
                      ) : (
                        <div className="space-y-1.5">
                          {stalenessReports.map((r, idx) => (
                            <div key={idx} className="p-2 bg-yellow-500/10 rounded-lg border border-yellow-500/30 text-xs">
                              <div className="flex items-start gap-2">
                                <AlertTriangle className="w-3 h-3 text-yellow-500 mt-0.5 flex-shrink-0" />
                                <div>
                                  <p className="font-medium text-foreground">{r.artifact_type}</p>
                                  <p className="text-[10px] text-muted-foreground">{r.reason}</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Parser Sub-tab */}
                  {assistantSubTab === 'parser' && (
                    <div className="space-y-2">
                      <textarea
                        placeholder="Paste meeting notes to extract entities, endpoints, and UI components..."
                        value={notesToParse}
                        onChange={e => setNotesToParse(e.target.value)}
                        className="w-full h-20 bg-background border border-border rounded-lg px-2 py-1.5 text-xs resize-none focus:outline-none focus:border-primary/50"
                      />
                      <button
                        onClick={parseMeetingNotes}
                        disabled={assistantLoading || !notesToParse.trim()}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-xs font-medium transition-all disabled:opacity-50"
                      >
                        {assistantLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <FileText className="w-3 h-3" />}
                        Parse Notes
                      </button>
                      {parsedNotes && (
                        <div className="space-y-1.5 text-xs">
                          <div className="p-2 bg-primary/5 rounded-lg border border-primary/20">
                            <p className="font-medium text-primary">{parsedNotes.feature_name}</p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">{parsedNotes.feature_description}</p>
                          </div>
                          {parsedNotes.entities.length > 0 && (
                            <div className="p-2 bg-green-500/5 rounded-lg border border-green-500/20">
                              <p className="font-medium text-green-500 mb-1">📊 {parsedNotes.entities.length} Entities</p>
                              <div className="flex flex-wrap gap-1">
                                {parsedNotes.entities.map((e, i) => (
                                  <span key={i} className="px-1.5 py-0.5 bg-green-500/10 text-green-600 rounded text-[10px]">{e.name}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {parsedNotes.endpoints.length > 0 && (
                            <div className="p-2 bg-blue-500/5 rounded-lg border border-blue-500/20">
                              <p className="font-medium text-blue-500 mb-1">🔌 {parsedNotes.endpoints.length} Endpoints</p>
                              <div className="space-y-0.5">
                                {parsedNotes.endpoints.slice(0, 3).map((ep, i) => (
                                  <p key={i} className="text-[10px] font-mono text-muted-foreground">
                                    <span className="text-blue-400">{ep.method}</span> {ep.path}
                                  </p>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : activeTab === 'notifications' ? (
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
