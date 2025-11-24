import { useState, useEffect } from 'react'
import { useArtifactStore } from '../stores/artifactStore'
import { FileCode, Sparkles } from 'lucide-react'
import EnhancedDiagramEditor from '../components/EnhancedDiagramEditor'

export default function Canvas() {
  const { artifacts } = useArtifactStore()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  
  const diagramArtifacts = artifacts.filter(a => 
    a.type.startsWith('mermaid_') || a.type.startsWith('html_')
  )

  const selectedArtifact = selectedArtifactId 
    ? artifacts.find(a => a.id === selectedArtifactId)
    : diagramArtifacts[0] || null

  useEffect(() => {
    if (diagramArtifacts.length > 0 && !selectedArtifactId) {
      setSelectedArtifactId(diagramArtifacts[0].id)
    }
  }, [diagramArtifacts.length])

  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-6 flex flex-col animate-fade-in-up">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2 text-primary">
          <FileCode className="w-8 h-8 animate-pulse-glow" />
          Canvas - Interactive Diagram Editor
        </h1>
        <p className="text-muted-foreground mt-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary/50" />
          Visual diagram editor with Miro-like features - drag, drop, connect, and edit nodes
        </p>
      </div>
      
      {diagramArtifacts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center border border-border rounded-xl bg-muted/30">
          <div className="text-center">
            <FileCode className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-lg font-medium text-muted-foreground mb-2">No diagrams available</p>
            <p className="text-sm text-muted-foreground">
              Generate a Mermaid or HTML diagram first to use the Canvas editor
            </p>
          </div>
        </div>
          ) : (
            <div className="flex-1 border border-border rounded-xl overflow-hidden bg-card shadow-lg">
              <EnhancedDiagramEditor />
            </div>
          )}
    </div>
  )
}
