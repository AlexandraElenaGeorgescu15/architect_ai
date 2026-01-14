import { useState, useEffect, useRef } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { useArtifactStore } from '../stores/artifactStore'
import { useDiagramStore } from '../stores/diagramStore'
import { FileCode, Sparkles, ChevronDown } from 'lucide-react'
import EnhancedDiagramEditor from '../components/EnhancedDiagramEditor'

export default function Canvas() {
  const { artifacts } = useArtifactStore()
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
  
  // Only show Mermaid diagrams (exclude HTML)
  const diagramArtifacts = artifacts
    .filter(a => a.type.startsWith('mermaid_'))
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))

  const selectedArtifact = selectedArtifactId 
    ? artifacts.find(a => a.id === selectedArtifactId)
    : (targetType
        ? diagramArtifacts.find(a => a.type === targetType) || diagramArtifacts[0] || null
        : diagramArtifacts[0] || null)

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
    
    if (initialId) {
      setSelectedArtifactId(initialId)
    }
    if (initialType) {
      setTargetType(initialType)
    }
    
    // Log for debugging
    console.debug('[Canvas] Navigation state:', { initialId, initialType, state })
  }, [location.state, searchParams])

  useEffect(() => {
    // If we have a target type but the id isn't found yet, pick latest of that type when it arrives
    if (!selectedArtifactId && targetType) {
      const latestOfType = diagramArtifacts.find(a => a.type === targetType)
      if (latestOfType) {
        setSelectedArtifactId(latestOfType.id)
        return
      }
    }
    if (diagramArtifacts.length > 0 && !selectedArtifactId) {
      setSelectedArtifactId(diagramArtifacts[0].id)
    }
  }, [diagramArtifacts, selectedArtifactId, targetType])

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
      
      {/* Compact Diagram Selector */}
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
