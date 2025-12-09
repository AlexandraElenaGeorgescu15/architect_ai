import { useState, useEffect } from 'react'
import { History, ChevronDown, RefreshCw, GitCompare, Check, Clock } from 'lucide-react'
import api from '../../services/api'

interface Version {
  version: number
  artifact_id: string
  artifact_type: string
  content: string
  metadata: any
  created_at: string
  is_current: boolean
}

interface VersionSelectorProps {
  artifactId: string
  currentContent: string
  onVersionRestore: (content: string, version: number) => void
}

export default function VersionSelector({ artifactId, currentContent, onVersionRestore }: VersionSelectorProps) {
  const [versions, setVersions] = useState<Version[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const [compareMode, setCompareMode] = useState(false)

  useEffect(() => {
    loadVersions()
  }, [artifactId])

  const loadVersions = async () => {
    setIsLoading(true)
    try {
      const response = await api.get(`/api/versions/${artifactId}`)
      // Sort by version number descending (newest first)
      const sortedVersions = [...response.data].sort((a: Version, b: Version) => b.version - a.version)
      setVersions(sortedVersions)
      
      // Set current version
      const current = sortedVersions.find((v: Version) => v.is_current)
      if (current) {
        setSelectedVersion(current.version)
      }
    } catch (error) {
      // No versions yet or error loading
      setVersions([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleRestore = async (version: number) => {
    try {
      // API endpoint: POST /api/versions/{artifact_id}/restore/{version_number}
      const response = await api.post(`/api/versions/${artifactId}/restore/${version}`)
      if (response.data) {
        // Reload versions and notify parent
        await loadVersions()
        // Use the restored content from the API response (which is the new version)
        onVersionRestore(response.data.content, response.data.version)
      }
    } catch (error) {
      console.error('Failed to restore version:', error)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (versions.length === 0) {
    return null // No versions yet
  }

  const currentVersion = versions.find(v => v.is_current)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-card transition-colors text-foreground"
      >
        <History className="w-4 h-4" />
        <span>
          Version {currentVersion?.version || 'N/A'} of {versions.length}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute right-0 mt-2 w-96 bg-card border border-border rounded-xl shadow-2xl z-50 max-h-96 overflow-hidden flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-border bg-secondary/20">
              <h3 className="font-bold text-foreground flex items-center gap-2">
                <History className="w-5 h-5" />
                Version History
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                {versions.length} version{versions.length !== 1 ? 's' : ''} available
              </p>
            </div>

            {/* Version List */}
            <div className="overflow-y-auto custom-scrollbar flex-1">
              {isLoading ? (
                <div className="p-8 text-center">
                  <RefreshCw className="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Loading versions...</p>
                </div>
              ) : (
                <div className="p-2">
                  {versions.map((version) => (
                    <div
                      key={version.version}
                      className={`p-3 rounded-lg mb-2 transition-colors cursor-pointer ${
                        version.is_current
                          ? 'bg-primary/10 border border-primary/30'
                          : 'hover:bg-secondary/50 border border-transparent'
                      }`}
                      onClick={() => {
                        if (!version.is_current) {
                          if (confirm(`Restore version ${version.version}? This will create a new version with this content.`)) {
                            handleRestore(version.version)
                            setIsOpen(false)
                          }
                        }
                      }}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                            version.is_current ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'
                          }`}>
                            {version.is_current ? (
                              <Check className="w-4 h-4" />
                            ) : (
                              <span className="text-xs font-bold">v{version.version}</span>
                            )}
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-foreground">
                              Version {version.version}
                              {version.is_current && (
                                <span className="ml-2 text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">
                                  Current
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {formatDate(version.created_at)}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Metadata */}
                      {version.metadata && (
                        <div className="mt-2 space-y-1">
                          {version.metadata.restored_from && (
                            <p className="text-xs">
                              <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-500 rounded">
                                ↩ Restored from v{version.metadata.restored_from}
                              </span>
                            </p>
                          )}
                          {version.metadata.model_used && (
                            <p className="text-xs text-muted-foreground">
                              Model: <span className="text-foreground">{version.metadata.model_used.replace('ollama:', '').replace('gemini:', '')}</span>
                            </p>
                          )}
                          {version.metadata.validation_score !== undefined && (
                            <p className="text-xs text-muted-foreground">
                              Score: <span className={`font-bold ${
                                version.metadata.validation_score >= 80 ? 'text-green-500' :
                                version.metadata.validation_score >= 60 ? 'text-yellow-500' :
                                'text-red-500'
                              }`}>{version.metadata.validation_score.toFixed(1)}%</span>
                            </p>
                          )}
                          {version.metadata.update_type && (
                            <p className="text-xs text-muted-foreground">
                              Type: <span className="text-foreground">{version.metadata.update_type}</span>
                            </p>
                          )}
                        </div>
                      )}

                      {!version.is_current && (
                        <div className="mt-2 pt-2 border-t border-border/50">
                          <button
                            className="text-xs text-primary hover:underline flex items-center gap-1"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (confirm(`Restore version ${version.version}?`)) {
                                handleRestore(version.version)
                                setIsOpen(false)
                              }
                            }}
                          >
                            <RefreshCw className="w-3 h-3" />
                            Restore this version
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-border bg-secondary/10">
              <p className="text-xs text-muted-foreground text-center">
                💡 Click any version to restore it
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

