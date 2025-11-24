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

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      const finalScore = feedbackType === 'approval' ? score : 50
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
    <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="glass-panel bg-card text-card-foreground border-2 border-border rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-floating animate-scale-in custom-scrollbar">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between bg-background/50">
          <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
            <span className="text-2xl">{feedbackType === 'approval' ? '👍' : '👎'}</span>
            {feedbackType === 'approval' ? 'Positive Feedback' : 'Needs Improvement'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 group"
            aria-label="Close"
          >
            <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 bg-background/30">
          <div className="glass-panel bg-primary/5 border border-primary/20 rounded-xl p-4">
            <label className="block text-sm font-semibold text-foreground mb-1">
              Artifact Type
            </label>
            <p className="text-sm text-primary capitalize font-medium">
              {artifact.type.replace(/_/g, ' ')}
            </p>
          </div>

          {feedbackType === 'approval' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-semibold text-foreground">
                  Quality Score
                </label>
                <div className="px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20">
                  <span className="text-lg font-bold text-primary">{score}%</span>
                </div>
              </div>
              <input
                type="range"
                min="70"
                max="100"
                value={score}
                onChange={(e) => setScore(Number(e.target.value))}
                className="w-full h-2 rounded-full appearance-none bg-muted cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 
                  [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary 
                  [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5 
                  [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-primary 
                  [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:shadow-md [&::-moz-range-thumb]:cursor-pointer"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span className="font-mono">70%</span>
                <span className="font-mono">85%</span>
                <span className="font-mono">100%</span>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-foreground mb-2">
              {feedbackType === 'approval' ? 'Additional Notes (Optional)' : "What's wrong?"}
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                feedbackType === 'approval'
                  ? 'Tell us what you liked about this artifact...'
                  : 'Describe what needs to be improved...'
              }
              className="w-full h-32 p-4 glass-input border-2 border-border rounded-xl bg-background/50 text-foreground resize-none transition-all duration-300 focus:border-primary/50 focus:bg-background"
            />
          </div>

          {feedbackType === 'correction' && (
            <div>
              <label className="block text-sm font-semibold text-foreground mb-2">
                Corrected Content (Optional)
              </label>
              <textarea
                value={correctedContent}
                onChange={(e) => setCorrectedContent(e.target.value)}
                placeholder="Provide the corrected version of the artifact..."
                className="w-full h-48 p-4 glass-input border-2 border-border rounded-xl bg-background/50 text-foreground font-mono text-sm resize-none transition-all duration-300 focus:border-primary/50 focus:bg-background custom-scrollbar"
              />
              <p className="text-xs text-muted-foreground mt-2 flex items-start gap-2">
                <span className="text-primary">💡</span>
                <span>Providing corrected content helps improve the model for future generations.</span>
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-6 border-t border-border bg-background/50 -mx-6 px-6 -mb-6 pb-6">
            <button
              onClick={onClose}
              className="px-6 py-2.5 border-2 border-border rounded-xl hover:bg-muted hover:border-primary/30 transition-all duration-300 font-semibold text-foreground"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="px-6 py-2.5 bg-primary text-primary-foreground rounded-xl font-semibold hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-300 shadow-md hover:shadow-glow hover:scale-105 active:scale-95"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Submitting...
                </span>
              ) : (
                'Submit Feedback'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

