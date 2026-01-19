import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { GitBranch, GitCommit, RefreshCw, CheckCircle, ChevronRight, Loader2, ArrowUpCircle, Eye, Plus, Minus, ArrowLeftRight, CheckSquare, Square, AlertTriangle, Wand2, Columns, List, FolderOpen } from 'lucide-react'
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
  const [selectedVersion, setSelectedVersion] = useState<VersionInfo | null>(null)
  
  // Multi-select for comparison
  const [compareSelection, setCompareSelection] = useState<VersionInfo[]>([])
  const [showDiff, setShowDiff] = useState(false)
  const [compareViewMode, setCompareViewMode] = useState<'diff' | 'side-by-side'>('diff')
  
  // Refs for synchronized scrolling in side-by-side view
  const leftPanelRef = useRef<HTMLDivElement>(null)
  const rightPanelRef = useRef<HTMLDivElement>(null)
  const isScrollingSynced = useRef(false)
  
  // Synchronized scroll handler
  const handleSyncScroll = useCallback((source: 'left' | 'right') => {
    if (isScrollingSynced.current) return
    isScrollingSynced.current = true
    
    const sourceRef = source === 'left' ? leftPanelRef : rightPanelRef
    const targetRef = source === 'left' ? rightPanelRef : leftPanelRef
    
    if (sourceRef.current && targetRef.current) {
      targetRef.current.scrollTop = sourceRef.current.scrollTop
    }
    
    requestAnimationFrame(() => {
      isScrollingSynced.current = false
    })
  }, [])
  
  const [isLoading, setIsLoading] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)
  const [isMigrating, setIsMigrating] = useState(false)
  const [migrationPreview, setMigrationPreview] = useState<any>(null)
  const [showMigrationPanel, setShowMigrationPanel] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { addNotification } = useUIStore()
  const { currentFolderId } = useArtifactStore()

  useEffect(() => {
    loadAllVersions()
  }, [currentFolderId])

  const loadAllVersions = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Filter versions by folder if one is selected
      const params = currentFolderId ? { folder_id: currentFolderId } : {}
      const response = await api.get<AllVersionsResponse>('/api/versions/all', { params })
      setAllVersions(response.data)
      console.log(`📁 [VERSION_CONTROL] Loaded ${response.data.total_versions} versions for folder: ${currentFolderId || 'all'}`)
      
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
      const response = await api.post(`/api/versions/${version.artifact_id}/restore/${version.version}`)
      const restoredVersion = response.data
      
      // Get all artifacts and find one matching by type (artifact_type)
      // The artifact store uses job_id as 'id', but versions use artifact_type as 'artifact_id'
      const { artifacts, setArtifacts, addArtifact } = useArtifactStore.getState()
      const existingArtifact = artifacts.find(a => a.type === version.artifact_type)
      
      if (existingArtifact) {
        // Update existing artifact
        const updatedArtifacts = artifacts.map(artifact => {
          if (artifact.type === version.artifact_type) {
            return {
              ...artifact,
              content: restoredVersion.content,
              score: restoredVersion.metadata?.validation_score,
              model_used: restoredVersion.metadata?.model_used,
              updatedAt: new Date().toISOString()
            }
          }
          return artifact
        })
        setArtifacts(updatedArtifacts)
        addNotification('success', `Version ${version.version} restored. Artifact "${version.artifact_type}" updated.`)
      } else {
        // Create new artifact from the restored version
        const newArtifact = {
          id: version.artifact_id,
          type: version.artifact_type,
          content: restoredVersion.content,
          score: restoredVersion.metadata?.validation_score,
          model_used: restoredVersion.metadata?.model_used,
          createdAt: restoredVersion.created_at,
          updatedAt: new Date().toISOString()
        }
        addArtifact(newArtifact as any)
        addNotification('success', `Version ${version.version} restored. New artifact "${version.artifact_type}" created.`)
      }
      
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
    // Use composite key (artifact_id + version) to handle both legacy timestamped artifacts (all v1) 
    // and new stable artifacts (v1, v2, v3...)
    if (compareSelection.some(v => v.artifact_id === version.artifact_id && v.version === version.version)) {
      setCompareSelection(prev => prev.filter(v => !(v.artifact_id === version.artifact_id && v.version === version.version)))
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

  const checkMigrationNeeded = async () => {
    try {
      const response = await api.get('/api/versions/migration/preview')
      setMigrationPreview(response.data)
      if (response.data.needs_migration) {
        setShowMigrationPanel(true)
      }
    } catch (err) {
      console.error('Failed to check migration:', err)
    }
  }

  const runMigration = async () => {
    if (!confirm('This will consolidate legacy timestamped artifacts into stable IDs. This action cannot be undone. Continue?')) {
      return
    }
    
    setIsMigrating(true)
    try {
      const response = await api.post('/api/versions/migration/run')
      addNotification('success', `Migration complete: ${response.data.migrated_versions} versions consolidated from ${response.data.artifacts_consolidated} artifacts`)
      setShowMigrationPanel(false)
      setMigrationPreview(null)
      // Reload versions to show updated data
      await loadAllVersions()
    } catch (err: any) {
      console.error('Migration failed:', err)
      addNotification('error', err?.response?.data?.detail || 'Migration failed')
    } finally {
      setIsMigrating(false)
    }
  }

  // Check for legacy data on mount
  useEffect(() => {
    checkMigrationNeeded()
  }, [])

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
      {/* Migration Warning Banner */}
      {migrationPreview?.needs_migration && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-bold text-amber-600 dark:text-amber-400">Legacy Version Data Detected</h4>
            <p className="text-xs text-muted-foreground mt-1">
              You have {Object.keys(migrationPreview.legacy_groups || {}).length} artifact type(s) with timestamped IDs.
              These show as separate v1 entries instead of proper version history.
            </p>
            <button
              onClick={() => setShowMigrationPanel(true)}
              className="mt-2 px-3 py-1.5 text-xs bg-amber-500 text-white rounded-lg hover:bg-amber-600 flex items-center gap-1.5"
            >
              <Wand2 className="w-3 h-3" />
              View & Migrate
            </button>
          </div>
        </div>
      )}

      {/* Migration Panel Modal */}
      {showMigrationPanel && migrationPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border">
              <h3 className="text-lg font-bold text-foreground flex items-center gap-2">
                <Wand2 className="w-5 h-5 text-primary" />
                Migrate Legacy Versions
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Consolidate timestamped artifacts into stable IDs for proper version tracking
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {Object.entries(migrationPreview.legacy_groups || {}).map(([baseType, data]: [string, any]) => (
                <div key={baseType} className="border border-border rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-foreground">{baseType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                    <span className="text-xs px-2 py-1 bg-primary/10 text-primary rounded">
                      {data.total_versions} version{data.total_versions !== 1 ? 's' : ''} → will become v1-v{data.total_versions}
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    {data.artifacts.slice(0, 5).map((artifact: any) => (
                      <div key={artifact.artifact_id} className="flex items-center justify-between">
                        <span className="font-mono truncate max-w-[250px]">{artifact.artifact_id}</span>
                        <span>{artifact.version_count} ver</span>
                      </div>
                    ))}
                    {data.artifacts.length > 5 && (
                      <div className="text-muted-foreground/70">... and {data.artifacts.length - 5} more</div>
                    )}
                  </div>
                </div>
              ))}
              
              {migrationPreview.stable_artifacts?.length > 0 && (
                <div className="border border-green-500/30 bg-green-500/5 rounded-lg p-3">
                  <h4 className="font-bold text-green-600 dark:text-green-400 text-sm mb-1">Already Using Stable IDs ✓</h4>
                  <div className="text-xs text-muted-foreground">
                    {migrationPreview.stable_artifacts.map((a: any) => a.artifact_id).join(', ')}
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-4 border-t border-border flex items-center justify-between">
              <button
                onClick={() => setShowMigrationPanel(false)}
                className="px-4 py-2 text-sm border border-border rounded-lg hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={runMigration}
                disabled={isMigrating}
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
              >
                {isMigrating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Migrating...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    Run Migration
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-primary" />
            Version History
            {currentFolderId && (
              <span className="text-sm font-medium text-primary bg-primary/10 px-2 py-0.5 rounded-md flex items-center gap-1">
                <FolderOpen className="w-3.5 h-3.5" />
                {currentFolderId}
              </span>
            )}
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
        /* Comparison View */
        <div className="flex-1 flex flex-col min-h-0 glass-panel rounded-xl overflow-hidden">
          {/* Header with view toggle */}
          <div className="p-3 border-b border-border bg-muted/30 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-4 text-xs">
              {/* View Mode Toggle */}
              <div className="flex items-center bg-background/50 rounded-lg p-0.5 border border-border">
                <button
                  onClick={() => setCompareViewMode('diff')}
                  className={`px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                    compareViewMode === 'diff' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  title="Unified Diff View"
                >
                  <List className="w-3 h-3" />
                  Diff
                </button>
                <button
                  onClick={() => setCompareViewMode('side-by-side')}
                  className={`px-2 py-1 rounded-md flex items-center gap-1 transition-colors ${
                    compareViewMode === 'side-by-side' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                  title="Side by Side View"
                >
                  <Columns className="w-3 h-3" />
                  Side by Side
                </button>
              </div>
              
              {/* Version labels */}
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
            
            {/* Restore button */}
            {[...compareSelection].sort((a,b) => a.version - b.version)[1].is_current ? (
              <span className="text-xs text-green-600 dark:text-green-400 font-medium px-2 py-1 bg-green-100 dark:bg-green-500/20 rounded flex items-center gap-1">
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
          
          {/* Content Area */}
          {compareViewMode === 'diff' ? (
            /* Unified Diff View */
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
          ) : (
            /* Side by Side View */
            <div className="flex-1 flex min-h-0 overflow-hidden">
              {(() => {
                const sorted = [...compareSelection].sort((a, b) => a.version - b.version)
                const [vOld, vNew] = sorted
                const oldLines = (vOld.content || '').split('\n')
                const newLines = (vNew.content || '').split('\n')
                const maxLines = Math.max(oldLines.length, newLines.length)
                
                return (
                  <>
                    {/* Left Panel - Old Version */}
                    <div className="flex-1 flex flex-col min-w-0 border-r border-border">
                      <div className="p-2 border-b border-border bg-red-500/5 flex items-center gap-2 flex-shrink-0">
                        <Minus className="w-3 h-3 text-red-500" />
                        <span className="text-xs font-bold text-red-600">
                          Version {vOld.version}
                        </span>
                        <span className="text-[10px] text-muted-foreground truncate">
                          {vOld.artifact_id}
                        </span>
                      </div>
                      <div 
                        ref={leftPanelRef}
                        onScroll={() => handleSyncScroll('left')}
                        className="flex-1 overflow-auto font-mono text-xs bg-background/30"
                      >
                        {Array.from({ length: maxLines }).map((_, idx) => {
                          const line = oldLines[idx]
                          const newLine = newLines[idx]
                          const isDifferent = line !== newLine
                          
                          return (
                            <div 
                              key={idx} 
                              className={`flex ${isDifferent && line !== undefined ? 'bg-red-500/10' : ''}`}
                            >
                              <span className="w-8 text-right pr-2 text-muted-foreground select-none border-r border-border opacity-50 flex-shrink-0">
                                {idx + 1}
                              </span>
                              <span className={`flex-1 px-2 whitespace-pre-wrap break-all ${
                                isDifferent && line !== undefined ? 'text-red-600' : 'text-foreground'
                              }`}>
                                {line ?? ''}
                              </span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                    
                    {/* Right Panel - New Version */}
                    <div className="flex-1 flex flex-col min-w-0">
                      <div className="p-2 border-b border-border bg-green-500/5 flex items-center gap-2 flex-shrink-0">
                        <Plus className="w-3 h-3 text-green-500" />
                        <span className="text-xs font-bold text-green-600">
                          Version {vNew.version}
                        </span>
                        <span className="text-[10px] text-muted-foreground truncate">
                          {vNew.artifact_id}
                        </span>
                        {vNew.is_current && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-green-500 text-white rounded">Current</span>
                        )}
                      </div>
                      <div 
                        ref={rightPanelRef}
                        onScroll={() => handleSyncScroll('right')}
                        className="flex-1 overflow-auto font-mono text-xs bg-background/30"
                      >
                        {Array.from({ length: maxLines }).map((_, idx) => {
                          const oldLine = oldLines[idx]
                          const line = newLines[idx]
                          const isDifferent = oldLine !== line
                          
                          return (
                            <div 
                              key={idx} 
                              className={`flex ${isDifferent && line !== undefined ? 'bg-green-500/10' : ''}`}
                            >
                              <span className="w-8 text-right pr-2 text-muted-foreground select-none border-r border-border opacity-50 flex-shrink-0">
                                {idx + 1}
                              </span>
                              <span className={`flex-1 px-2 whitespace-pre-wrap break-all ${
                                isDifferent && line !== undefined ? 'text-green-600' : 'text-foreground'
                              }`}>
                                {line ?? ''}
                              </span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </>
                )
              })()}
            </div>
          )}
        </div>
      ) : (
        /* Normal View - 2 Column Layout (simplified) */
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 flex-1 min-h-0">
          {/* Left Panel: Artifact Types */}
          <div className="col-span-1 md:col-span-4 glass-panel rounded-xl p-3 flex flex-col min-h-[150px] md:min-h-0">
            <h3 className="text-xs font-bold text-foreground mb-2">Artifact Types</h3>
            <div className="flex-1 overflow-y-auto space-y-1">
              {allVersions.artifact_types.map((type) => {
                const versions = getVersionsForType(type)
                const count = versions.length
                const hasSelectedVersion = compareSelection.some(v => v.artifact_type === type)
                const currentVersion = versions.find(v => v.is_current)
                return (
                  <button
                    key={type}
                    onClick={() => { 
                      setSelectedType(type)
                      setSelectedVersion(null)
                    }}
                    className={`w-full text-left p-2.5 rounded-lg text-xs transition-all ${
                      selectedType === type
                        ? 'bg-primary/10 border-primary border'
                        : hasSelectedVersion
                          ? 'border-blue-500/50 bg-blue-500/5 border'
                          : 'border border-transparent hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-foreground">{formatArtifactType(type)}</span>
                      <ChevronRight className={`w-3 h-3 text-muted-foreground transition-transform ${selectedType === type ? 'rotate-90' : ''}`} />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <span>{count} version{count !== 1 ? 's' : ''}</span>
                      {currentVersion && (
                        <span className="text-green-600">v{currentVersion.version} current</span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Right Panel: Versions */}
          <div className="col-span-1 md:col-span-8 glass-panel rounded-xl p-3 flex flex-col min-h-[300px] md:min-h-0">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-foreground">
                {selectedType ? `${formatArtifactType(selectedType)} Versions` : 'Select a Type'}
              </h3>
            </div>
            
            {/* Comparison Selection Bar - Always visible when versions selected */}
            {compareSelection.length > 0 && (
              <div className="mb-3 p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
                    Compare Selection ({compareSelection.length}/2)
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCompareSelection([])}
                      className="text-[10px] text-muted-foreground hover:text-foreground"
                    >
                      Clear
                    </button>
                    <button
                      onClick={startCompare}
                      disabled={compareSelection.length !== 2}
                      className="px-2 py-1 text-[10px] bg-primary text-primary-foreground rounded disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                    >
                      <ArrowLeftRight className="w-3 h-3" />
                      Compare
                    </button>
                  </div>
                </div>
                <div className="space-y-1">
                  {compareSelection.map((v, i) => (
                    <div key={`${v.artifact_id}-${v.version}`} className="flex items-center justify-between text-[10px]">
                      <span className="text-foreground truncate max-w-[200px]">
                        <span className="text-muted-foreground">{i + 1}.</span> {v.artifact_id.length > 20 ? v.artifact_id.slice(0, 20) + '...' : v.artifact_id} <span className="font-bold">v{v.version}</span>
                      </span>
                      <button
                        onClick={() => setCompareSelection(prev => prev.filter(x => !(x.artifact_id === v.artifact_id && x.version === v.version)))}
                        className="text-red-500 hover:text-red-600 ml-2"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="flex-1 overflow-y-auto space-y-1.5">
              {selectedType ? (
                getVersionsForType(selectedType).length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <GitCommit className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-xs">No versions for this type</p>
                  </div>
                ) : [...getVersionsForType(selectedType)].sort((a, b) => b.version - a.version).map((version) => {
                  const isSelected = selectedVersion?.version === version.version
                  const isChecked = compareSelection.some(v => v.artifact_id === version.artifact_id && v.version === version.version)
                  
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
                                <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 bg-green-500 text-white rounded-full dark:bg-green-500/20 dark:text-green-400">
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
                      
                      <div className="text-[10px] text-muted-foreground mb-2 pl-6 flex flex-wrap items-center gap-x-2 gap-y-0.5">
                        {version.metadata?.restored_from && (
                          <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-600 rounded">
                            ↩ restored from v{version.metadata.restored_from}
                          </span>
                        )}
                        {version.metadata?.model_used && (
                          <span>Model: {version.metadata.model_used.replace('ollama:', '').replace('huggingface:', '').replace('gemini:', '')}</span>
                        )}
                        {version.metadata?.validation_score !== undefined && (
                          <span className={`px-1 rounded ${version.metadata.validation_score >= 80 ? 'text-green-600' : version.metadata.validation_score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                            Score: {version.metadata.validation_score.toFixed(1)}%
                          </span>
                        )}
                        {version.content && (
                          <span>{version.content.length.toLocaleString()} chars</span>
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
                  <p className="text-xs mb-2">Select an artifact type to see its versions</p>
                  <p className="text-[10px] text-muted-foreground/70">
                    💡 Use checkboxes to select 2 versions to compare
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}