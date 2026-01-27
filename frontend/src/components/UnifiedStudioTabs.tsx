import React, { useState, useEffect, useCallback, useMemo, useRef, lazy, Suspense, memo, ComponentType } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArtifactType } from '../services/generationService'
import { useSystemStatus } from '../hooks/useSystemStatus'
import {
  Loader2, Sparkles, FileText, CheckCircle2, Folder, Code, FileCode,
  Download, Key, Settings, Search, Network, ListTodo, Sliders, Edit3, GitBranch,
  FolderGit2, Link2, ShieldCheck
} from 'lucide-react'
import MeetingNotesManager from './MeetingNotesManager'
import BulkGenerationDialog from './BulkGenerationDialog'
import { bulkGenerate, updateArtifact as updateArtifactApi } from '../services/generationService'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { useDiagramStore } from '../stores/diagramStore'
import { useKeyboardShortcuts, COMMON_SHORTCUTS } from '../hooks/useKeyboardShortcuts'

// Lazy load with retry - handles chunk loading failures after deployments
function lazyWithRetry<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  retries = 2
): React.LazyExoticComponent<T> {
  return lazy(() =>
    importFn().catch((error) => {
      const isChunkError = error.message?.includes('dynamically imported module') ||
        error.message?.includes('Loading chunk') ||
        error.message?.includes('Failed to fetch')

      if (isChunkError && retries > 0) {
        console.warn(`Chunk loading failed, retrying... (${retries} attempts left)`)
        return new Promise<{ default: T }>((resolve) => {
          setTimeout(() => {
            resolve(lazyWithRetry(importFn, retries - 1) as unknown as { default: T })
          }, 1000)
        })
      }

      if (isChunkError) {
        console.error('Chunk loading failed, reloading page...')
        window.location.reload()
      }

      throw error
    })
  )
}

// Lazy load heavy components with retry logic for deployment resilience
const ArtifactTabs = lazyWithRetry(() => import('./artifacts/ArtifactTabs'))
const CodeEditor = lazyWithRetry(() => import('./CodeEditor'))
const ExportManager = lazyWithRetry(() => import('./ExportManager'))
const MarkdownArtifactViewer = lazyWithRetry(() => import('./MarkdownArtifactViewer'))
const SemanticSearchPanel = lazyWithRetry(() => import('./SemanticSearchPanel'))
const ApiKeysManager = lazyWithRetry(() => import('./ApiKeysManager'))
const InteractivePrototypeEditor = lazyWithRetry(() => import('./InteractivePrototypeEditor'))
const CodeWithTestsEditor = lazyWithRetry(() => import('./CodeWithTestsEditor'))
const MermaidRenderer = lazyWithRetry(() => import('./MermaidRenderer'))
const VersionControl = lazyWithRetry(() => import('./VersionControl'))
const MultiRepoManager = lazyWithRetry(() => import('./MultiRepoManager'))
const ArtifactDependencies = lazyWithRetry(() => import('./ArtifactDependencies'))

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
  const { artifacts, currentFolderId } = useArtifactStore()

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
              {currentFolderId && (
                <span className="text-sm font-medium text-primary bg-primary/10 px-3 py-1 rounded-lg flex items-center gap-1.5">
                  <Folder className="w-4 h-4" />
                  {currentFolderId}
                </span>
              )}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              {artifacts.length} artifact{artifacts.length !== 1 ? 's' : ''} • {currentFolderId ? `Showing artifacts for folder "${currentFolderId}"` : 'Browse and manage your generated artifacts'}
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
  generate: (params: any) => Promise<any>
  clearProgress: () => void
  cancelGeneration?: () => void
  isBuilding: boolean
  build: (params: any) => Promise<any>
  artifacts: any[]
  getArtifactsByType: (type: ArtifactType) => any[]
  artifactTypes: { value: ArtifactType; label: string; category: string }[]
  onOpenCustomArtifactModal?: () => void  // Open custom artifact type modal
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
      className={`text-left px-3 py-2.5 text-xs rounded-lg border transition-all ${isSelected
          ? 'border-primary bg-primary/10 text-primary font-bold shadow-sm'
          : 'border-transparent bg-background/30 hover:bg-background/50 text-muted-foreground hover:text-foreground'
        }`}
    >
      {type.label}
    </button>
  )
})

// Helper function to get the currently displayed artifact (matches MermaidDiagramViewer logic)
function getDisplayedArtifact(selectedArtifactType: ArtifactType, progress: any, getArtifactsByType: (type: ArtifactType) => any[]) {
  const latestArtifact = getArtifactsByType(selectedArtifactType)?.[0]
  return latestArtifact || progress?.artifact || null
}

// Edit in Canvas button component that uses the same artifact as MermaidDiagramViewer
// FIXED: Uses reactive selector to ensure fresh data and proper navigation
const EditInCanvasButton = memo(function EditInCanvasButton({
  selectedArtifactType,
  progress,
  navigate
}: {
  selectedArtifactType: ArtifactType
  progress: any
  navigate: (path: string, state?: any) => void
}) {
  // Use reactive selector pattern (same as MermaidDiagramViewer)
  const latestArtifact = useArtifactStore(
    useCallback(state => state.artifacts
      .filter(a => a.type === selectedArtifactType)
      .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))[0],
      [selectedArtifactType])
  )

  const displayedArtifact = latestArtifact || progress?.artifact || null

  const handleEditInCanvas = useCallback(() => {
    if (displayedArtifact) {
      // FIXED: Pass both artifactId AND diagramId for backward compatibility
      // Canvas.tsx checks for both keys
      navigate('/canvas', {
        state: {
          artifactId: displayedArtifact.id,
          diagramId: displayedArtifact.id,  // Canvas also checks this key
          artifactType: displayedArtifact.type
        }
      })
    }
  }, [displayedArtifact, navigate])

  if (!displayedArtifact) {
    return null
  }

  return (
    <button
      onClick={handleEditInCanvas}
      className="text-xs px-3 py-1.5 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors flex items-center gap-1.5 font-medium"
    >
      <Edit3 className="w-3 h-3" />
      Edit in Canvas
    </button>
  )
})

// Skeleton loader for diagram viewer - prevents flash of "no content" during load
const DiagramSkeleton = memo(function DiagramSkeleton() {
  return (
    <div className="h-full flex items-center justify-center p-8 animate-pulse">
      <div className="text-center max-w-md w-full">
        {/* Diagram placeholder */}
        <div className="mx-auto mb-6 w-full max-w-lg">
          <div className="bg-muted/40 rounded-xl p-6 space-y-4">
            {/* Entity boxes */}
            <div className="flex justify-between gap-4">
              <div className="flex-1 h-24 bg-muted/60 rounded-lg" />
              <div className="flex-1 h-24 bg-muted/60 rounded-lg" />
            </div>
            {/* Connecting lines placeholder */}
            <div className="flex justify-center">
              <div className="w-32 h-2 bg-muted/50 rounded" />
            </div>
            <div className="flex justify-between gap-4">
              <div className="flex-1 h-20 bg-muted/60 rounded-lg" />
              <div className="flex-1 h-20 bg-muted/60 rounded-lg" />
              <div className="flex-1 h-20 bg-muted/60 rounded-lg" />
            </div>
          </div>
        </div>
        <div className="flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground font-medium">Loading diagram...</span>
        </div>
      </div>
    </div>
  )
})

// MermaidDiagramViewer component that uses store directly for reactivity
const MermaidDiagramViewer = memo(function MermaidDiagramViewer({
  selectedArtifactType,
  progress,
  artifactTypes,
  onContentUpdate,
  isGenerating = false
}: {
  selectedArtifactType: ArtifactType
  progress: any
  artifactTypes: { value: ArtifactType; label: string; category: string }[]
  onContentUpdate: (artifact: any, newContent: string) => Promise<void>
  isGenerating?: boolean
}) {
  // CRITICAL FIX: Use reactive selector pattern to ensure re-render on artifact updates
  // This fixes the bug where AI Repair succeeds but component doesn't re-render
  const { isLoading } = useArtifactStore()
  const { resetState: resetDiagramState } = useDiagramStore()
  const latestArtifact = useArtifactStore(
    useCallback(state => state.artifacts
      .filter(a => a.type === selectedArtifactType)
      .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))[0],
      [selectedArtifactType])
  )

  // CRITICAL FIX: Reset diagram state when artifact type changes
  // This prevents "zombie state" where errors from a broken diagram of type A
  // persist when viewing a working diagram of type B
  // We use useEffect here but also add a key to MermaidRenderer below for instant reset
  useEffect(() => {
    resetDiagramState()
  }, [selectedArtifactType, resetDiagramState])

  const handleDiagramContentUpdate = useCallback(async (newContent: string) => {
    const artifact = latestArtifact || progress?.artifact
    if (!artifact) return
    await onContentUpdate(artifact, newContent)
  }, [latestArtifact, progress?.artifact, onContentUpdate])

  // CRITICAL: Show skeleton while loading to prevent race condition
  // This fixes the bug where "No Diagram Generated Yet" flashes before data loads
  if (isLoading && !latestArtifact?.content && !progress?.artifact?.content) {
    return <DiagramSkeleton />
  }

  // Show skeleton during generation (before artifact is ready)
  if (isGenerating && !progress?.artifact?.content && !latestArtifact?.content) {
    return <DiagramSkeleton />
  }

  if (latestArtifact?.content) {
    return (
      <MermaidRenderer
        // CRITICAL: key forces remount when artifact type/id changes, clearing all state including errors
        key={`${selectedArtifactType}-${latestArtifact.id}`}
        content={latestArtifact.content}
        artifactType={selectedArtifactType}
        onContentUpdate={handleDiagramContentUpdate}
      />
    )
  } else if (progress?.artifact?.content) {
    return (
      <MermaidRenderer
        // CRITICAL: key forces remount when artifact type changes during generation
        key={`${selectedArtifactType}-progress`}
        content={progress.artifact.content}
        artifactType={selectedArtifactType}
        onContentUpdate={handleDiagramContentUpdate}
      />
    )
  } else {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <FileCode className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold text-muted-foreground mb-2">No Diagram Generated Yet</h3>
          <p className="text-sm text-muted-foreground">
            Click "Generate" to create your {artifactTypes.find(t => t.value === selectedArtifactType)?.label || 'diagram'}
          </p>
        </div>
      </div>
    )
  }
})

function UnifiedStudioTabs(props: UnifiedStudioTabsProps) {
  const [activeView, setActiveView] = useState('context')
  const [selectedCategory, setSelectedCategory] = useState<string>('All')  // Category filter for artifact types
  const navigate = useNavigate()

  // CRITICAL FIX: Reset diagram error state when switching artifact types
  // This prevents "zombie state" where errors from broken diagrams persist
  // and infect subsequent working diagrams
  const { resetState: resetDiagramState } = useDiagramStore()

  useEffect(() => {
    // Clear stale diagram errors when switching to a different artifact type
    resetDiagramState()
  }, [props.selectedArtifactType, resetDiagramState])

  // Get unique categories from artifact types
  const categories = useMemo(() => {
    const cats = ['All', ...new Set(props.artifactTypes.map(t => t.category))]
    return cats
  }, [props.artifactTypes])

  // Filter artifact types by selected category
  const filteredArtifactTypes = useMemo(() => {
    if (selectedCategory === 'All') {
      return props.artifactTypes
    }
    return props.artifactTypes.filter(t => t.category === selectedCategory)
  }, [props.artifactTypes, selectedCategory])

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
  const { addArtifact, updateArtifact, getArtifactsByType } = useArtifactStore()
  const { addNotification } = useUIStore()
  const [isBulkDialogOpen, setBulkDialogOpen] = useState(false)
  const [isBulkGenerating, setIsBulkGenerating] = useState(false)

  // Meeting notes folder selection state - sync with global store
  const [folders, setFolders] = useState<Array<{ id: string; name: string; notes_count: number }>>([])
  const { currentFolderId, setCurrentFolderId } = useArtifactStore()

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
    if (!currentFolderId && props.meetingNotes.length < 10) {
      alert('Please select a folder or provide meeting notes (at least 10 characters)')
      return
    }

    try {
      const response = await props.build({
        meeting_notes: currentFolderId ? undefined : props.meetingNotes,
        folder_id: currentFolderId || undefined,
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
  }, [props, currentFolderId])

  const handleGenerate = useCallback(async () => {
    // Allow generation even without context - it will build context on-the-fly
    if (!currentFolderId && props.meetingNotes.length < 10) {
      alert('Please provide meeting notes (at least 10 characters) or select a folder')
      return
    }

    try {
      await props.generate({
        context_id: props.contextId || undefined,
        meeting_notes: (!props.contextId && !currentFolderId) ? props.meetingNotes : undefined,
        folder_id: (!props.contextId && currentFolderId) ? currentFolderId : undefined,
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
  }, [props, currentFolderId, addNotification])

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
    const trimmedNotes = props.meetingNotes.trim()
    const useNotes = trimmedNotes.length >= 10 ? trimmedNotes : undefined
    const hasFolder = !!currentFolderId
    const hasContext = !!props.contextId

    if (!useNotes && !hasFolder && !hasContext) {
      addNotification('error', 'Please provide meeting notes (>=10 chars), select a folder, or reuse a built context before bulk generation.')
      return
    }

    setIsBulkGenerating(true)
    try {
      const response = await bulkGenerate(
        selectedArtifacts.map((artifact_type) => ({
          artifact_type,
          meeting_notes: useNotes,
          context_id: hasContext ? props.contextId || undefined : undefined,
          folder_id: !useNotes && hasFolder ? currentFolderId || undefined : undefined,
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
  }, [addArtifact, addNotification, props.contextId, props.meetingNotes, currentFolderId])

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
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-full">
              {/* Left Column: Inputs */}
              <div className="lg:col-span-4 flex flex-col gap-4 overflow-auto custom-scrollbar">
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
                        value={currentFolderId || ''}
                        onChange={(e) => setCurrentFolderId(e.target.value || null)}
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
                        disabled={!!currentFolderId}
                      />
                    </div>

                    <div className="flex gap-3">
                      <button
                        onClick={handleBuildContext}
                        disabled={props.isBuilding || (!currentFolderId && props.meetingNotes.length < 10)}
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
                      <div className="flex items-center justify-between mb-3">
                        <label className="text-[10px] font-bold text-primary uppercase tracking-widest">Select Artifact</label>
                        {props.onOpenCustomArtifactModal && (
                          <button
                            onClick={props.onOpenCustomArtifactModal}
                            className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-primary hover:bg-primary/10 rounded-lg transition-colors"
                            title="Create custom artifact type"
                          >
                            <Sparkles className="w-3 h-3" />
                            Custom
                          </button>
                        )}
                      </div>

                      {/* Category Tabs */}
                      <div className="flex flex-wrap gap-1 mb-3">
                        {categories.map((category) => (
                          <button
                            key={category}
                            onClick={() => setSelectedCategory(category)}
                            className={`px-2 py-1 text-[10px] font-medium rounded-md transition-all ${selectedCategory === category
                                ? 'bg-primary text-primary-foreground shadow-sm'
                                : 'bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground'
                              }`}
                          >
                            {category}
                            <span className="ml-1 opacity-60">
                              ({category === 'All'
                                ? props.artifactTypes.length
                                : props.artifactTypes.filter(t => t.category === category).length})
                            </span>
                          </button>
                        ))}
                      </div>

                      <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto custom-scrollbar pr-1">
                        {filteredArtifactTypes.map((type) => (
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
                      disabled={props.isGenerating || (!currentFolderId && props.meetingNotes.length < 10)}
                      className={`
                        w-full py-4 text-primary-foreground rounded-xl font-black uppercase tracking-widest shadow-lg transition-all duration-300 flex items-center justify-center gap-3
                        ${props.isGenerating
                          ? 'bg-primary/80 cursor-not-allowed shadow-none'
                          : 'bg-gradient-to-r from-primary to-primary/90 hover:from-primary/90 hover:to-primary shadow-primary/30 hover:shadow-xl hover:shadow-primary/40 hover:-translate-y-1 active:translate-y-0'
                        }
                        disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:translate-y-0
                      `}
                    >
                      {props.isGenerating ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          <span className="animate-pulse">GENERATING...</span>
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
              <div className="lg:col-span-8 glass-panel rounded-2xl overflow-hidden flex flex-col shadow-floating border-border bg-card backdrop-blur-xl hover:shadow-[0_25px_50px_-12px_rgba(0,0,0,0.15)] transition-shadow duration-500 min-h-[400px]">
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
                          <MermaidDiagramViewer
                            selectedArtifactType={props.selectedArtifactType}
                            progress={props.progress}
                            artifactTypes={props.artifactTypes}
                            isGenerating={props.isGenerating}
                            onContentUpdate={async (artifact, newContent) => {
                              // Update local store (prefer update to avoid duplicates)
                              updateArtifact(artifact.id, {
                                content: newContent,
                                updated_at: new Date().toISOString(),
                              })

                              try {
                                await updateArtifactApi(artifact.id, newContent, {
                                  artifact_type: artifact.type || props.selectedArtifactType
                                })
                                addNotification('success', 'Diagram updated with AI repair')
                              } catch (err: any) {
                                console.error('Failed to persist AI repair:', err)
                                addNotification('warning', 'Diagram updated locally, but saving failed.')
                              }
                            }}
                          />
                        </Suspense>
                      </div>
                      {/* Small Footer - Canvas Editor Link */}
                      <div className="border-t border-border px-4 py-3 bg-secondary/10 flex items-center justify-between flex-shrink-0">
                        <span className="text-xs text-muted-foreground flex items-center gap-2">
                          <Sparkles className="w-3 h-3 text-primary" />
                          For interactive editing with drag-and-drop, use <strong>Canvas</strong>
                        </span>
                        <EditInCanvasButton
                          selectedArtifactType={props.selectedArtifactType}
                          progress={props.progress}
                          navigate={navigate}
                        />
                      </div>
                    </>
                  ) : props.selectedArtifactType === 'code_prototype' ? (
                    <Suspense fallback={<LoadingFallback />}>
                      <CodeWithTestsEditor key="code-prototype" />
                    </Suspense>
                  ) : ['jira', 'backlog', 'personas', 'workflows', 'estimations', 'feature_scoring', 'api_docs'].includes(props.selectedArtifactType) ? (
                    /* PM/Documentation artifacts - render as formatted Markdown */
                    <Suspense fallback={<LoadingFallback />}>
                      {/* Key forces remount when type changes to ensure clean state */}
                      <MarkdownArtifactViewer key={`md-${props.selectedArtifactType}`} artifactType={props.selectedArtifactType} />
                    </Suspense>
                  ) : (
                    /* HTML artifacts (visual_prototype, html_*) - render in iframe with AI modifier */
                    <Suspense fallback={<LoadingFallback />}>
                      {/* Key forces remount when type changes to ensure clean state */}
                      <InteractivePrototypeEditor key={`html-${props.selectedArtifactType}`} artifactType={props.selectedArtifactType} />
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

              <div className="glass-panel rounded-2xl overflow-hidden shadow-elevated hover:shadow-floating transition-all duration-300 border-border bg-card interactive-card">
                <div className="border-b border-border bg-secondary/20 px-6 py-5 backdrop-blur-md">
                  <h3 className="font-black flex items-center gap-3 text-foreground">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/30">
                      <FolderGit2 className="w-4 h-4 text-emerald-500" />
                    </div>
                    Multi-Repository Analysis
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 ml-11">Configure multiple repositories for unified architecture analysis</p>
                </div>
                <div className="p-6">
                  <Suspense fallback={<LoadingFallback />}>
                    <MultiRepoManager />
                  </Suspense>
                </div>
              </div>

              <div className="glass-panel rounded-2xl overflow-hidden shadow-elevated hover:shadow-floating transition-all duration-300 border-border bg-card interactive-card">
                <div className="border-b border-border bg-secondary/20 px-6 py-5 backdrop-blur-md">
                  <h3 className="font-black flex items-center gap-3 text-foreground">
                    <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center border border-orange-500/30">
                      <Link2 className="w-4 h-4 text-orange-500" />
                    </div>
                    Artifact Dependencies
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1 ml-11">View and manage artifact relationships and staleness</p>
                </div>
                <div className="p-6">
                  <Suspense fallback={<LoadingFallback />}>
                    <ArtifactDependencies />
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
