import { useState, useEffect } from 'react'
import { X, Layers, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { ArtifactType } from '../services/generationService'

interface BulkGenerationProgress {
  artifactType: ArtifactType
  status: 'pending' | 'generating' | 'completed' | 'failed'
  progress: number
  message?: string
  error?: string
}

interface BulkGenerationDialogProps {
  isOpen: boolean
  onClose: () => void
  artifactTypes: { value: ArtifactType; label: string; category: string }[]
  onGenerate: (artifactTypes: ArtifactType[], onProgress?: (progress: BulkGenerationProgress[]) => void) => Promise<void>
}

export default function BulkGenerationDialog({
  isOpen,
  onClose,
  artifactTypes,
  onGenerate,
}: BulkGenerationDialogProps) {
  const [selection, setSelection] = useState<ArtifactType[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [bulkProgress, setBulkProgress] = useState<BulkGenerationProgress[]>([])
  const [showProgress, setShowProgress] = useState(false)

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setShowProgress(false)
      setBulkProgress([])
    }
  }, [isOpen])

  if (!isOpen) return null

  const toggleSelection = (type: ArtifactType) => {
    setSelection((prev) =>
      prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type]
    )
  }

  const handleProgressUpdate = (progress: BulkGenerationProgress[]) => {
    setBulkProgress(progress)
  }

  const handleGenerate = async () => {
    if (!selection.length) return
    setIsSubmitting(true)
    setShowProgress(true)
    
    // Initialize progress for all selected artifacts
    const initialProgress: BulkGenerationProgress[] = selection.map(type => ({
      artifactType: type,
      status: 'pending',
      progress: 0
    }))
    setBulkProgress(initialProgress)
    
    try {
      await onGenerate(selection, handleProgressUpdate)
      // Don't clear selection immediately - let user see results
      setTimeout(() => {
        setSelection([])
        onClose()
      }, 2000)
    } finally {
      setIsSubmitting(false)
    }
  }

  const getArtifactLabel = (type: ArtifactType) => {
    return artifactTypes.find(t => t.value === type)?.label || type
  }

  const completedCount = bulkProgress.filter(p => p.status === 'completed').length
  const failedCount = bulkProgress.filter(p => p.status === 'failed').length
  const totalCount = bulkProgress.length

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-fade-in">
      <div className="glass-panel bg-card text-card-foreground border-2 border-border rounded-2xl shadow-floating w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
              <Layers className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Bulk Generation</h2>
              <p className="text-xs text-muted-foreground">Select multiple artifacts to generate in one run.</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 group"
            aria-label="Close"
          >
            <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 custom-scrollbar bg-background/30">
          {showProgress && bulkProgress.length > 0 ? (
            /* Progress View */
            <div className="space-y-3">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-foreground">Generation Progress</h3>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-green-500 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> {completedCount} done
                  </span>
                  {failedCount > 0 && (
                    <span className="text-red-500 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> {failedCount} failed
                    </span>
                  )}
                  <span className="text-muted-foreground">{totalCount} total</span>
                </div>
              </div>
              
              {/* Overall Progress Bar */}
              <div className="mb-4">
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-primary to-primary/80 transition-all duration-500"
                    style={{ width: `${((completedCount + failedCount) / totalCount) * 100}%` }}
                  />
                </div>
                <div className="text-xs text-muted-foreground mt-1 text-right">
                  {Math.round(((completedCount + failedCount) / totalCount) * 100)}% complete
                </div>
              </div>
              
              {/* Individual Artifact Progress */}
              <div className="space-y-2 max-h-[40vh] overflow-y-auto pr-2 custom-scrollbar">
                {bulkProgress.map((item) => (
                  <div 
                    key={item.artifactType}
                    className={`p-3 rounded-xl border-2 transition-all duration-300 ${
                      item.status === 'completed' 
                        ? 'border-green-500/50 bg-green-500/5' 
                        : item.status === 'failed'
                          ? 'border-red-500/50 bg-red-500/5'
                          : item.status === 'generating'
                            ? 'border-primary/50 bg-primary/5'
                            : 'border-border bg-card/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm text-foreground">
                        {getArtifactLabel(item.artifactType)}
                      </span>
                      <div className="flex items-center gap-2">
                        {item.status === 'pending' && (
                          <span className="text-xs text-muted-foreground">Waiting...</span>
                        )}
                        {item.status === 'generating' && (
                          <span className="text-xs text-primary flex items-center gap-1">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            {item.progress}%
                          </span>
                        )}
                        {item.status === 'completed' && (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        )}
                        {item.status === 'failed' && (
                          <AlertCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                    </div>
                    
                    {item.status === 'generating' && (
                      <div className="h-1 bg-muted rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-primary transition-all duration-300"
                          style={{ width: `${item.progress}%` }}
                        />
                      </div>
                    )}
                    
                    {item.message && (
                      <div className="text-xs text-muted-foreground mt-1">{item.message}</div>
                    )}
                    
                    {item.error && (
                      <div className="text-xs text-red-500 mt-1">{item.error}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Selection View */
            <div className="grid gap-3 md:grid-cols-2">
              {artifactTypes.map((type) => (
                <label
                  key={type.value}
                  className={`glass-button border-2 rounded-xl p-4 cursor-pointer transition-all duration-300 group ${
                    selection.includes(type.value)
                      ? 'border-primary bg-primary/10 shadow-glow'
                      : 'border-border hover:border-primary/50 hover:bg-primary/5'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selection.includes(type.value)}
                      onChange={() => toggleSelection(type.value)}
                      className="mt-1 w-4 h-4 accent-primary rounded border-border"
                    />
                    <div className="flex-1">
                      <span className="font-semibold text-foreground block group-hover:text-primary transition-colors">
                        {type.label}
                      </span>
                      <span className="text-xs text-muted-foreground block mt-1">{type.category}</span>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-background/50">
          {showProgress ? (
            <>
              <div className="flex items-center gap-2">
                {completedCount === totalCount && failedCount === 0 ? (
                  <span className="text-sm text-green-500 font-medium flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    All artifacts generated successfully!
                  </span>
                ) : completedCount + failedCount === totalCount ? (
                  <span className="text-sm text-foreground">
                    Generation complete: {completedCount} success, {failedCount} failed
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating artifacts...
                  </span>
                )}
              </div>
              <button
                onClick={onClose}
                disabled={isSubmitting && completedCount + failedCount < totalCount}
                className="px-6 py-2.5 bg-muted text-foreground rounded-xl font-semibold hover:bg-muted/80 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-300"
              >
                {completedCount + failedCount === totalCount ? 'Close' : 'Cancel'}
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <div className="px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20">
                  <span className="text-sm font-bold text-primary">{selection.length}</span>
                </div>
                <span className="text-sm text-muted-foreground">artifacts selected</span>
              </div>
              <button
                onClick={handleGenerate}
                disabled={!selection.length || isSubmitting}
                className="px-6 py-2.5 bg-primary text-primary-foreground rounded-xl font-semibold hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-300 shadow-md hover:shadow-glow hover:scale-105 active:scale-95"
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Starting...
                  </span>
                ) : (
                  'Generate Selected'
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

