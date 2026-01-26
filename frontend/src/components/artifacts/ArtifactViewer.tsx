import { useState } from 'react'
import { Artifact } from '../../types'
import { Copy, Download, ThumbsUp, ThumbsDown, Edit2, Eye, Check, GitBranch } from 'lucide-react'
import FeedbackModal from './FeedbackModal'
import { submitFeedback, FeedbackType } from '../../services/feedbackService'
import { useUIStore } from '../../stores/uiStore'
import ArtifactComparisonDrawer from './ArtifactComparisonDrawer'
import VersionSelector from './VersionSelector'

interface ArtifactViewerProps {
  artifact: Artifact
  onUpdate?: (artifact: Artifact) => void
}

export default function ArtifactViewer({ artifact, onUpdate }: ArtifactViewerProps) {
  // Safety check: return early if artifact is not provided
  if (!artifact) {
    return (
      <div className="bg-card border border-border rounded-lg overflow-hidden p-6">
        <p className="text-muted-foreground">No artifact selected</p>
      </div>
    )
  }

  const [isEditing, setIsEditing] = useState(false)
  const [editedContent, setEditedContent] = useState(artifact.content)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [feedbackType, setFeedbackType] = useState<FeedbackType | null>(null)
  const [copied, setCopied] = useState(false)
  const [isComparisonOpen, setComparisonOpen] = useState(false)
  const { addNotification } = useUIStore()

  const isMermaid = artifact?.type?.startsWith('mermaid_') || false
  const isCode = artifact?.type === 'code_prototype' || artifact?.type === 'api_docs'
  const isHTML = artifact?.type?.startsWith('html_') || !!(artifact as any)?.html_content

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content)
      setCopied(true)
      addNotification('success', 'Copied to clipboard!')
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      addNotification('error', 'Failed to copy to clipboard')
    }
  }

  const handleDownload = () => {
    const blob = new Blob([artifact.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact.type}_${artifact.id}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    addNotification('success', 'Download started!')
  }

  const handleSave = () => {
    if (onUpdate) {
      onUpdate({ ...artifact, content: editedContent })
    }
    setIsEditing(false)
    addNotification('success', 'Artifact updated!')
  }

  const handleFeedback = (type: FeedbackType) => {
    setFeedbackType(type)
    setShowFeedbackModal(true)
  }

  const handleSubmitFeedback = async (score: number, notes?: string, correctedContent?: string) => {
    try {
      await submitFeedback({
        artifact_id: artifact.id,
        score,
        notes,
        feedback_type: feedbackType!,
        corrected_content: correctedContent,
      })
      addNotification('success', 'Feedback submitted! Thank you.')
      setShowFeedbackModal(false)
    } catch (error) {
      addNotification('error', 'Failed to submit feedback')
    }
  }

  return (
    <>
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h3 className="font-semibold capitalize">{artifact.type.replace(/_/g, ' ')}</h3>
              <p className="text-sm text-muted-foreground">
                {new Date(artifact.created_at).toLocaleString()}
              </p>
            </div>
            {artifact.score !== undefined && (
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${artifact.score >= 80 ? 'bg-green-500/20 text-green-500' :
                artifact.score >= 60 ? 'bg-yellow-500/20 text-yellow-500' :
                  'bg-red-500/20 text-red-500'
                }`}>
                {artifact.score}%
              </span>
            )}
          </div>

          {/* Model and Attempt Info */}
          {(artifact.model_used || artifact.attempts) && (
            <div className="flex items-center gap-3 text-xs text-muted-foreground px-6 pb-2">
              {artifact.model_used && (
                <span className="px-2 py-1 bg-primary/10 text-primary rounded font-medium">
                  Model: {artifact.model_used.replace('ollama:', '').replace('huggingface:', '')}
                </span>
              )}
              {artifact.attempts && artifact.attempts.length > 0 && (
                <span className="px-2 py-1 bg-secondary text-muted-foreground rounded">
                  Attempt {artifact.attempts[artifact.attempts.length - 1].retry + 1} of {artifact.attempts.length}
                </span>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            {/* Version Selector - use artifact.type as the version key since versions are stored by type */}
            <VersionSelector
              artifactId={artifact.type}
              currentContent={artifact.content}
              onVersionRestore={(content, version) => {
                if (onUpdate) {
                  onUpdate({ ...artifact, content })
                }
                addNotification('success', `Restored to version ${version}`)
              }}
            />

            <div className="flex items-center gap-2 border-l border-border pl-3">
              <button
                onClick={handleCopy}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
                title="Copy to clipboard"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
              <button
                onClick={handleDownload}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
                title="Download"
              >
                <Download className="w-4 h-4" />
              </button>
              <button
                onClick={() => setComparisonOpen(true)}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
                title="Compare versions"
              >
                <GitBranch className="w-4 h-4" />
              </button>
              {isCode && (
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="p-2 hover:bg-accent rounded-lg transition-colors"
                  title={isEditing ? 'View mode' : 'Edit mode'}
                >
                  {isEditing ? (
                    <Eye className="w-4 h-4" />
                  ) : (
                    <Edit2 className="w-4 h-4" />
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {isHTML ? (
            <div className="bg-muted rounded-lg overflow-hidden border border-border">
              <iframe
                srcDoc={(artifact as any).html_content || artifact.content}
                className="w-full h-[600px] border-0"
                title="HTML Preview"
                sandbox="allow-scripts allow-same-origin allow-forms"
              />
            </div>
          ) : isMermaid ? (
            <div className="bg-muted rounded-lg p-4 overflow-auto">
              <pre className="text-sm font-mono whitespace-pre-wrap">{artifact.content}</pre>
              <div className="mt-4 text-xs text-muted-foreground">
                💡 Mermaid diagrams can be rendered in a diagram viewer
              </div>
            </div>
          ) : isCode ? (
            <div className="relative">
              {isEditing ? (
                <div className="space-y-2">
                  <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full h-96 p-4 border border-border rounded-lg bg-background text-foreground font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setIsEditing(false)
                        setEditedContent(artifact.content)
                      }}
                      className="px-4 py-2 border border-border rounded-lg hover:bg-accent"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-muted rounded-lg p-4 overflow-auto max-h-96">
                  <pre className="text-sm font-mono whitespace-pre-wrap">{artifact.content}</pre>
                </div>
              )}
            </div>
          ) : (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <pre className="whitespace-pre-wrap text-sm">{artifact.content}</pre>
            </div>
          )}
        </div>

        {/* Feedback Buttons */}
        <div className="p-4 border-t border-border bg-muted/50">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">Was this helpful?</span>
            <div className="flex gap-2">
              <button
                onClick={() => handleFeedback('positive')}
                className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-500 rounded-lg hover:bg-green-500/30 transition-colors"
              >
                <ThumbsUp className="w-4 h-4" />
                <span className="text-sm">Good</span>
              </button>
              <button
                onClick={() => handleFeedback('negative')}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-500 rounded-lg hover:bg-red-500/30 transition-colors"
              >
                <ThumbsDown className="w-4 h-4" />
                <span className="text-sm">Needs Improvement</span>
              </button>
            </div>
          </div>
        </div>

        {/* Feedback Modal */}

      </div>

      {/* Feedback Modal - Moved outside to avoid overflow clipping */}
      {showFeedbackModal && feedbackType && (
        <FeedbackModal
          artifact={artifact}
          feedbackType={feedbackType}
          onClose={() => {
            setShowFeedbackModal(false)
            setFeedbackType(null)
          }}
          onSubmit={handleSubmitFeedback}
        />
      )}

      <ArtifactComparisonDrawer artifact={artifact} isOpen={isComparisonOpen} onClose={() => setComparisonOpen(false)} />
    </>
  )
}

