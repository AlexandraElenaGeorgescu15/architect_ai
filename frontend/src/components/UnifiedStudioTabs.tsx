import { useState, useEffect, useCallback, useMemo, useRef, lazy, Suspense, memo } from 'react'
import { ArtifactType } from '../services/generationService'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { 
  Loader2, Sparkles, FileText, CheckCircle2, Folder, Code, FileCode, 
  Download, Key, Settings, Search, Network, ListTodo, Sliders, Edit3, GitBranch
} from 'lucide-react'
import MeetingNotesManager from './MeetingNotesManager'
import BulkGenerationDialog from './BulkGenerationDialog'
import { bulkGenerate } from '../services/generationService'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { useKeyboardShortcuts, COMMON_SHORTCUTS } from '../hooks/useKeyboardShortcuts'

// Lazy load heavy components for better initial load performance
const ArtifactTabs = lazy(() => import('./artifacts/ArtifactTabs'))
const CodeEditor = lazy(() => import('./CodeEditor'))
const ExportManager = lazy(() => import('./ExportManager'))
const SemanticSearchPanel = lazy(() => import('./SemanticSearchPanel'))
const ApiKeysManager = lazy(() => import('./ApiKeysManager'))
const InteractivePrototypeEditor = lazy(() => import('./InteractivePrototypeEditor'))
const CodeWithTestsEditor = lazy(() => import('./CodeWithTestsEditor'))
const MermaidRenderer = lazy(() => import('./MermaidRenderer'))
const VersionControl = lazy(() => import('./VersionControl'))

// Loading fallback component
const LoadingFallback = memo(function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-full min-h-[200px]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="text-sm text-muted-foreground">Loading...</span>
      </div>
    </div>
  )
})

// Library View with Search
const LibraryView = memo(function LibraryView() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const { artifacts } = useArtifactStore()
  
  // Focus search input when opened
  useEffect(() => {
    if (showSearch && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [showSearch])
  
  // Close search on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showSearch) {
        setShowSearch(false)
        setSearchQuery('')
      }
      // Ctrl/Cmd + F to open search
      if ((e.ctrlKey || e.metaKey) && e.key === 'f' && !showSearch) {
        e.preventDefault()
        setShowSearch(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showSearch])
  
  return (
    <div className="h-full overflow-auto custom-scrollbar p-4 animate-fade-in-up">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center glass-panel p-6 rounded-2xl border-border bg-card shadow-elevated hover:shadow-floating transition-all duration-300">
          <div>
            <h2 className="text-3xl font-black text-foreground tracking-tight flex items-center gap-3">
              <span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">Artifact Library</span>
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {artifacts.length} artifact{artifacts.length !== 1 ? 's' : ''} • Browse and manage your generated artifacts
            </p>
          </div>
          <div className="flex gap-3">
            {showSearch ? (
              <div className="flex items-center gap-2">
                <input
                  ref={searchInputRef}
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search artifacts..."
                  className="px-4 py-2 border border-border rounded-xl bg-background text-foreground text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                />
                <button 
                  onClick={() => {
                    setShowSearch(false)
                    setSearchQuery('')
                  }}
                  className="p-2 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded-lg transition-colors"
                  title="Close search"
                >
                  ✕
                </button>
              </div>
            ) : (
              <button 
                onClick={() => setShowSearch(true)}
                className="px-6 py-3 border border-border rounded-xl hover:bg-primary/10 hover:border-primary/30 flex items-center gap-2 text-sm glass-button transition-all duration-300 shadow-sm hover:shadow-md font-bold group"
              >
                <Search className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" /> Search
              </button>
            )}
          </div>
        </div>
        <div className="glass-panel rounded-2xl p-8 min-h-[500px] border-border bg-card shadow-elevated hover:shadow-floating transition-shadow duration-300">
          <Suspense fallback={<LoadingFallback />}>
            <ArtifactTabs searchQuery={searchQuery} />
          </Suspense>
        </div>
      </div>
    </div>
  )
})

interface UnifiedStudioTabsProps {
  meetingNotes: string
  setMeetingNotes: (notes: string) => void
  selectedArtifactType: ArtifactType
  setSelectedArtifactType: (type: ArtifactType) => void
  contextId: string | null
  setContextId: (id: string | null) => void
  isGenerating: boolean
  progress: any
  generate: (params: any) => Promise<void>
  clearProgress: () => void
  cancelGeneration?: () => void
  isBuilding: boolean
  build: (params: any) => Promise<any>
  artifacts: any[]
  getArtifactsByType: (type: ArtifactType) => any[]
  artifactTypes: { value: ArtifactType; label: string; category: string }[]
}

// Memoized tab button component to prevent unnecessary re-renders
const TabButton = memo(function TabButton({ 
  id, 
  label, 
  icon: Icon, 
  isActive, 
  onClick 
}: { 
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  isActive: boolean
  onClick: () => void
}) {
  return (
    <button
      data-tab={id}
      onClick={onClick}
      className={`
        px-4 py-2 text-xs font-semibold rounded-lg transition-all duration-200 flex items-center gap-2
        ${isActive
          ? 'text-primary-foreground bg-primary shadow-md'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
        }
      `}
    >
      <Icon className={`w-4 h-4 ${isActive ? 'text-primary-foreground' : ''}`} />
      <span>{label}</span>
    </button>
  )
})

// Memoized artifact type button for the grid
const ArtifactTypeButton = memo(function ArtifactTypeButton({
  type,
  isSelected,
  onClick
}: {
  type: { value: ArtifactType; label: string; category: string }
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left px-3 py-2.5 text-xs rounded-lg border transition-all ${
        isSelected
          ? 'border-primary bg-primary/10 text-primary font-bold shadow-sm'
          : 'border-transparent bg-background/30 hover:bg-background/50 text-muted-foreground hover:text-foreground'
      }`}
    >
      {type.label}
    </button>
  )
})

function UnifiedStudioTabs(props: UnifiedStudioTabsProps) {
  const [activeView, setActiveView] = useState('context')
  
  // Memoize tabs configuration
  const tabs = useMemo(() => [
    { id: 'context', label: 'Context', icon: FileText },
    { id: 'studio', label: 'Studio', icon: Sparkles },
    { id: 'library', label: 'Library', icon: Folder },
    { id: 'version-control', label: 'Version Control', icon: GitBranch },
    { id: 'settings', label: 'Settings', icon: Settings },
  ], [])
  
  const [aiQuestion, setAiQuestion] = useState('')
  const [aiResponse, setAiResponse] = useState<string | null>(null)
  const [isAskingAi, setIsAskingAi] = useState(false)
  const quickInputRef = useRef<HTMLTextAreaElement | null>(null)
  const qualityPrediction = props.progress?.qualityPrediction
  const qualityBadgeClass = !qualityPrediction
    ? 'bg-muted text-muted-foreground'
    : qualityPrediction.label === 'high'
      ? 'bg-primary/10 text-primary border border-primary/30'
      : qualityPrediction.label === 'medium'
        ? 'bg-accent/10 text-accent border border-accent/30'
        : 'bg-destructive/10 text-destructive border border-destructive/30'
  const { addArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()
  const [isBulkDialogOpen, setBulkDialogOpen] = useState(false)
  const [isBulkGenerating, setIsBulkGenerating] = useState(false)
  
  // Meeting notes folder selection state
  const [folders, setFolders] = useState<Array<{ id: string; name: string; notes_count: number }>>([])
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)
  
  // Import useSystemStatus to check backend readiness
  const { isReady: backendReady } = useSystemStatus()
  
  // Load folders when generate tab is active and backend is ready
  useEffect(() => {
    if (backendReady) {
      loadFolders()
    }
  }, [backendReady])
  
  const loadFolders = async () => {
    try {
      const { default: api } = await import('../services/api')
      const response = await api.get('/api/meeting-notes/folders')
      setFolders(response.data.folders || [])
    } catch (error) {
      // Failed to load folders - handle in UI
      console.error('Failed to load folders:', error)
    }
  }

  const handleBuildContext = useCallback(async () => {
    if (!selectedFolderId && props.meetingNotes.length < 10) {
      alert('Please select a folder or provide meeting notes (at least 10 characters)')
      return
    }

    try {
      const response = await props.build({
        meeting_notes: selectedFolderId ? undefined : props.meetingNotes,
        folder_id: selectedFolderId || undefined,
        include_rag: true,
        include_kg: true,
        include_patterns: true,
        max_rag_chunks: 18,
        artifact_type: props.selectedArtifactType,
      })
      if (response?.context_id) {
        props.setContextId(response.context_id)
        addNotification('success', 'Context built successfully!')
      } else {
        addNotification('warning', 'Context built but no ID returned. Generation will still work.')
      }
    } catch (error: any) {
      console.error('Context build error:', error)
      const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to build context'
      addNotification('error', `Context build failed: ${errorMsg}. You can still generate directly.`)
      // Don't throw - allow generation to proceed without context
    }
  }, [props, selectedFolderId])

  const handleGenerate = useCallback(async () => {
    // Allow generation even without context - it will build context on-the-fly
    if (!selectedFolderId && props.meetingNotes.length < 10) {
      alert('Please provide meeting notes (at least 10 characters) or select a folder')
      return
    }

    try {
      await props.generate({
        context_id: props.contextId || undefined,
        meeting_notes: (!props.contextId && !selectedFolderId) ? props.meetingNotes : undefined,
        folder_id: (!props.contextId && selectedFolderId) ? selectedFolderId : undefined,
        artifact_type: props.selectedArtifactType,
        options: {
          max_retries: 3,
          use_validation: true,
          temperature: 0.7,
        },
      })
    } catch (error: any) {
      console.error('Generation error:', error)
      addNotification('error', error?.response?.data?.detail || error?.message || 'Failed to generate artifact. Please try again.')
    }
  }, [props, selectedFolderId, addNotification])

  const handleAskAi = useCallback(async (question: string) => {
    if (!question.trim()) return
    setIsAskingAi(true)
    setAiResponse(null)

    try {
      const { sendChatMessage } = await import('../services/chatService')
      const response = await sendChatMessage({
        message: question,
        conversation_history: [],
        include_project_context: true
      })
      setAiResponse(response.message)
    } catch (error) {
      // Chat error - show user error
      setAiResponse('Sorry, I encountered an error. Please try again.')
    } finally {
      setIsAskingAi(false)
    }
  }, [])

  const handleBulkGenerate = useCallback(async (selectedArtifacts: ArtifactType[]) => {
    if (!props.meetingNotes || props.meetingNotes.length < 10) {
      addNotification('error', 'Please provide meeting notes before bulk generation.')
      return
    }
    setIsBulkGenerating(true)
    try {
      const response = await bulkGenerate(
        selectedArtifacts.map((artifact_type) => ({
          artifact_type,
          meeting_notes: props.meetingNotes,
          context_id: props.contextId || undefined,
        }))
      )
      response.forEach((item) => {
        if (item.artifact) {
          addArtifact(item.artifact)
        }
      })
      addNotification('success', `Bulk generation triggered for ${selectedArtifacts.length} artifacts.`)
    } catch (error) {
      // Bulk generation failed - show user error
      addNotification('error', 'Bulk generation failed. Please try again.')
    } finally {
      setIsBulkGenerating(false)
    }
  }, [addArtifact, addNotification, props.contextId, props.meetingNotes])

  const keyboardShortcuts = useMemo(
    () => [
      {
        ...COMMON_SHORTCUTS.BUILD_CONTEXT,
        action: () => {
          if (!props.isBuilding) {
            handleBuildContext()
          }
        },
      },
      {
        ...COMMON_SHORTCUTS.GENERATE,
        action: () => {
          if (!props.isGenerating) {
            handleGenerate()
          }
        },
      },
      {
        ...COMMON_SHORTCUTS.NEW_MEETING_NOTES,
        action: () => {
          quickInputRef.current?.focus()
        },
      },
    ],
    [handleBuildContext, handleGenerate, props.isBuilding, props.isGenerating]
  )

  useKeyboardShortcuts(keyboardShortcuts)

  return (
    <div className="h-full flex flex-col gap-2">
      {/* Compact Tab Navigation */}
      <div className="flex-shrink-0">
        <div className="glass-panel rounded-xl p-1.5 flex items-center justify-between bg-card border-border">
          <div className="flex items-center gap-1 flex-wrap">
            {tabs.map((tab) => (
              <TabButton
                key={tab.id}
                id={tab.id}
                label={tab.label}
                icon={tab.icon}
                isActive={activeView === tab.id}
                onClick={() => setActiveView(tab.id)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Content Area - Maximum Space */}
      <div className="flex-1 min-h-0 overflow-auto">
        
        {/* CONTEXT VIEW */}
        {activeView === 'context' && (
          <div className="h-full overflow-auto custom-scrollbar p-1 animate-fade-in-up">
            <div className="flex justify-center items-start pb-6">
              {/* Meeting Notes Card - Full Width, Centered */}
              <div className="w-full max-w-4xl glass-panel rounded-2xl p-0 flex flex-col shadow-elevated hover:shadow-floating transition-all duration-300 interactive-card bg-card border-border">
                <div className="p-6 border-b border-border bg-secondary/30 flex items-center gap-3">
                   <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-md group-hover:shadow-lg transition-shadow duration-300">
                      <FileText className="w-6 h-6 text-primary" />
                   </div>
                   <div className="flex-1">
                      <h2 className="text-lg font-bold text-foreground truncate-with-ellipsis">Project Context</h2>
                      <p className="text-xs text-muted-foreground uppercase tracking-wider truncate-with-ellipsis">Meeting Notes & Requirements</p>
                   </div>
                </div>
                <div className="flex-1 overflow-auto custom-scrollbar p-6 bg-background/10">
                  <Suspense fallback={<LoadingFallback />}>
                    <MeetingNotesManager />
                  </Suspense>
                </div>
                <div className="p-6 border-t border-border bg-secondary/10 text-center">
                  <p className="text-xs text-muted-foreground">
                    💡 <strong>Tip:</strong> For insights into your codebase, visit the <strong>Intelligence</strong> page to view the Knowledge Graph and Pattern Mining results.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STUDIO VIEW */}
        {activeView === 'studio' && (
          <div className="h-full p-1 animate-fade-in-up overflow-auto custom-scrollbar">
            <div className="grid grid-cols-12 gap-4 min-h-full">
              {/* Left Column: Inputs */}
              <div className="col-span-4 flex flex-col gap-4 overflow-auto custom-scrollbar">
                {/* Generation Controls */}
                <div className="glass-panel rounded-2xl p-6 flex-shrink-0 border-border shadow-elevated hover:shadow-floating transition-all duration-300 bg-card">
                  <div className="flex items-center gap-3 mb-6">
                     <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center border border-primary/30 animate-pulse-glow shadow-lg">
                        <Sparkles className="w-6 h-6 text-primary" />
                     </div>
                     <h2 className="text-xl font-black text-foreground tracking-tight truncate-with-ellipsis">Generator</h2>
                  </div>
                  
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold text-primary uppercase tracking-widest flex items-center gap-2">
                        <Folder className="w-3 h-3" />
                        Data Source
                      </label>
                      <select
                        value={selectedFolderId || ''}
                        onChange={(e) => setSelectedFolderId(e.target.value || null)}
                        className="w-full px-4 py-3 text-sm glass-input rounded-xl text-foreground outline-none focus:border-primary focus:shadow-lg focus:shadow-primary/10 transition-all duration-300 shadow-sm hover:shadow-md truncate-with-ellipsis"
                      >
                        <option value="" className="bg-card text-foreground">📝 Quick Notes (Below)</option>
                        {folders.map((folder) => (
                          <option key={folder.id} value={folder.id} className="bg-card text-foreground">
                            📁 {folder.name} ({folder.notes_count} notes)
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-[10px] font-bold text-primary uppercase tracking-widest flex items-center gap-2">
                        <FileText className="w-3 h-3" />
                        Requirements
                      </label>
                      <textarea
                        ref={quickInputRef}
                        value={props.meetingNotes}
                        onChange={(e) => props.setMeetingNotes(e.target.value)}
                        placeholder="Describe what you want to build..."
                        className="w-full h-32 p-4 text-sm glass-input rounded-xl text-foreground resize-none outline-none focus:border-primary focus:shadow-lg focus:shadow-primary/10 transition-all duration-300 shadow-sm hover:shadow-md"
                        disabled={!!selectedFolderId}
                      />
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={handleBuildContext}
                        disabled={props.isBuilding || (!selectedFolderId && props.meetingNotes.length < 10)}
                        className="flex-1 py-3 glass-button text-foreground text-sm font-bold rounded-xl flex items-center justify-center gap-2 hover:text-primary hover:bg-primary/10 hover:shadow-lg transition-all duration-300 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                      >
                        {props.isBuilding ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4 text-primary" />}
                        BUILD CONTEXT
                      </button>
                      <button
                        onClick={() => setBulkDialogOpen(true)}
                        className="px-4 py-3 glass-button text-foreground rounded-xl hover:text-primary hover:bg-primary/10 hover:shadow-lg transition-all duration-300 shadow-sm group"
                        title="Bulk Generate"
                      >
                        <ListTodo className="w-5 h-5 group-hover:scale-110 transition-transform duration-300" />
                      </button>
                    </div>

                    <div className="pt-5 border-t border-border/50">
                      <label className="text-[10px] font-bold text-primary uppercase tracking-widest mb-3 block">Select Artifact</label>
                      <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto custom-scrollbar pr-1">
                        {props.artifactTypes.map((type) => (
                          <ArtifactTypeButton
                            key={type.value}
                            type={type}
                            isSelected={props.selectedArtifactType === type.value}
                            onClick={() => props.setSelectedArtifactType(type.value)}
                          />
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={handleGenerate}
                      disabled={props.isGenerating || (!selectedFolderId && props.meetingNotes.length < 10)}
                      className="w-full py-4 bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary text-primary-foreground rounded-xl font-black uppercase tracking-widest shadow-lg shadow-primary/30 hover:shadow-xl hover:shadow-primary/40 transition-all duration-300 flex items-center justify-center gap-3 transform hover:-translate-y-1 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                    >
                      {props.isGenerating ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          PROCESSING...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5 fill-current" />
                          GENERATE
                        </>
                      )}
                    </button>

                    {/* Progress Bar */}
                    {props.isGenerating && props.progress && (
                      <div className="space-y-2 glass-panel p-4 rounded-xl text-xs border-primary/30 mt-4 bg-background/30">
                         <div className="flex justify-between items-center">
                            <span className="uppercase tracking-wider text-primary font-bold">{props.progress.status?.replace(/_/g, ' ')}</span>
                            <span className="font-mono font-bold text-foreground">{props.progress.progress}%</span>
                         </div>
                         <div className="h-2 bg-background/50 rounded-full overflow-hidden border border-border/50">
                            <div 
                              className="h-full bg-primary transition-all duration-500 shadow-[0_0_10px_rgba(var(--primary),0.8)]"
                              style={{ width: `${props.progress.progress}%` }} 
                            />
                         </div>
                         {qualityPrediction && (
                            <div className="flex justify-between items-center text-[10px] text-muted-foreground mt-2 pt-2 border-t border-border/50">
                              <span>QUALITY FORECAST</span>
                              <span className={`font-bold px-2 py-0.5 rounded-full ${qualityBadgeClass}`}>
                                {qualityPrediction.label.toUpperCase()}
                              </span>
                            </div>
                         )}
                         {/* Cancel Button */}
                         {props.cancelGeneration && (
                           <button
                             onClick={props.cancelGeneration}
                             className="w-full mt-3 py-2 text-xs font-bold text-destructive bg-destructive/10 hover:bg-destructive/20 border border-destructive/30 rounded-lg transition-all duration-200 uppercase tracking-wider"
                           >
                             Cancel Generation
                           </button>
                         )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Main Workspace */}
              <div className="col-span-8 glass-panel rounded-2xl overflow-hidden flex flex-col shadow-floating border-border bg-card backdrop-blur-xl hover:shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)] transition-shadow duration-500 min-h-[400px]">
                 <div className="border-b border-border p-4 flex items-center gap-4 bg-secondary/20">
                    <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary/10 to-primary/5 border border-primary/30 rounded-lg shadow-sm">
                      <Code className="w-4 h-4 text-primary" />
                      <span className="text-xs font-bold text-primary uppercase tracking-wider">Editor Mode</span>
                    </div>
                    <div className="h-6 w-px bg-border/50" />
                    <span className="text-sm font-bold text-foreground truncate-with-ellipsis">
                       {props.artifactTypes.find(t => t.value === props.selectedArtifactType)?.label || 'Select Artifact'}
                    </span>
                 </div>
                 <div className="flex-1 overflow-hidden relative bg-background/20 flex flex-col">
                    {/* Render appropriate editor based on artifact type */}
                    {props.selectedArtifactType.includes('mermaid') ? (
                      <>
                        {/* Mermaid Diagram Rendering */}
                        <div className="flex-1 overflow-hidden">
                          <Suspense fallback={<LoadingFallback />}>
                            {(() => {
                              const latestArtifact = props.getArtifactsByType(props.selectedArtifactType)?.[0]
                              if (latestArtifact?.content) {
                                return <MermaidRenderer content={latestArtifact.content} />
                              } else if (props.progress?.artifact?.content) {
                                return <MermaidRenderer content={props.progress.artifact.content} />
                              } else {
                                return (
                                  <div className="h-full flex items-center justify-center p-8">
                                    <div className="text-center max-w-md">
                                      <FileCode className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                                      <h3 className="text-lg font-semibold text-muted-foreground mb-2">No Diagram Generated Yet</h3>
                                      <p className="text-sm text-muted-foreground">
                                        Click "Generate" to create your {props.artifactTypes.find(t => t.value === props.selectedArtifactType)?.label || 'diagram'}
                                      </p>
                                    </div>
                                  </div>
                                )
                              }
                            })()}
                          </Suspense>
                        </div>
                        {/* Small Footer - Canvas Editor Link */}
                        <div className="border-t border-border px-4 py-3 bg-secondary/10 flex items-center justify-between flex-shrink-0">
                          <span className="text-xs text-muted-foreground flex items-center gap-2">
                            <Sparkles className="w-3 h-3 text-primary" />
                            For interactive editing with drag-and-drop, use <strong>Canvas</strong>
                          </span>
                          <button
                            onClick={() => window.location.href = '/canvas'}
                            className="text-xs px-3 py-1.5 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors flex items-center gap-1.5 font-medium"
                          >
                            <Edit3 className="w-3 h-3" />
                            Edit in Canvas
                          </button>
                        </div>
                      </>
                    ) : props.selectedArtifactType === 'code_prototype' ? (
                      <Suspense fallback={<LoadingFallback />}>
                        <CodeWithTestsEditor />
                      </Suspense>
                    ) : (
                      <Suspense fallback={<LoadingFallback />}>
                        <InteractivePrototypeEditor artifactType={props.selectedArtifactType} />
                      </Suspense>
                    )}
                 </div>
              </div>
            </div>
          </div>
        )}

        {/* LIBRARY VIEW */}
        {activeView === 'library' && (
          <LibraryView />
        )}

        {/* VERSION CONTROL VIEW */}
        {activeView === 'version-control' && (
          <div className="h-full overflow-auto custom-scrollbar p-4 animate-fade-in-up">
            <div className="w-full h-full">
              <Suspense fallback={<LoadingFallback />}>
                <VersionControl />
              </Suspense>
            </div>
          </div>
        )}

        {/* SETTINGS VIEW */}
        {activeView === 'settings' && (
          <div className="h-full overflow-auto custom-scrollbar p-4 animate-fade-in-up">
            <div className="max-w-5xl mx-auto space-y-8 pb-10">
              <div className="glass-panel rounded-2xl p-6 border-border shadow-elevated bg-card">
                <h2 className="text-4xl font-black text-foreground tracking-tight flex items-center gap-3">
                  <span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">Configuration</span>
                </h2>
                <p className="text-sm text-muted-foreground mt-2">Manage your application settings and preferences</p>
              </div>
              
              <div className="glass-panel rounded-2xl overflow-hidden shadow-elevated hover:shadow-floating transition-all duration-300 border-border bg-card interactive-card">
                 <div className="border-b border-border bg-secondary/20 px-8 py-6 backdrop-blur-md">
                    <h3 className="font-black text-lg flex items-center gap-3 text-foreground">
                       <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center border border-primary/30">
                         <Network className="w-5 h-5 text-primary" />
                       </div>
                       Model Fine-Tuning
                    </h3>
                    <p className="text-xs text-muted-foreground mt-2 ml-13">Configure and train custom models</p>
                 </div>
                 <div className="p-8">
                    <div className="text-center py-12">
                      <Sliders className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                      <p className="text-lg font-medium text-muted-foreground mb-2">Fine-Tuning Settings</p>
                      <p className="text-sm text-muted-foreground">
                        Configure model fine-tuning in the <strong>Intelligence</strong> page
                      </p>
                    </div>
                 </div>
              </div>

              <div className="glass-panel rounded-2xl overflow-hidden shadow-elevated hover:shadow-floating transition-all duration-300 border-border bg-card interactive-card">
                 <div className="border-b border-border bg-secondary/20 px-8 py-6 backdrop-blur-md">
                    <h3 className="font-black text-lg flex items-center gap-3 text-foreground">
                       <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center border border-accent/30">
                         <Key className="w-5 h-5 text-accent" />
                       </div>
                       API Keys
                    </h3>
                    <p className="text-xs text-muted-foreground mt-2 ml-13">Manage your API keys and credentials</p>
                 </div>
                 <div className="p-8">
                    <Suspense fallback={<LoadingFallback />}>
                      <ApiKeysManager />
                    </Suspense>
                 </div>
              </div>

              <div className="glass-panel rounded-2xl overflow-hidden shadow-elevated hover:shadow-floating transition-all duration-300 border-border bg-card interactive-card">
                 <div className="border-b border-border bg-secondary/20 px-6 py-5 backdrop-blur-md">
                    <h3 className="font-black flex items-center gap-3 text-foreground">
                       <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center border border-accent/30">
                         <Download className="w-4 h-4 text-accent" />
                       </div>
                       Export Options
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1 ml-11 truncate-with-ellipsis">Export your artifacts</p>
                 </div>
                 <div className="p-6">
                    <Suspense fallback={<LoadingFallback />}>
                      <ExportManager />
                    </Suspense>
                 </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <BulkGenerationDialog
        isOpen={isBulkDialogOpen}
        onClose={() => setBulkDialogOpen(false)}
        artifactTypes={props.artifactTypes}
        onGenerate={handleBulkGenerate}
      />
    </div>
  )
}

// Export with memo for shallow prop comparison optimization
export default memo(UnifiedStudioTabs)
