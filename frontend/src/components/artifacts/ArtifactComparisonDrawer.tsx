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
    <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex justify-end">
      <div 
        className="h-full bg-card text-card-foreground border-l border-border flex flex-col shadow-2xl"
        style={{ width: 'min(95vw, 600px)' }}
      >
        {/* Header - compact */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-background/50 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-primary/10">
              <GitBranch className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h3 className="font-bold text-foreground text-sm">Compare Versions</h3>
              <p className="text-xs text-muted-foreground capitalize">
                {artifact.type.replace(/_/g, ' ')}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-1.5 hover:bg-destructive/10 hover:text-destructive rounded-lg transition-colors" 
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar bg-background/30 min-h-0">
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
              <div className="grid grid-cols-2 gap-3">
                {[selected.first, selected.second].map((value, index) => (
                  <div key={index} className="bg-background/50 border border-border rounded-lg p-3 space-y-2">
                    <p className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <span className="w-5 h-5 rounded bg-primary/10 flex items-center justify-center text-[10px] text-primary font-bold">
                        {index + 1}
                      </span>
                      {index === 0 ? 'First' : 'Second'}
                    </p>
                    <select
                      value={value || ''}
                      onChange={(e) =>
                        setSelected((prev) => ({
                          ...prev,
                          [index === 0 ? 'first' : 'second']: Number(e.target.value),
                        }))
                      }
                      className="w-full border border-border rounded-lg px-2 py-1.5 bg-background text-foreground text-xs transition-colors focus:border-primary/50"
                    >
                      <option value="">Select...</option>
                      {versions.map((version) => (
                        <option key={version.version} value={version.version}>
                          v{version.version}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              {comparison && (
                <div className="space-y-3">
                  <div className="bg-primary/5 border border-primary/20 rounded-lg p-2">
                    <div className="flex flex-wrap gap-3 text-xs">
                      <div className="flex items-center gap-1">
                        <span className="text-muted-foreground">Size:</span>
                        <span className="text-foreground font-bold">{comparison.differences.size_diff}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-muted-foreground">Lines:</span>
                        <span className="text-foreground font-bold">{comparison.differences.lines_diff}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-muted-foreground">Match:</span>
                        <span className="text-primary font-bold">
                          {(comparison.differences.similarity * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-3">
                    {[selected.first, selected.second].map((versionNumber, index) => {
                      const version = versions.find((v) => v.version === versionNumber)
                      return (
                        <div key={index} className="border border-border rounded-lg overflow-hidden">
                          <div className="px-2 py-1.5 bg-background/50 border-b border-border flex items-center justify-between">
                            <span className="text-xs font-bold text-foreground">v{versionNumber}</span>
                          </div>
                          <pre className="p-2 text-[10px] whitespace-pre-wrap max-h-40 overflow-y-auto bg-background/30 custom-scrollbar text-foreground font-mono leading-relaxed">
                            {version?.content?.substring(0, 500) || 'No content'}{version?.content && version.content.length > 500 ? '...' : ''}
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

