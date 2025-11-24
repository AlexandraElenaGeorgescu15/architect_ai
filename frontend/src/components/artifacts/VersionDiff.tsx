import { useState, useEffect, useMemo } from 'react'
import { GitCompare, X, ChevronLeft, ChevronRight, Eye, Code } from 'lucide-react'
import api from '../../services/api'
import { diffLines, Change } from 'diff'

interface Version {
  version: number
  artifact_id: string
  artifact_type: string
  content: string
  metadata: any
  created_at: string
  is_current: boolean
}

interface VersionDiffProps {
  artifactId: string
  version1: number
  version2: number
  onClose: () => void
}

export default function VersionDiff({ artifactId, version1, version2, onClose }: VersionDiffProps) {
  const [v1Data, setV1Data] = useState<Version | null>(null)
  const [v2Data, setV2Data] = useState<Version | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split')

  useEffect(() => {
    loadVersions()
  }, [artifactId, version1, version2])

  const loadVersions = async () => {
    setIsLoading(true)
    try {
      const [resp1, resp2] = await Promise.all([
        api.get(`/api/versions/${artifactId}/${version1}`),
        api.get(`/api/versions/${artifactId}/${version2}`)
      ])
      setV1Data(resp1.data)
      setV2Data(resp2.data)
    } catch (error) {
      console.error('Failed to load versions for comparison:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const diff = useMemo(() => {
    if (!v1Data || !v2Data) return []
    return diffLines(v1Data.content, v2Data.content)
  }, [v1Data, v2Data])

  const stats = useMemo(() => {
    if (!diff.length) return { additions: 0, deletions: 0, unchanged: 0 }
    
    let additions = 0
    let deletions = 0
    let unchanged = 0

    diff.forEach((change: Change) => {
      if (change.added) {
        additions += change.count || 0
      } else if (change.removed) {
        deletions += change.count || 0
      } else {
        unchanged += change.count || 0
      }
    })

    return { additions, deletions, unchanged }
  }, [diff])

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-card border border-border rounded-2xl p-8 text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading comparison...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 overflow-hidden flex items-center justify-center p-4">
      {/* Main container */}
      <div className="bg-card border border-border rounded-2xl shadow-2xl max-w-7xl w-full h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between bg-secondary/20">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <GitCompare className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Version Comparison</h2>
              <p className="text-sm text-muted-foreground">
                Comparing v{version1} with v{version2}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex items-center gap-2 bg-secondary/50 rounded-lg p-1">
              <button
                onClick={() => setViewMode('split')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  viewMode === 'split'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Split
              </button>
              <button
                onClick={() => setViewMode('unified')}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  viewMode === 'unified'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                Unified
              </button>
            </div>

            <button
              onClick={onClose}
              className="w-10 h-10 rounded-lg hover:bg-secondary/50 flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="px-6 py-3 border-b border-border bg-secondary/10 flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-sm text-foreground">
              <span className="font-bold text-green-500">{stats.additions}</span> additions
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <span className="text-sm text-foreground">
              <span className="font-bold text-red-500">{stats.deletions}</span> deletions
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-gray-400"></div>
            <span className="text-sm text-foreground">
              <span className="font-bold">{stats.unchanged}</span> unchanged
            </span>
          </div>
        </div>

        {/* Diff Content */}
        <div className="flex-1 overflow-auto custom-scrollbar">
          {viewMode === 'split' ? (
            <div className="grid grid-cols-2 h-full">
              {/* Left: Version 1 */}
              <div className="border-r border-border">
                <div className="sticky top-0 bg-red-500/10 border-b border-border px-4 py-2 flex items-center gap-2 z-10">
                  <ChevronLeft className="w-4 h-4 text-red-500" />
                  <span className="text-sm font-bold text-red-500">Version {version1}</span>
                  <span className="text-xs text-muted-foreground">
                    {v1Data && new Date(v1Data.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="font-mono text-sm">
                  {diff.map((change: Change, i: number) => {
                    if (change.added) return null
                    return (
                      <div
                        key={i}
                        className={`px-4 py-0.5 ${
                          change.removed ? 'bg-red-500/20 text-red-400' : 'text-muted-foreground'
                        }`}
                      >
                        {change.value.split('\n').map((line, j) => (
                          <div key={j} className="whitespace-pre-wrap break-all">
                            {change.removed && '-'} {line}
                          </div>
                        ))}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Right: Version 2 */}
              <div>
                <div className="sticky top-0 bg-green-500/10 border-b border-border px-4 py-2 flex items-center gap-2 z-10">
                  <ChevronRight className="w-4 h-4 text-green-500" />
                  <span className="text-sm font-bold text-green-500">Version {version2}</span>
                  <span className="text-xs text-muted-foreground">
                    {v2Data && new Date(v2Data.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="font-mono text-sm">
                  {diff.map((change: Change, i: number) => {
                    if (change.removed) return null
                    return (
                      <div
                        key={i}
                        className={`px-4 py-0.5 ${
                          change.added ? 'bg-green-500/20 text-green-400' : 'text-muted-foreground'
                        }`}
                      >
                        {change.value.split('\n').map((line, j) => (
                          <div key={j} className="whitespace-pre-wrap break-all">
                            {change.added && '+'} {line}
                          </div>
                        ))}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          ) : (
            /* Unified View */
            <div className="font-mono text-sm p-4">
              {diff.map((change: Change, i: number) => (
                <div
                  key={i}
                  className={`px-2 py-0.5 rounded ${
                    change.added
                      ? 'bg-green-500/20 text-green-400'
                      : change.removed
                      ? 'bg-red-500/20 text-red-400'
                      : 'text-muted-foreground'
                  }`}
                >
                  {change.value.split('\n').map((line, j) => (
                    <div key={j} className="whitespace-pre-wrap break-all">
                      {change.added && '+ '}
                      {change.removed && '- '}
                      {!change.added && !change.removed && '  '}
                      {line}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

