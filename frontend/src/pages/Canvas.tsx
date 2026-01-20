import { useState, useEffect, useRef } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { useArtifactStore } from '../stores/artifactStore'
import { useDiagramStore } from '../stores/diagramStore'
import { FileCode, Sparkles, ChevronDown, FolderOpen } from 'lucide-react'
import EnhancedDiagramEditor from '../components/EnhancedDiagramEditor'

export default function Canvas() {
  const { artifacts, currentFolderId } = useArtifactStore()
  const { resetState: resetDiagramState } = useDiagramStore()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [targetType, setTargetType] = useState<string | null>(null)
  const [showSelector, setShowSelector] = useState(false)
  const selectorRef = useRef<HTMLDivElement>(null)
  
  // CRITICAL: Reset diagram state on unmount to prevent stale errors from leaking
  // between diagram views. This fixes the bug where viewing a broken diagram
  // then navigating to a working one would still show the error state.
  useEffect(() => {
    return () => {
      resetDiagramState()
    }
  }, [resetDiagramState])
  
  // Only show Mermaid diagrams (exclude HTML), filtered by current folder
  const diagramArtifacts = artifacts
    .filter(a => a.type.startsWith('mermaid_'))
    .filter(a => !currentFolderId || a.folder_id === currentFolderId)  // Filter by folder
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))

  // FIXED: If ID is set but not found, fall back to type-based or first diagram
  // This prevents showing empty canvas when artifact ID is stale/deleted
  const selectedArtifact = (() => {
    // First priority: Try to find by exact ID
    if (selectedArtifactId) {
      const byId = artifacts.find(a => a.id === selectedArtifactId)
      if (byId) return byId
      
      // ID not found - log warning and fall back
      console.warn(`[Canvas] Artifact ID "${selectedArtifactId}" not found, falling back to type/first`)
    }
    
    // Second priority: Find by type
    if (targetType) {
      const byType = diagramArtifacts.find(a => a.type === targetType)
      if (byType) return byType
    }
    
    // Last resort: First available diagram
    return diagramArtifacts[0] || null
  })()

  // Initialize selection from navigation state or query param
  // Supports multiple parameter styles: artifactId/artifactType OR diagramId/content
  useEffect(() => {
    const state = (location.state as { 
      artifactId?: string; 
      artifactType?: string;
      diagramId?: string;  // Alternative key from ArtifactCard (this is an ID, not a type)
      content?: string;    // Optional content for immediate display
    } | null) || {}
    const queryArtifactId = searchParams.get('artifactId') || searchParams.get('diagram')
    const queryArtifactType = searchParams.get('artifactType')
    
    // Support both 'artifactId' and 'diagramId' keys (both are IDs)
    const initialId = state.artifactId || state.diagramId || queryArtifactId
    // Only use artifactType from state or query - diagramId is an ID, not a type!
    const initialType = state.artifactType || queryArtifactType
    
    console.log('[Canvas] Navigation received:', { initialId, initialType, state, diagramArtifacts: diagramArtifacts.map(a => a.id) })
    
    if (initialId) {
      // Verify the artifact exists before setting
      const exists = artifacts.find(a => a.id === initialId)
      if (exists) {
        console.log('[Canvas] Setting artifact ID:', initialId)
        setSelectedArtifactId(initialId)
      } else {
        console.warn('[Canvas] Artifact not found by ID, trying type:', initialType)
        // Try to find by type instead
        if (initialType) {
          const byType = diagramArtifacts.find(a => a.type === initialType)
          if (byType) {
            console.log('[Canvas] Found artifact by type:', byType.id)
            setSelectedArtifactId(byType.id)
          }
        }
      }
    }
    if (initialType) {
      setTargetType(initialType)
    }
  }, [location.state, searchParams, artifacts, diagramArtifacts])

  useEffect(() => {
    // FIXED: Sync selectedArtifactId with actual selection to prevent stale ID issues
    
    // Case 1: ID is set but artifact not found (stale ID) - sync with actual selection
    if (selectedArtifactId && selectedArtifact && selectedArtifact.id !== selectedArtifactId) {
      console.debug('[Canvas] Syncing stale ID to actual artifact:', selectedArtifact.id)
      setSelectedArtifactId(selectedArtifact.id)
      return
    }
    
    // Case 2: No ID but have a target type - find by type
    if (!selectedArtifactId && targetType) {
      const latestOfType = diagramArtifacts.find(a => a.type === targetType)
      if (latestOfType) {
        setSelectedArtifactId(latestOfType.id)
        return
      }
    }
    
    // Case 3: No ID, no type - use first available
    if (diagramArtifacts.length > 0 && !selectedArtifactId) {
      setSelectedArtifactId(diagramArtifacts[0].id)
    }
  }, [diagramArtifacts, selectedArtifactId, selectedArtifact, targetType])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
        setShowSelector(false)
      }
    }

    if (showSelector) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [showSelector])

  return (
    <div className="w-full h-[calc(100vh-32px)] flex flex-col animate-fade-in-up overflow-hidden">
      
      {/* Folder Indicator + Compact Diagram Selector */}
      {currentFolderId && (
        <div className="mx-4 mb-2 flex items-center gap-2 text-xs text-primary bg-primary/10 px-3 py-1.5 rounded-lg border border-primary/20">
          <FolderOpen className="w-4 h-4" />
          <span className="font-medium">Viewing diagrams from: <strong>{currentFolderId}</strong></span>
        </div>
      )}
      
      {diagramArtifacts.length > 1 && (
        <div ref={selectorRef} className="mb-3 mx-4 relative flex-shrink-0 z-50">
          <button
            onClick={() => setShowSelector(!showSelector)}
            className="w-full px-3 py-2 text-sm bg-card border border-border rounded-lg flex items-center justify-between hover:border-primary transition-colors"
          >
            <span className="text-sm font-medium">
              {selectedArtifact ? `${selectedArtifact.type.replace('mermaid_', '').replace(/_/g, ' ')}` : 'Select Diagram'}
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showSelector ? 'rotate-180' : ''}`} />
          </button>
          {showSelector && (
            <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {diagramArtifacts.map((artifact) => (
                <button
                  key={artifact.id}
                  onClick={() => {
                    setSelectedArtifactId(artifact.id)
                    setShowSelector(false)
                  }}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-primary/10 transition-colors ${
                    selectedArtifactId === artifact.id ? 'bg-primary/20 font-medium' : ''
                  }`}
                >
                  {artifact.type.replace('mermaid_', '').replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {diagramArtifacts.length === 0 ? (
        <div className="flex-1 h-full min-h-[80vh] mx-1.5 mb-2 flex items-center justify-center border border-border rounded-xl bg-muted/30">
          <div className="text-center">
            <FileCode className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-lg font-medium text-muted-foreground mb-2">No Mermaid diagrams available</p>
            <p className="text-sm text-muted-foreground">
              Generate a Mermaid diagram first to use the Canvas editor
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 h-[calc(100vh-110px)] min-h-[calc(100vh-110px)] mx-1.5 mb-2 border border-border rounded-xl overflow-hidden bg-card shadow-lg">
          <EnhancedDiagramEditor selectedArtifactId={selectedArtifactId} />
        </div>
      )}
    </div>
  )
}
