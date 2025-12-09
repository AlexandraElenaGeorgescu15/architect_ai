import { useState } from 'react'
import { Artifact } from '../../types'
import { FeedbackType } from '../../services/feedbackService'
import { X } from 'lucide-react'

interface FeedbackModalProps {
  artifact: Artifact
  feedbackType: FeedbackType
  onClose: () => void
  onSubmit: (score: number, notes?: string, correctedContent?: string) => Promise<void>
}

export default function FeedbackModal({
  artifact,
  feedbackType,
  onClose,
  onSubmit,
}: FeedbackModalProps) {
  const [score, setScore] = useState(85)
  const [notes, setNotes] = useState('')
  const [correctedContent, setCorrectedContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Map feedback types for display
  const isPositive = feedbackType === 'positive'
  const showCorrection = feedbackType === 'negative' || feedbackType === 'correction'

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      const finalScore = isPositive ? score : 50
      await onSubmit(
        finalScore,
        notes || undefined,
        correctedContent || undefined
      )
    } catch (error) {
      // Failed to submit feedback - handle in UI
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
      <div 
        className="bg-card text-card-foreground border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden"
        style={{
          width: 'min(95vw, 500px)',
          maxHeight: 'min(90vh, 600px)',
        }}
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between bg-background/50 flex-shrink-0">
          <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
            <span className="text-xl">{isPositive ? '👍' : '👎'}</span>
            {isPositive ? 'Positive Feedback' : 'Needs Improvement'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-destructive/10 hover:text-destructive rounded-lg transition-colors"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content - scrollable */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
          <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
            <label className="block text-xs font-semibold text-foreground mb-1">
              Artifact Type
            </label>
            <p className="text-sm text-primary capitalize font-medium">
              {artifact.type.replace(/_/g, ' ')}
            </p>
          </div>

          {isPositive && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-semibold text-foreground">
                  Quality Score
                </label>
                <div className="px-2 py-1 rounded-lg bg-primary/10 border border-primary/20">
                  <span className="text-sm font-bold text-primary">{score}%</span>
                </div>
              </div>
              <input
                type="range"
                min="70"
                max="100"
                value={score}
                onChange={(e) => setScore(Number(e.target.value))}
                className="w-full h-2 rounded-full appearance-none bg-muted cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary 
                  [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 
                  [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-primary 
                  [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:shadow-md [&::-moz-range-thumb]:cursor-pointer"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>70%</span>
                <span>85%</span>
                <span>100%</span>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-foreground mb-1">
              {isPositive ? 'Additional Notes (Optional)' : "What's wrong?"}
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                isPositive
                  ? 'Tell us what you liked...'
                  : 'Describe what needs to be improved...'
              }
              className="w-full h-20 p-3 border border-border rounded-lg bg-background text-foreground text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>

          {showCorrection && (
            <div>
              <label className="block text-sm font-semibold text-foreground mb-1">
                Corrected Content (Optional)
              </label>
              <textarea
                value={correctedContent}
                onChange={(e) => setCorrectedContent(e.target.value)}
                placeholder="Provide the corrected version..."
                className="w-full h-24 p-3 border border-border rounded-lg bg-background text-foreground font-mono text-xs resize-none focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
              <p className="text-xs text-muted-foreground mt-1">
                💡 Providing corrections helps improve future generations.
              </p>
            </div>
          )}
        </div>

        {/* Actions - fixed at bottom */}
        <div className="p-4 border-t border-border bg-muted/30 flex justify-end gap-3 flex-shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-border rounded-lg hover:bg-muted transition-colors text-sm font-medium text-foreground"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium text-sm hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </div>
      </div>
    </div>
  )
}

