import { useState, useEffect, useMemo } from 'react'
import { GitBranch, GitCommit, GitCompare, FileText, RefreshCw, Eye, AlertCircle, CheckCircle, X } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import api from '../services/api'
import { diffLines, Change } from 'diff'

interface GitStatus {
  is_repo: boolean
  status: string
  files?: Array<{
    file: string
    absolute_path: string
    status: 'tracked' | 'modified' | 'untracked' | 'added' | 'deleted'
    name: string
  }>
}

interface GitDiffResult {
  file_path: string
  absolute_path: string
  is_tracked: boolean
  diff: string
  stats: {
    additions: number
    deletions: number
    files_changed: number
  }
  error?: string
}

export default function VersionControl() {
  const { artifacts } = useArtifactStore()
  const [gitStatus, setGitStatus] = useState<GitStatus | null>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [gitDiff, setGitDiff] = useState<GitDiffResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingDiff, setIsLoadingDiff] = useState(false)
  const [viewMode, setViewMode] = useState<'split' | 'unified'>('split')
  const [baseRef, setBaseRef] = useState<string>('HEAD~1')
  const [activeTab, setActiveTab] = useState<'artifacts' | 'git'>('artifacts')
  const [artifactVersions, setArtifactVersions] = useState<Record<string, any[]>>({}) // artifact_type -> versions
  const [selectedArtifactType, setSelectedArtifactType] = useState<string | null>(null)
  const [isLoadingVersions, setIsLoadingVersions] = useState(false)

  useEffect(() => {
    loadGitStatus()
    loadArtifactVersions()
  }, [artifacts])

  const loadArtifactVersions = async () => {
    setIsLoadingVersions(true)
    try {
      // Group versions by artifact_type instead of artifact_id
      // This way all ERD versions show together, even if they have different artifact_ids
      const versionsByType: Record<string, any[]> = {}
      
      // Get unique artifact types from artifacts
      const artifactTypes = new Set(artifacts.map(a => a.type))
      
      // Load versions for each artifact type
      for (const artifactType of artifactTypes) {
        try {
          console.log(`📋 [VERSION_CONTROL] Loading versions for type: ${artifactType}`)
          const response = await api.get(`/api/versions/by-type/${encodeURIComponent(artifactType)}`)
          console.log(`📋 [VERSION_CONTROL] Got ${response.data?.length || 0} versions for ${artifactType}`)
          if (response.data && response.data.length > 0) {
            versionsByType[artifactType] = response.data
            console.log(`✅ [VERSION_CONTROL] Loaded ${response.data.length} versions for ${artifactType}`)
          } else {
            console.log(`⚠️ [VERSION_CONTROL] No versions returned for ${artifactType}, trying fallback...`)
            // Try loading by individual artifact IDs as fallback
            const artifactsOfType = artifacts.filter(a => a.type === artifactType)
            for (const artifact of artifactsOfType) {
              try {
                const response = await api.get(`/api/versions/${artifact.id}`)
                if (response.data && response.data.length > 0) {
                  if (!versionsByType[artifactType]) {
                    versionsByType[artifactType] = []
                  }
                  // Add artifact_id to each version for reference
                  const versionsWithId = response.data.map((v: any) => ({
                    ...v,
                    artifact_id: artifact.id
                  }))
                  versionsByType[artifactType].push(...versionsWithId)
                }
              } catch (err) {
                // Artifact has no versions yet
                continue
              }
            }
          }
        } catch (error: any) {
          console.error(`❌ [VERSION_CONTROL] Error loading versions for ${artifactType}:`, error)
          // Try loading by individual artifact IDs as fallback
          const artifactsOfType = artifacts.filter(a => a.type === artifactType)
          for (const artifact of artifactsOfType) {
            try {
              const response = await api.get(`/api/versions/${artifact.id}`)
              if (response.data && response.data.length > 0) {
                if (!versionsByType[artifactType]) {
                  versionsByType[artifactType] = []
                }
                // Add artifact_id to each version for reference
                const versionsWithId = response.data.map((v: any) => ({
                  ...v,
                  artifact_id: artifact.id
                }))
                versionsByType[artifactType].push(...versionsWithId)
              }
            } catch (err) {
              // Artifact has no versions yet
              continue
            }
          }
        }
      }
      
      // Convert to artifact_id-based map for compatibility with existing UI
      // Group by artifact_type, but use artifact_type as the key
      const versionsMap: Record<string, any[]> = {}
      for (const [artifactType, versions] of Object.entries(versionsByType)) {
        // Use artifact_type as key, but we'll need to update the UI to handle this
        // For now, also create entries for each artifact_id
        for (const version of versions) {
          const artifactId = version.artifact_id || artifactType
          if (!versionsMap[artifactId]) {
            versionsMap[artifactId] = []
          }
          versionsMap[artifactId].push(version)
        }
      }
      
      // Also create a type-based mapping for easier access
      setArtifactVersions(versionsByType as any)
    } catch (error) {
      console.error('Failed to load artifact versions:', error)
    } finally {
      setIsLoadingVersions(false)
    }
  }

  const loadGitStatus = async () => {
    setIsLoading(true)
    try {
      const response = await api.get('/api/git/status')
      setGitStatus(response.data)
    } catch (error) {
      console.error('Failed to load git status:', error)
      setGitStatus({
        is_repo: false,
        status: 'error'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const loadGitDiff = async (filePath: string) => {
    setIsLoadingDiff(true)
    setSelectedFile(filePath)
    try {
      const response = await api.get('/api/git/diff', {
        params: {
          file_path: filePath,
          base_ref: baseRef || undefined
        }
      })
      setGitDiff(response.data)
    } catch (error: any) {
      console.error('Failed to load git diff:', error)
      setGitDiff({
        file_path: filePath,
        absolute_path: filePath,
        is_tracked: false,
        diff: '',
        stats: { additions: 0, deletions: 0, files_changed: 0 },
        error: error.response?.data?.detail || 'Failed to load diff'
      })
    } finally {
      setIsLoadingDiff(false)
    }
  }

  const parsedDiff = useMemo(() => {
    if (!gitDiff?.diff) return []
    
    // Parse git diff format
    const lines = gitDiff.diff.split('\n')
    const changes: Array<{ type: 'context' | 'added' | 'removed'; line: string; lineNumber?: number }> = []
    
    let oldLineNum = 0
    let newLineNum = 0
    
    for (const line of lines) {
      if (line.startsWith('@@')) {
        // Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
        const match = line.match(/@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/)
        if (match) {
          oldLineNum = parseInt(match[1]) - 1
          newLineNum = parseInt(match[3]) - 1
        }
        continue
      }
      
      if (line.startsWith('+') && !line.startsWith('+++')) {
        newLineNum++
        changes.push({ type: 'added', line: line.substring(1), lineNumber: newLineNum })
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        oldLineNum++
        changes.push({ type: 'removed', line: line.substring(1), lineNumber: oldLineNum })
      } else if (line.startsWith(' ')) {
        oldLineNum++
        newLineNum++
        changes.push({ type: 'context', line: line.substring(1), lineNumber: newLineNum })
      }
    }
    
    return changes
  }, [gitDiff])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'tracked':
        return 'text-green-500 bg-green-500/10'
      case 'modified':
        return 'text-yellow-500 bg-yellow-500/10'
      case 'untracked':
        return 'text-gray-500 bg-gray-500/10'
      case 'added':
        return 'text-blue-500 bg-blue-500/10'
      case 'deleted':
        return 'text-red-500 bg-red-500/10'
      default:
        return 'text-muted-foreground bg-muted'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'tracked':
        return <CheckCircle className="w-4 h-4" />
      case 'modified':
        return <AlertCircle className="w-4 h-4" />
      case 'untracked':
        return <FileText className="w-4 h-4" />
      case 'added':
        return <GitCommit className="w-4 h-4" />
      case 'deleted':
        return <X className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  if (!gitStatus) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading git status...</p>
        </div>
      </div>
    )
  }

  if (!gitStatus.is_repo) {
    return (
      <div className="glass-panel rounded-2xl p-8 text-center">
        <div className="w-16 h-16 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-4">
          <GitBranch className="w-8 h-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-bold text-foreground mb-2">Not a Git Repository</h3>
        <p className="text-muted-foreground mb-4">
          This directory is not a git repository. Initialize git to track artifact changes.
        </p>
        <button
          onClick={loadGitStatus}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
        >
          <RefreshCw className="w-4 h-4 inline mr-2" />
          Refresh
        </button>
      </div>
    )
  }

  const artifactFiles = gitStatus.files || []

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
              <GitBranch className="w-5 h-5 text-primary" />
            </div>
            Version Control
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Track and compare artifact versions
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Tab Switcher */}
          <div className="flex gap-1 bg-muted rounded-lg p-1">
            <button
              onClick={() => setActiveTab('artifacts')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'artifacts'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Artifact Versions
            </button>
            <button
              onClick={() => setActiveTab('git')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'git'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Git Diff
            </button>
          </div>
          <button
            onClick={() => {
              if (activeTab === 'artifacts') {
                loadArtifactVersions()
              } else {
                loadGitStatus()
              }
            }}
            disabled={isLoading || isLoadingVersions}
            className="px-4 py-2 border border-border rounded-lg hover:bg-card flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${(isLoading || isLoadingVersions) ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {activeTab === 'artifacts' ? (
        /* Artifact Versions View */
        <div className="grid grid-cols-1 lg:grid-cols-[1fr,1fr] gap-6 flex-1 min-h-0">
          {/* Left: Artifact List */}
          <div className="glass-panel rounded-2xl p-6 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Artifacts</h3>
              <span className="text-sm text-muted-foreground">
                {Object.keys(artifactVersions).length} artifacts with versions
              </span>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2">
              {isLoadingVersions ? (
                <div className="text-center py-8">
                  <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
                  <p className="text-muted-foreground">Loading versions...</p>
                </div>
              ) : Object.keys(artifactVersions).length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <GitCompare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>No artifact versions found</p>
                  <p className="text-xs mt-2">Generate artifacts to see version history</p>
                </div>
              ) : (
                // Group artifacts by type and show versions per type
                Array.from(new Set(artifacts.map(a => a.type)))
                  .filter(artifactType => artifactVersions[artifactType] && artifactVersions[artifactType].length > 0)
                  .map((artifactType) => {
                    const versions = artifactVersions[artifactType] || []
                    const currentVersion = versions.find((v: any) => v.is_current) || versions[0]
                    return (
                      <button
                        key={artifactType}
                        onClick={() => setSelectedArtifactType(artifactType)}
                        className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                          selectedArtifactType === artifactType
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                              <span className="font-medium text-foreground truncate">
                                {artifactType.replace(/_/g, ' ')}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {versions.length} version{versions.length !== 1 ? 's' : ''} across {new Set(versions.map((v: any) => v.artifact_id)).size} artifact{new Set(versions.map((v: any) => v.artifact_id)).size !== 1 ? 's' : ''}
                            </p>
                          </div>
                          <div className="px-2 py-1 rounded text-xs font-medium bg-primary/20 text-primary">
                            v{currentVersion?.version || versions.length}
                          </div>
                        </div>
                      </button>
                    )
                  })
              )}
            </div>
          </div>

          {/* Right: Version List */}
          <div className="glass-panel rounded-2xl p-6 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Versions</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2">
              {selectedArtifactType && artifactVersions[selectedArtifactType] ? (
                artifactVersions[selectedArtifactType]
                  .sort((a: any, b: any) => {
                    // Sort by created_at descending (newest first)
                    const dateA = new Date(a.created_at || 0).getTime()
                    const dateB = new Date(b.created_at || 0).getTime()
                    return dateB - dateA
                  })
                  .map((version: any, index: number) => (
                    <div
                      key={`${version.artifact_id}-${version.version}-${index}`}
                      className={`p-4 rounded-lg border-2 ${
                        version.is_current
                          ? 'border-primary bg-primary/10'
                          : 'border-border bg-card/50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-foreground">
                          Version {version.version}
                          {version.is_current && (
                            <span className="ml-2 text-xs px-2 py-0.5 bg-primary text-primary-foreground rounded">
                              Current
                            </span>
                          )}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(version.created_at).toLocaleString()}
                        </span>
                      </div>
                      {version.artifact_id && (
                        <p className="text-xs text-muted-foreground mb-1">
                          Artifact ID: <span className="font-mono">{version.artifact_id}</span>
                        </p>
                      )}
                      {version.metadata?.model_used && (
                        <p className="text-xs text-muted-foreground mb-2">
                          Model: {version.metadata.model_used.replace('ollama:', '').replace('huggingface:', '')}
                        </p>
                      )}
                      {version.metadata?.validation_score !== undefined && (
                        <p className="text-xs text-muted-foreground">
                          Score: {version.metadata.validation_score}/100
                        </p>
                      )}
                    </div>
                  ))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <GitCommit className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>Select an artifact type to view versions</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Git Diff View */
        <div className="grid grid-cols-1 lg:grid-cols-[1fr,1fr] gap-6 flex-1 min-h-0">
          {/* Left: Artifact List */}
          <div className="glass-panel rounded-2xl p-6 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Artifacts</h3>
              <span className="text-sm text-muted-foreground">
                {artifactFiles.length} files
              </span>
            </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2">
            {artifactFiles.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No artifact files found in outputs directory</p>
              </div>
            ) : (
              artifactFiles.map((file, index) => (
                <button
                  key={index}
                  onClick={() => loadGitDiff(file.absolute_path)}
                  className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                    selectedFile === file.absolute_path
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        <span className="font-medium text-foreground truncate">{file.name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{file.file}</p>
                    </div>
                    <div className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 ${getStatusColor(file.status)}`}>
                      {getStatusIcon(file.status)}
                      <span className="capitalize">{file.status}</span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right: Git Diff Viewer */}
        <div className="glass-panel rounded-2xl p-6 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-foreground">Git Diff</h3>
            {gitDiff && (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={baseRef}
                  onChange={(e) => setBaseRef(e.target.value)}
                  placeholder="HEAD~1"
                  className="px-3 py-1 text-sm border border-border rounded-lg bg-background text-foreground w-32"
                />
                <div className="flex items-center gap-1 bg-secondary/50 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('split')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      viewMode === 'split'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Split
                  </button>
                  <button
                    onClick={() => setViewMode('unified')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      viewMode === 'unified'
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    Unified
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-auto custom-scrollbar">
            {isLoadingDiff ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
                  <p className="text-muted-foreground">Loading diff...</p>
                </div>
              </div>
            ) : !selectedFile ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <GitCompare className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>Select an artifact to view its git diff</p>
                </div>
              </div>
            ) : gitDiff?.error ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <AlertCircle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
                  <p className="text-foreground font-medium mb-1">Error loading diff</p>
                  <p className="text-sm text-muted-foreground">{gitDiff.error}</p>
                </div>
              </div>
            ) : gitDiff && gitDiff.diff ? (
              <>
                {/* Stats Bar */}
                <div className="mb-4 p-3 bg-secondary/30 rounded-lg flex items-center gap-6 border border-border">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-sm text-foreground">
                      <span className="font-bold text-green-500">{gitDiff.stats.additions}</span> additions
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-sm text-foreground">
                      <span className="font-bold text-red-500">{gitDiff.stats.deletions}</span> deletions
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {gitDiff.file_path}
                  </div>
                </div>

                {/* Diff Content */}
                {viewMode === 'split' ? (
                  <div className="grid grid-cols-2 gap-0 border border-border rounded-lg overflow-hidden">
                    {/* Left: Old Version */}
                    <div className="bg-red-500/5">
                      <div className="sticky top-0 bg-red-500/10 border-b border-border px-4 py-2 flex items-center gap-2 z-10">
                        <span className="text-sm font-bold text-red-500">Old Version</span>
                      </div>
                      <div className="font-mono text-xs p-4">
                        {parsedDiff.map((change, i) => {
                          if (change.type === 'added') return null
                          return (
                            <div
                              key={i}
                              className={`py-0.5 ${
                                change.type === 'removed'
                                  ? 'bg-red-500/20 text-red-400'
                                  : 'text-muted-foreground'
                              }`}
                            >
                              {change.type === 'removed' && '-'} {change.line}
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Right: New Version */}
                    <div className="bg-green-500/5">
                      <div className="sticky top-0 bg-green-500/10 border-b border-border px-4 py-2 flex items-center gap-2 z-10">
                        <span className="text-sm font-bold text-green-500">New Version</span>
                      </div>
                      <div className="font-mono text-xs p-4">
                        {parsedDiff.map((change, i) => {
                          if (change.type === 'removed') return null
                          return (
                            <div
                              key={i}
                              className={`py-0.5 ${
                                change.type === 'added'
                                  ? 'bg-green-500/20 text-green-400'
                                  : 'text-muted-foreground'
                              }`}
                            >
                              {change.type === 'added' && '+'} {change.line}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Unified View */
                  <div className="font-mono text-xs p-4 bg-background border border-border rounded-lg">
                    {parsedDiff.map((change, i) => (
                      <div
                        key={i}
                        className={`py-0.5 ${
                          change.type === 'added'
                            ? 'bg-green-500/20 text-green-400'
                            : change.type === 'removed'
                            ? 'bg-red-500/20 text-red-400'
                            : 'text-muted-foreground'
                        }`}
                      >
                        {change.type === 'added' && '+ '}
                        {change.type === 'removed' && '- '}
                        {change.type === 'context' && '  '}
                        {change.line}
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <GitCompare className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No changes detected</p>
                </div>
              </div>
            )}
          </div>
        </div>
        </div>
      )}
    </div>
  )
}

