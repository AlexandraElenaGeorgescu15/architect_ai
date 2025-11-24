import { useEffect, useState } from 'react'
import { X, GitBranch, Loader2 } from 'lucide-react'
import { Artifact } from '../../types'
import { ArtifactVersion, compareVersions, listVersions, VersionComparison } from '../../services/versionService'
import { useUIStore } from '../../stores/uiStore'

interface ArtifactComparisonDrawerProps {
  artifact: Artifact
  isOpen: boolean
  onClose: () => void
}

export default function ArtifactComparisonDrawer({ artifact, isOpen, onClose }: ArtifactComparisonDrawerProps) {
  const [versions, setVersions] = useState<ArtifactVersion[]>([])
  const [selected, setSelected] = useState<{ first?: number; second?: number }>({})
  const [comparison, setComparison] = useState<VersionComparison | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const { addNotification } = useUIStore()

  useEffect(() => {
    if (!isOpen) return
    setIsLoading(true)
    listVersions(artifact.id)
      .then((data) => setVersions(data))
      .catch((error) => {
        // Failed to load versions - show notification
        addNotification('error', 'Failed to load versions')
      })
      .finally(() => setIsLoading(false))
  }, [isOpen, artifact.id, addNotification])

  useEffect(() => {
    if (!selected.first || !selected.second || selected.first === selected.second) {
      setComparison(null)
      return
    }
    setIsLoading(true)
    compareVersions(artifact.id, selected.first, selected.second)
      .then(setComparison)
      .catch((error) => {
        // Failed to compare versions - show notification
        addNotification('error', 'Failed to compare versions')
      })
      .finally(() => setIsLoading(false))
  }, [selected, artifact.id, addNotification])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex justify-end animate-fade-in">
      <div className="w-full max-w-4xl h-full bg-card text-card-foreground border-l-2 border-border flex flex-col shadow-floating animate-fade-in-left">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
              <GitBranch className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-bold text-foreground">Compare Versions</h3>
              <p className="text-xs text-muted-foreground font-medium capitalize">
                {artifact.type.replace(/_/g, ' ')}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 group" 
            aria-label="Close comparison drawer"
          >
            <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar bg-background/30">
          {isLoading && (
            <div className="flex items-center justify-center py-10">
              <div className="flex items-center gap-3 text-primary">
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="font-medium">Loading versions…</span>
              </div>
            </div>
          )}

          {!isLoading && (
            <>
              <div className="grid grid-cols-2 gap-4">
                {[selected.first, selected.second].map((value, index) => (
                  <div key={index} className="glass-panel bg-background/50 border-2 border-border rounded-xl p-5 space-y-3">
                    <p className="text-sm font-bold text-foreground flex items-center gap-2">
                      <span className="w-6 h-6 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-xs text-primary font-bold">
                        {index === 0 ? '1' : '2'}
                      </span>
                      {index === 0 ? 'First version' : 'Second version'}
                    </p>
                    <select
                      value={value || ''}
                      onChange={(e) =>
                        setSelected((prev) => ({
                          ...prev,
                          [index === 0 ? 'first' : 'second']: Number(e.target.value),
                        }))
                      }
                      className="w-full glass-input border-2 border-border rounded-xl px-4 py-3 bg-background text-foreground text-sm font-medium transition-all duration-300 focus:border-primary/50"
                    >
                      <option value="">Select version</option>
                      {versions.map((version) => (
                        <option key={version.version} value={version.version}>
                          v{version.version} · {new Date(version.created_at).toLocaleString()}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              {comparison && (
                <div className="space-y-4 animate-fade-in-up">
                  <div className="glass-panel bg-primary/5 border-2 border-primary/20 rounded-xl p-4">
                    <div className="flex flex-wrap gap-4 text-sm font-medium">
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Size Δ:</span>
                        <span className="text-foreground font-bold">{comparison.differences.size_diff} chars</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Lines Δ:</span>
                        <span className="text-foreground font-bold">{comparison.differences.lines_diff}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">Similarity:</span>
                        <span className="text-primary font-bold">
                          {(comparison.differences.similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    {[selected.first, selected.second].map((versionNumber, index) => {
                      const version = versions.find((v) => v.version === versionNumber)
                      return (
                        <div key={index} className="glass-panel border-2 border-border rounded-xl overflow-hidden">
                          <div className="px-4 py-3 bg-background/50 border-b border-border flex items-center justify-between">
                            <span className="text-sm font-bold text-foreground">v{versionNumber}</span>
                            <span className="text-xs text-muted-foreground font-mono">
                              {version ? new Date(version.created_at).toLocaleString() : ''}
                            </span>
                          </div>
                          <pre className="p-4 text-xs whitespace-pre-wrap max-h-80 overflow-y-auto bg-background/30 custom-scrollbar text-foreground font-mono leading-relaxed">
                            {version?.content || 'No content'}
                          </pre>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

