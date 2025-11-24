import { useState } from 'react'
import { X, Layers } from 'lucide-react'
import { ArtifactType } from '../services/generationService'

interface BulkGenerationDialogProps {
  isOpen: boolean
  onClose: () => void
  artifactTypes: { value: ArtifactType; label: string; category: string }[]
  onGenerate: (artifactTypes: ArtifactType[]) => Promise<void>
}

export default function BulkGenerationDialog({
  isOpen,
  onClose,
  artifactTypes,
  onGenerate,
}: BulkGenerationDialogProps) {
  const [selection, setSelection] = useState<ArtifactType[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isOpen) return null

  const toggleSelection = (type: ArtifactType) => {
    setSelection((prev) =>
      prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type]
    )
  }

  const handleGenerate = async () => {
    if (!selection.length) return
    setIsSubmitting(true)
    try {
      await onGenerate(selection)
      setSelection([])
      onClose()
    } finally {
      setIsSubmitting(false)
    }
  }

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
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-background/50">
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
                <span className="animate-spin">⏳</span>
                Generating…
              </span>
            ) : (
              'Generate Selected'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

