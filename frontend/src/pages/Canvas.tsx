import { useState, useEffect } from 'react'
import { useArtifactStore } from '../stores/artifactStore'
import { FileCode, Sparkles, ChevronDown } from 'lucide-react'
import EnhancedDiagramEditor from '../components/EnhancedDiagramEditor'

export default function Canvas() {
  const { artifacts } = useArtifactStore()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [showSelector, setShowSelector] = useState(false)
  
  // Only show Mermaid diagrams (exclude HTML)
  const diagramArtifacts = artifacts.filter(a => 
    a.type.startsWith('mermaid_')
  )

  const selectedArtifact = selectedArtifactId 
    ? artifacts.find(a => a.id === selectedArtifactId)
    : diagramArtifacts[0] || null

  useEffect(() => {
    if (diagramArtifacts.length > 0 && !selectedArtifactId) {
      setSelectedArtifactId(diagramArtifacts[0].id)
    }
  }, [diagramArtifacts.length, selectedArtifactId])

  return (
    <div className="h-full overflow-hidden flex flex-col p-4 animate-fade-in-up">
      
      {/* Compact Diagram Selector */}
      {diagramArtifacts.length > 1 && (
        <div className="mb-3 relative flex-shrink-0">
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
            <div className="absolute z-10 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
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
        <div className="flex-1 flex items-center justify-center border border-border rounded-xl bg-muted/30">
          <div className="text-center">
            <FileCode className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-lg font-medium text-muted-foreground mb-2">No Mermaid diagrams available</p>
            <p className="text-sm text-muted-foreground">
              Generate a Mermaid diagram first to use the Canvas editor
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 border border-border rounded-xl overflow-hidden bg-card shadow-lg">
          <EnhancedDiagramEditor selectedArtifactId={selectedArtifactId} />
        </div>
      )}
    </div>
  )
}
