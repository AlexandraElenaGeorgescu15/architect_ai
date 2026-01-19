import { useState, useEffect } from 'react'
import { X, Layers, CheckCircle, AlertCircle, Loader2, Package, Zap, Layout, FileCode, FileText, Sparkles } from 'lucide-react'
import { ArtifactType } from '../services/generationService'

interface BulkGenerationProgress {
  artifactType: ArtifactType
  status: 'pending' | 'generating' | 'completed' | 'failed'
  progress: number
  message?: string
  error?: string
}

// Sprint Package Presets - Quick selection groups
interface PackagePreset {
  id: string
  name: string
  description: string
  icon: typeof Package
  color: string
  artifacts: ArtifactType[]
  estimatedTime: string
}

const PACKAGE_PRESETS: PackagePreset[] = [
  {
    id: 'full',
    name: 'Full Sprint Package',
    description: 'Complete artifact suite for a feature',
    icon: Package,
    color: 'text-primary',
    artifacts: ['mermaid_erd', 'mermaid_architecture', 'mermaid_sequence', 'api_docs', 'code_prototype', 'dev_visual_prototype', 'jira'],
    estimatedTime: '~15 min'
  },
  {
    id: 'backend',
    name: 'Backend Package',
    description: 'Data model, API, and implementation',
    icon: FileCode,
    color: 'text-emerald-500',
    artifacts: ['mermaid_erd', 'mermaid_class', 'api_docs', 'code_prototype'],
    estimatedTime: '~8 min'
  },
  {
    id: 'frontend',
    name: 'Frontend Package',
    description: 'UI prototype and user flows',
    icon: Layout,
    color: 'text-blue-500',
    artifacts: ['dev_visual_prototype', 'mermaid_user_flow', 'mermaid_state'],
    estimatedTime: '~6 min'
  },
  {
    id: 'documentation',
    name: 'Documentation Package',
    description: 'All diagrams and documentation',
    icon: FileText,
    color: 'text-amber-500',
    artifacts: ['mermaid_erd', 'mermaid_architecture', 'mermaid_sequence', 'mermaid_component', 'mermaid_data_flow', 'api_docs'],
    estimatedTime: '~10 min'
  },
  {
    id: 'quick',
    name: 'Quick Start',
    description: 'Essential artifacts only',
    icon: Zap,
    color: 'text-purple-500',
    artifacts: ['mermaid_erd', 'mermaid_architecture', 'api_docs'],
    estimatedTime: '~5 min'
  }
]

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
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'presets' | 'custom'>('presets')

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setShowProgress(false)
      setBulkProgress([])
      setActivePreset(null)
      setViewMode('presets')
    }
  }, [isOpen])

  if (!isOpen) return null

  const toggleSelection = (type: ArtifactType) => {
    setActivePreset(null) // Clear preset when manually selecting
    setSelection((prev) =>
      prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type]
    )
  }

  const applyPreset = (preset: PackagePreset) => {
    // Only include artifacts that are available in the artifactTypes list
    const availableArtifacts = preset.artifacts.filter(a => 
      artifactTypes.some(t => t.value === a)
    )
    setSelection(availableArtifacts as ArtifactType[])
    setActivePreset(preset.id)
    setViewMode('custom') // Switch to custom view to show what's selected
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fade-in">
      <div className="glass-panel bg-card text-card-foreground border-2 border-border rounded-2xl shadow-floating w-full max-w-3xl max-h-[85vh] sm:max-h-[80vh] overflow-hidden flex flex-col animate-scale-in mx-2 sm:mx-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
              <Layers className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Sprint Package Generator</h2>
              <p className="text-xs text-muted-foreground">Generate multiple artifacts in one run</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!showProgress && (
              <div className="flex rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => setViewMode('presets')}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    viewMode === 'presets' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-background hover:bg-secondary text-muted-foreground'
                  }`}
                >
                  <Sparkles className="w-3 h-3 inline mr-1" />
                  Presets
                </button>
                <button
                  onClick={() => setViewMode('custom')}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    viewMode === 'custom' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-background hover:bg-secondary text-muted-foreground'
                  }`}
                >
                  Custom
                </button>
              </div>
            )}
            <button 
              onClick={onClose} 
              className="p-2 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 group"
              aria-label="Close"
            >
              <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
            </button>
          </div>
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
          ) : viewMode === 'presets' ? (
            /* Presets View */
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground mb-4">
                Choose a pre-configured package or customize your selection
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                {PACKAGE_PRESETS.map((preset) => {
                  const Icon = preset.icon
                  const availableCount = preset.artifacts.filter(a => 
                    artifactTypes.some(t => t.value === a)
                  ).length
                  
                  return (
                    <button
                      key={preset.id}
                      onClick={() => applyPreset(preset)}
                      className={`text-left border-2 rounded-xl p-4 transition-all duration-300 hover:scale-[1.02] ${
                        activePreset === preset.id
                          ? 'border-primary bg-primary/10 shadow-glow'
                          : 'border-border hover:border-primary/50 hover:bg-primary/5'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-lg bg-secondary flex items-center justify-center ${preset.color}`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="flex-1">
                          <span className="font-semibold text-foreground block">
                            {preset.name}
                          </span>
                          <span className="text-xs text-muted-foreground block mt-1">
                            {preset.description}
                          </span>
                          <div className="flex items-center gap-3 mt-2">
                            <span className="text-xs px-2 py-0.5 bg-secondary rounded-full">
                              {availableCount} artifacts
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {preset.estimatedTime}
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
              
              {activePreset && (
                <div className="mt-4 p-3 bg-primary/5 border border-primary/20 rounded-lg">
                  <p className="text-sm text-primary font-medium mb-2">
                    Selected: {PACKAGE_PRESETS.find(p => p.id === activePreset)?.name}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {selection.map(type => (
                      <span key={type} className="text-xs px-2 py-1 bg-primary/10 text-primary rounded">
                        {getArtifactLabel(type)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Custom Selection View */
            <div className="space-y-4">
              {activePreset && (
                <div className="p-3 bg-primary/5 border border-primary/20 rounded-lg flex items-center justify-between">
                  <span className="text-sm text-primary">
                    Based on: {PACKAGE_PRESETS.find(p => p.id === activePreset)?.name}
                  </span>
                  <button 
                    onClick={() => { setActivePreset(null); setSelection([]) }}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    Clear
                  </button>
                </div>
              )}
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

