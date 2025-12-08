import { useState, useEffect, useMemo } from 'react'
import { GitBranch, GitCommit, RefreshCw, FileText, Clock, CheckCircle, ChevronRight, Loader2, ArrowUpCircle, Eye, Plus, Minus, ArrowLeftRight, CheckSquare, Square } from 'lucide-react'
import api from '../services/api'
import { useUIStore } from '../stores/uiStore'
import { useArtifactStore } from '../stores/artifactStore'

interface VersionInfo {
  version: number
  artifact_id: string
  artifact_type: string
  content: string
  metadata: {
    model_used?: string
    validation_score?: number
    [key: string]: any
  }
  created_at: string
  is_current: boolean
}

interface AllVersionsResponse {
  versions_by_type: Record<string, VersionInfo[]>
  artifact_types: string[]
  total_versions: number
  total_artifacts: number
}

interface DiffLine {
  type: 'added' | 'removed' | 'unchanged'
  content: string
  lineNumber: number
}

export default function VersionControl() {
  const [allVersions, setAllVersions] = useState<AllVersionsResponse | null>(null)
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null)
  const [selectedVersion, setSelectedVersion] = useState<VersionInfo | null>(null)
  
  // Multi-select for comparison
  const [compareSelection, setCompareSelection] = useState<VersionInfo[]>([])
  const [showDiff, setShowDiff] = useState(false)
  
  const [isLoading, setIsLoading] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { addNotification } = useUIStore()
  const { updateArtifact } = useArtifactStore()

  useEffect(() => {
    loadAllVersions()
  }, [])

  const loadAllVersions = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.get<AllVersionsResponse>('/api/versions/all')
      setAllVersions(response.data)
      
      if (response.data.artifact_types.length > 0 && !selectedType) {
        setSelectedType(response.data.artifact_types[0])
      }
    } catch (err: any) {
      console.error('Failed to load versions:', err)
      setError(err?.response?.data?.detail || 'Failed to load versions')
    } finally {
      setIsLoading(false)
    }
  }

  const formatArtifactType = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }

  const getVersionsForType = (type: string): VersionInfo[] => {
    return allVersions?.versions_by_type[type] || []
  }

  const getUniqueArtifacts = (type: string): string[] => {
    const versions = getVersionsForType(type)
    return [...new Set(versions.map(v => v.artifact_id))]
  }

  const getVersionsForArtifact = (artifactId: string): VersionInfo[] => {
    if (!selectedType || !allVersions) return []
    return allVersions.versions_by_type[selectedType]?.filter(v => v.artifact_id === artifactId) || []
  }

  // Compute diff between two versions
  const computeDiff = useMemo((): DiffLine[] => {
    if (compareSelection.length !== 2) return []
    
    // Sort by version number to ensure intuitive diff (old -> new)
    const sorted = [...compareSelection].sort((a, b) => a.version - b.version)
    const [vOld, vNew] = sorted
    
    const oldLines = (vOld.content || '').split('\n')
    const newLines = (vNew.content || '').split('\n')
    const diff: DiffLine[] = []
    
    let lineNum = 1
    const maxLen = Math.max(oldLines.length, newLines.length)
    
    for (let i = 0; i < maxLen; i++) {
      const oldLine = oldLines[i]
      const newLine = newLines[i]
      
      if (oldLine === undefined && newLine !== undefined) {
        diff.push({ type: 'added', content: newLine, lineNumber: lineNum++ })
      } else if (newLine === undefined && oldLine !== undefined) {
        diff.push({ type: 'removed', content: oldLine, lineNumber: lineNum++ })
      } else if (oldLine !== newLine) {
        diff.push({ type: 'removed', content: oldLine || '', lineNumber: lineNum })
        diff.push({ type: 'added', content: newLine || '', lineNumber: lineNum++ })
      } else {
        diff.push({ type: 'unchanged', content: newLine || '', lineNumber: lineNum++ })
      }
    }
    
    return diff
  }, [compareSelection])

  const handleRestoreVersion = async (version: VersionInfo) => {
    if (!confirm(`Restore version ${version.version} as the current version? This will update the artifact in the library.`)) {
      return
    }
    
    setIsRestoring(true)
    try {
      // Call the restore endpoint
      await api.post(`/api/versions/${version.artifact_id}/restore/${version.version}`)
      
      // Update the artifact store with the restored content
      updateArtifact(version.artifact_id, {
        content: version.content,
        score: version.metadata?.validation_score,
        model_used: version.metadata?.model_used
      })
      
      addNotification('success', `Version ${version.version} restored as current`)
      
      // Reload versions to reflect the change
      await loadAllVersions()
    } catch (err: any) {
      console.error('Failed to restore version:', err)
      addNotification('error', err?.response?.data?.detail || 'Failed to restore version')
    } finally {
      setIsRestoring(false)
    }
  }

  const toggleCompareSelect = (version: VersionInfo) => {
    if (compareSelection.some(v => v.version === version.version)) {
      setCompareSelection(prev => prev.filter(v => v.version !== version.version))
    } else {
      if (compareSelection.length >= 2) {
        // Replace the first one (FIFO) or prevent? Let's prevent > 2
        addNotification('warning', 'You can only compare 2 versions at a time')
        return
      }
      setCompareSelection(prev => [...prev, version])
    }
  }

  const startCompare = () => {
    if (compareSelection.length === 2) {
      setShowDiff(true)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading version history...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
          <GitBranch className="w-8 h-8 text-red-500" />
        </div>
        <h3 className="text-lg font-bold text-foreground mb-2">Error Loading Versions</h3>
        <p className="text-muted-foreground mb-4">{error}</p>
        <button
          onClick={loadAllVersions}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
        >
          <RefreshCw className="w-4 h-4 inline mr-2" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 min-h-[400px] h-full">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-primary" />
            Version History
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {allVersions ? `${allVersions.total_versions} versions, ${allVersions.total_artifacts} artifacts` : 'Track versions'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {showDiff && (
            <button
              onClick={() => { setShowDiff(false); setCompareSelection([]) }}
              className="px-3 py-1.5 text-xs bg-muted hover:bg-muted/80 text-foreground rounded-lg flex items-center gap-1"
            >
              <ArrowLeftRight className="w-3 h-3" />
              Exit Compare
            </button>
          )}
          <button
            onClick={loadAllVersions}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs border border-border rounded-lg hover:bg-card flex items-center gap-1 disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Main Content */}
      {!allVersions || allVersions.total_versions === 0 ? (
        <div className="glass-panel rounded-xl p-8 text-center flex-1">
          <GitCommit className="w-12 h-12 mx-auto mb-3 text-muted-foreground/50" />
          <h3 className="font-bold text-foreground mb-1">No Versions Yet</h3>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            Generate artifacts to start tracking version history.
          </p>
        </div>
      ) : showDiff && compareSelection.length === 2 ? (
        /* Diff View */
        <div className="flex-1 flex flex-col min-h-0 glass-panel rounded-xl overflow-hidden">
          <div className="p-3 border-b border-border bg-muted/30 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-4 text-xs">
              <span className="font-bold text-foreground">Diff View</span>
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 bg-red-500/20 text-red-600 rounded font-medium flex items-center gap-1">
                  <Minus className="w-3 h-3" />
                  v{[...compareSelection].sort((a,b) => a.version - b.version)[0].version}
                </span>
                <span className="text-muted-foreground">→</span>
                <span className="px-2 py-1 bg-green-500/20 text-green-600 rounded font-medium flex items-center gap-1">
                  <Plus className="w-3 h-3" />
                  v{[...compareSelection].sort((a,b) => a.version - b.version)[1].version}
                </span>
              </div>
            </div>
            {/* Allow restoring the newer version if not current */}
             {[...compareSelection].sort((a,b) => a.version - b.version)[1].is_current ? (
                <span className="text-xs text-green-600 font-medium px-2 py-1 bg-green-100 rounded flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    Current
                </span>
             ) : (
                <button
                  onClick={() => handleRestoreVersion([...compareSelection].sort((a,b) => a.version - b.version)[1])}
                  disabled={isRestoring}
                  className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1"
                >
                  {isRestoring ? <Loader2 className="w-3 h-3 animate-spin" /> : <ArrowUpCircle className="w-3 h-3" />}
                  Restore v{[...compareSelection].sort((a,b) => a.version - b.version)[1].version}
                </button>
             )}
          </div>
          <div className="flex-1 overflow-auto font-mono text-xs p-2 bg-background/50">
            {computeDiff.map((line, idx) => (
              <div
                key={idx}
                className={`flex ${
                  line.type === 'added' ? 'bg-green-500/10' :
                  line.type === 'removed' ? 'bg-red-500/10' : ''
                }`}
              >
                <span className="w-8 text-right pr-2 text-muted-foreground select-none border-r border-border mr-2 opacity-50">
                  {line.lineNumber}
                </span>
                <span className="w-4 flex-shrink-0 flex items-center justify-center">
                  {line.type === 'added' && <Plus className="w-3 h-3 text-green-500" />}
                  {line.type === 'removed' && <Minus className="w-3 h-3 text-red-500" />}
                </span>
                <span className={`flex-1 whitespace-pre-wrap break-all ${
                  line.type === 'added' ? 'text-green-600' :
                  line.type === 'removed' ? 'text-red-600' : 'text-foreground'
                }`}>
                  {line.content || ' '}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* Normal View - 3 Column Layout */
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 flex-1 min-h-0">
          {/* Left Panel: Artifact Types */}
          <div className="col-span-1 md:col-span-3 glass-panel rounded-xl p-3 flex flex-col min-h-[150px] md:min-h-0">
            <h3 className="text-xs font-bold text-foreground mb-2">Types</h3>
            <div className="flex-1 overflow-y-auto space-y-1">
              {allVersions.artifact_types.map((type) => {
                const count = getVersionsForType(type).length
                return (
                  <button
                    key={type}
                    onClick={() => { setSelectedType(type); setSelectedArtifact(null); setSelectedVersion(null); setCompareSelection([]) }}
                    className={`w-full text-left p-2 rounded-lg text-xs transition-all ${
                      selectedType === type
                        ? 'bg-primary/10 border-primary border'
                        : 'border border-transparent hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-foreground truncate">{formatArtifactType(type)}</span>
                      <ChevronRight className={`w-3 h-3 text-muted-foreground ${selectedType === type ? 'rotate-90' : ''}`} />
                    </div>
                    <p className="text-[10px] text-muted-foreground">{count} version{count !== 1 ? 's' : ''}</p>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Middle Panel: Artifacts */}
          <div className="col-span-1 md:col-span-4 glass-panel rounded-xl p-3 flex flex-col min-h-[150px] md:min-h-0">
            <h3 className="text-xs font-bold text-foreground mb-2">
              {selectedType ? formatArtifactType(selectedType) : 'Select Type'}
            </h3>
            <div className="flex-1 overflow-y-auto space-y-1">
              {selectedType ? (
                getUniqueArtifacts(selectedType).length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-xs">No artifacts</p>
                  </div>
                ) : (
                  getUniqueArtifacts(selectedType).map((artifactId) => {
                    const versions = getVersionsForArtifact(artifactId)
                    const latest = versions[0]
                    return (
                      <button
                        key={artifactId}
                        onClick={() => { setSelectedArtifact(artifactId); setSelectedVersion(null); setCompareSelection([]) }}
                        className={`w-full text-left p-2 rounded-lg border text-xs transition-all ${
                          selectedArtifact === artifactId
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <FileText className="w-3 h-3 text-muted-foreground" />
                          <span className="font-medium text-foreground truncate">
                            {artifactId.length > 25 ? artifactId.slice(0, 25) + '...' : artifactId}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                          <span>{versions.length} version{versions.length !== 1 ? 's' : ''}</span>
                          {latest && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-2.5 h-2.5" />
                              {new Date(latest.created_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </button>
                    )
                  })
                )
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-xs">Select a type</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Versions */}
          <div className="col-span-1 md:col-span-5 glass-panel rounded-xl p-3 flex flex-col min-h-[300px] md:min-h-0">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-foreground">
                {selectedArtifact ? 'Versions' : 'Select Artifact'}
              </h3>
              {compareSelection.length > 0 && (
                <button
                    onClick={startCompare}
                    disabled={compareSelection.length !== 2}
                    className="px-2 py-1 text-[10px] bg-primary text-primary-foreground rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 transition-all"
                >
                    <ArrowLeftRight className="w-3 h-3" />
                    Compare ({compareSelection.length}/2)
                </button>
              )}
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-1.5">
              {selectedArtifact ? (
                getVersionsForArtifact(selectedArtifact).map((version) => {
                  const isSelected = selectedVersion?.version === version.version
                  const isChecked = compareSelection.some(v => v.version === version.version)
                  
                  return (
                    <div
                      key={`${version.artifact_id}-${version.version}`}
                      className={`p-2.5 rounded-lg border text-xs transition-all ${
                        isSelected ? 'border-primary bg-primary/5' :
                        version.is_current ? 'border-green-500/30 bg-green-500/5' :
                        'border-border bg-card/50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                            <button
                                onClick={(e) => { e.stopPropagation(); toggleCompareSelect(version); }}
                                className={`p-0.5 rounded transition-colors ${isChecked ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}
                                title="Select for comparison"
                            >
                                {isChecked ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                            </button>
                            
                            <div className="flex items-center gap-1.5 cursor-pointer" onClick={() => setSelectedVersion(version)}>
                              <GitCommit className="w-3 h-3 text-muted-foreground" />
                              <span className="font-bold text-foreground">v{version.version}</span>
                              {version.is_current && (
                                <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 bg-green-500 text-white rounded-full">
                                  <CheckCircle className="w-2.5 h-2.5" />
                                  Current
                                </span>
                              )}
                            </div>
                        </div>
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(version.created_at).toLocaleString()}
                        </span>
                      </div>
                      
                      <div className="text-[10px] text-muted-foreground mb-2 pl-6">
                        {version.metadata?.model_used && (
                          <span>Model: {version.metadata.model_used.replace('ollama:', '').replace('huggingface:', '')}</span>
                        )}
                        {version.content && (
                          <span className="ml-2">{version.content.length.toLocaleString()} chars</span>
                        )}
                      </div>
                      
                      <div className="flex gap-1.5 pl-6">
                        <button
                          onClick={() => setSelectedVersion(version)}
                          className={`flex-1 px-2 py-1 rounded text-[10px] font-medium flex items-center justify-center gap-1 ${
                            isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted hover:bg-muted/80'
                          }`}
                        >
                          <Eye className="w-3 h-3" />
                          View
                        </button>
                        {!version.is_current && (
                          <button
                            onClick={() => handleRestoreVersion(version)}
                            disabled={isRestoring}
                            className="flex-1 px-2 py-1 rounded bg-green-500/10 hover:bg-green-500/20 text-green-600 text-[10px] font-medium flex items-center justify-center gap-1 disabled:opacity-50"
                          >
                            {isRestoring ? <Loader2 className="w-3 h-3 animate-spin" /> : <ArrowUpCircle className="w-3 h-3" />}
                            Make Current
                          </button>
                        )}
                      </div>
                      
                      {/* Content Preview if selected */}
                      {isSelected && (
                         <div className="mt-2 pl-6 pt-2 border-t border-border/50">
                            <div className="max-h-32 overflow-y-auto bg-muted/30 p-2 rounded text-[10px] font-mono whitespace-pre-wrap">
                                {version.content}
                            </div>
                         </div>
                      )}
                    </div>
                  )
                })
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <GitCommit className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-xs">Select an artifact</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}