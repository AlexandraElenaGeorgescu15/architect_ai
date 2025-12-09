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

          {/* Dropdown - constrained sizing */}
          <div 
            className="absolute right-0 mt-2 bg-card border border-border rounded-xl shadow-2xl z-[100] overflow-hidden flex flex-col"
            style={{
              width: 'min(90vw, 340px)',
              maxHeight: 'min(70vh, 400px)',
            }}
          >
            {/* Header */}
            <div className="p-3 border-b border-border bg-secondary/20 flex-shrink-0">
              <h3 className="font-bold text-foreground text-sm flex items-center gap-2">
                <History className="w-4 h-4" />
                Version History
              </h3>
              <p className="text-xs text-muted-foreground">
                {versions.length} version{versions.length !== 1 ? 's' : ''}
              </p>
            </div>

            {/* Version List */}
            <div className="overflow-y-auto custom-scrollbar flex-1 min-h-0">
              {isLoading ? (
                <div className="p-6 text-center">
                  <RefreshCw className="w-5 h-5 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">Loading...</p>
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {versions.map((version) => (
                    <div
                      key={version.version}
                      className={`p-2 rounded-lg transition-colors cursor-pointer ${
                        version.is_current
                          ? 'bg-primary/10 border border-primary/30'
                          : 'hover:bg-secondary/50 border border-transparent'
                      }`}
                      onClick={() => {
                        if (!version.is_current) {
                          if (confirm(`Restore version ${version.version}?`)) {
                            handleRestore(version.version)
                            setIsOpen(false)
                          }
                        }
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className={`w-6 h-6 rounded flex-shrink-0 flex items-center justify-center text-[10px] font-bold ${
                            version.is_current ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'
                          }`}>
                            {version.is_current ? <Check className="w-3 h-3" /> : `v${version.version}`}
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-semibold text-foreground flex items-center gap-1">
                              v{version.version}
                              {version.is_current && (
                                <span className="text-[9px] px-1 py-0.5 bg-primary/20 text-primary rounded">Current</span>
                              )}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                              {formatDate(version.created_at)}
                            </p>
                          </div>
                        </div>
                        {!version.is_current && (
                          <button
                            className="text-[10px] text-primary hover:underline flex items-center gap-0.5 flex-shrink-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (confirm(`Restore v${version.version}?`)) {
                                handleRestore(version.version)
                                setIsOpen(false)
                              }
                            }}
                          >
                            <RefreshCw className="w-2.5 h-2.5" />
                            Restore
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-2 border-t border-border bg-secondary/10 flex-shrink-0">
              <p className="text-[10px] text-muted-foreground text-center">
                Click to restore
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

