import { useState } from 'react'
import { Artifact } from '../../types'
import { FileCode, ExternalLink, ThumbsUp, ThumbsDown, History, X, Clock, Check, RefreshCw, Loader2 } from 'lucide-react'
import { useArtifactStore } from '../../stores/artifactStore'
import { useUIStore } from '../../stores/uiStore'
import { submitFeedback } from '../../services/feedbackService'
import { regenerateArtifact } from '../../services/generationService'
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

interface ArtifactCardProps {
  artifact: Artifact
  onClick?: () => void
}

export default function ArtifactCard({ artifact, onClick }: ArtifactCardProps) {
  const { setCurrentArtifact, updateArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)
  const [showVersionHistory, setShowVersionHistory] = useState(false)
  const [versions, setVersions] = useState<Version[]>([])
  const [isLoadingVersions, setIsLoadingVersions] = useState(false)
  const [isRestoring, setIsRestoring] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)

  const handleClick = () => {
    setCurrentArtifact(artifact)
    if (onClick) {
      onClick()
    }
  }

  const handleFeedback = async (e: React.MouseEvent, type: 'positive' | 'negative') => {
    e.stopPropagation()
    setIsSubmittingFeedback(true)
    
    try {
      await submitFeedback({
        artifact_id: artifact.id,
        score: type === 'positive' ? 85 : 60,
        feedback_type: type,
      })
      addNotification('success', 
        type === 'positive' 
          ? '👍 Thanks! This feedback will be used for model training.'
          : '👎 Feedback received. This will help improve the model.'
      )
    } catch (error) {
      console.error('Feedback error:', error)
      addNotification('error', 'Failed to submit feedback. Please try again.')
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  const handleRegenerate = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsRegenerating(true)
    
    try {
      addNotification('info', `Regenerating ${artifact.type.replace(/_/g, ' ')}...`)
      
      const response = await regenerateArtifact(artifact.type, {
        temperature: 0.8 // Slightly higher for variation
      })
      
      if (response.job_id) {
        addNotification('success', 'Regeneration started! Check the Studio for progress.')
      }
    } catch (error: any) {
      console.error('Regenerate error:', error)
      addNotification('error', error?.response?.data?.detail || 'Failed to regenerate artifact')
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleVersionHistory = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowVersionHistory(true)
    loadVersions()
  }

  const loadVersions = async () => {
    setIsLoadingVersions(true)
    try {
      // Use the correct endpoint for type-based version lookup
      // Backend has /api/versions/by-type/{artifact_type} for type-based queries
      const response = await api.get(`/api/versions/by-type/${artifact.type}`)
      const sortedVersions = [...response.data].sort((a: Version, b: Version) => b.version - a.version)
      setVersions(sortedVersions)
    } catch (error) {
      // No versions yet or error loading - show empty state
      console.debug('No versions found for artifact type:', artifact.type)
      setVersions([])
    } finally {
      setIsLoadingVersions(false)
    }
  }

  const handleRestoreVersion = async (version: Version) => {
    setIsRestoring(true)
    try {
      const response = await api.post(`/api/versions/${version.artifact_id}/restore/${version.version}`)
      if (response.data) {
        // Update the artifact content in the store
        updateArtifact(artifact.id, { content: response.data.content })
        addNotification('success', `Restored to version ${version.version}`)
        await loadVersions()
      }
    } catch (error) {
      addNotification('error', 'Failed to restore version')
    } finally {
      setIsRestoring(false)
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

  const isMermaid = artifact.type.startsWith('mermaid_')
  const preview = artifact.content.substring(0, 150)

  return (
    <div
      onClick={handleClick}
      className="bg-card border border-border rounded-lg p-4 hover:border-primary transition-colors cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-muted-foreground" />
          <h3 className="font-semibold text-sm capitalize">
            {artifact.type.replace(/_/g, ' ')}
          </h3>
        </div>
        {artifact.score !== undefined && (
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            artifact.score >= 80 ? 'bg-green-500/20 text-green-500' :
            artifact.score >= 60 ? 'bg-yellow-500/20 text-yellow-500' :
            'bg-red-500/20 text-red-500'
          }`}>
            {artifact.score}%
          </span>
        )}
      </div>

      <div className="space-y-2">
        <p className="text-sm text-muted-foreground line-clamp-3">
          {preview}
          {artifact.content.length > 150 && '...'}
        </p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{new Date(artifact.created_at).toLocaleDateString()}</span>
          <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        {/* Model and Attempt Info */}
        {(artifact.model_used || artifact.attempts) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground pt-1 border-t border-border/50">
            {artifact.model_used && (
              <span className="px-2 py-0.5 bg-primary/10 text-primary rounded">
                {artifact.model_used.replace('ollama:', '').replace('huggingface:', '')}
              </span>
            )}
            {artifact.attempts && artifact.attempts.length > 0 && (
              <span className="text-muted-foreground">
                Try {artifact.attempts[artifact.attempts.length - 1].retry + 1} of {artifact.attempts.length}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Feedback Buttons */}
      <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-border">
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => handleFeedback(e, 'positive')}
            disabled={isSubmittingFeedback}
            className="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded-md hover:bg-green-500/20 hover:text-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group/thumb"
            title="This looks good! Will be used for model training"
          >
            <ThumbsUp className="w-3.5 h-3.5 group-hover/thumb:scale-110 transition-transform" />
            <span className="hidden sm:inline">Good</span>
          </button>
          <button
            onClick={(e) => handleFeedback(e, 'negative')}
            disabled={isSubmittingFeedback}
            className="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded-md hover:bg-red-500/20 hover:text-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group/thumb"
            title="Needs improvement - feedback helps training"
          >
            <ThumbsDown className="w-3.5 h-3.5 group-hover/thumb:scale-110 transition-transform" />
            <span className="hidden sm:inline">Improve</span>
          </button>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleRegenerate}
            disabled={isRegenerating}
            className="flex items-center gap-1 px-2 py-1.5 text-xs rounded-md hover:bg-primary/20 hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Regenerate artifact"
          >
            {isRegenerating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            onClick={handleVersionHistory}
            className="flex items-center gap-1 px-2 py-1.5 text-xs rounded-md hover:bg-primary/20 hover:text-primary transition-colors"
            title="View version history"
          >
            <History className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {isMermaid && (
        <div className="mt-2 text-xs text-primary">
          📊 Diagram
        </div>
      )}

      {/* Version History Modal */}
      {showVersionHistory && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            onClick={(e) => {
              e.stopPropagation()
              setShowVersionHistory(false)
            }}
          />
          
          {/* Modal - centered with proper constraints */}
          <div 
            className="fixed z-[101] bg-card border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden"
            style={{
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 'min(90vw, 420px)',
              maxHeight: 'min(80vh, 500px)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-3 border-b border-border flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-primary" />
                <div>
                  <h3 className="font-bold text-foreground text-sm">Version History</h3>
                  <p className="text-xs text-muted-foreground">
                    {artifact.type.replace(/_/g, ' ')}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowVersionHistory(false)}
                className="p-1.5 hover:bg-accent rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-3 min-h-0">
              {isLoadingVersions ? (
                <div className="text-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Loading versions...</p>
                </div>
              ) : versions.length === 0 ? (
                <div className="text-center py-6">
                  <History className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No version history</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Save changes in Canvas to create versions
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {versions.map((version) => (
                    <div
                      key={version.version}
                      className={`p-2 rounded-lg border transition-colors ${
                        version.is_current
                          ? 'bg-primary/10 border-primary/30'
                          : 'border-border hover:border-primary/30 hover:bg-accent/50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className={`w-7 h-7 rounded flex-shrink-0 flex items-center justify-center text-xs font-bold ${
                            version.is_current ? 'bg-primary/20 text-primary' : 'bg-secondary text-muted-foreground'
                          }`}>
                            {version.is_current ? <Check className="w-3.5 h-3.5" /> : `v${version.version}`}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-foreground flex items-center gap-1 flex-wrap">
                              v{version.version}
                              {version.is_current && (
                                <span className="text-[10px] px-1.5 py-0.5 bg-primary/20 text-primary rounded">Current</span>
                              )}
                            </p>
                            <p className="text-[10px] text-muted-foreground">{formatDate(version.created_at)}</p>
                          </div>
                        </div>
                        
                        {!version.is_current && (
                          <button
                            onClick={() => handleRestoreVersion(version)}
                            disabled={isRestoring}
                            className="px-2 py-1 text-[10px] bg-primary/10 text-primary hover:bg-primary/20 rounded flex items-center gap-1 disabled:opacity-50 flex-shrink-0"
                          >
                            <RefreshCw className={`w-3 h-3 ${isRestoring ? 'animate-spin' : ''}`} />
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
            <div className="p-2 border-t border-border bg-secondary/10 text-center flex-shrink-0">
              <p className="text-[10px] text-muted-foreground">
                💡 Click Restore to revert
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

