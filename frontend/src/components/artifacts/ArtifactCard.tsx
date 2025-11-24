import { useState } from 'react'
import { Artifact } from '../../types'
import { FileCode, ExternalLink, ThumbsUp, ThumbsDown } from 'lucide-react'
import { useArtifactStore } from '../../stores/artifactStore'
import { useUIStore } from '../../stores/uiStore'
import { submitFeedback, FeedbackType } from '../../services/feedbackService'

interface ArtifactCardProps {
  artifact: Artifact
  onClick?: () => void
}

export default function ArtifactCard({ artifact, onClick }: ArtifactCardProps) {
  const { setCurrentArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)

  const handleClick = () => {
    setCurrentArtifact(artifact)
    if (onClick) {
      onClick()
    }
  }

  const handleFeedback = async (e: React.MouseEvent, type: FeedbackType) => {
    e.stopPropagation()
    setIsSubmittingFeedback(true)
    
    try {
      await submitFeedback({
        artifact_id: artifact.id,
        score: type === 'approval' ? 85 : 60,
        feedback_type: type,
      })
      addNotification('success', 
        type === 'approval' 
          ? '👍 Thanks! This will help improve future generations.'
          : 'Feedback received. We\'ll work on improving this.'
      )
    } catch (error) {
      addNotification('error', 'Failed to submit feedback. Please try again.')
    } finally {
      setIsSubmittingFeedback(false)
    }
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
      </div>

      {/* Feedback Buttons */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border">
        <button
          onClick={(e) => handleFeedback(e, 'approval')}
          disabled={isSubmittingFeedback}
          className="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded-md hover:bg-green-500/20 hover:text-green-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group/thumb"
          title="This looks good! Help improve future generations"
        >
          <ThumbsUp className="w-3.5 h-3.5 group-hover/thumb:scale-110 transition-transform" />
          <span className="hidden sm:inline">Good</span>
        </button>
        <button
          onClick={(e) => handleFeedback(e, 'correction')}
          disabled={isSubmittingFeedback}
          className="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded-md hover:bg-red-500/20 hover:text-red-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed group/thumb"
          title="Needs improvement"
        >
          <ThumbsDown className="w-3.5 h-3.5 group-hover/thumb:scale-110 transition-transform" />
          <span className="hidden sm:inline">Improve</span>
        </button>
      </div>

      {isMermaid && (
        <div className="mt-2 text-xs text-primary">
          📊 Diagram
        </div>
      )}
    </div>
  )
}

