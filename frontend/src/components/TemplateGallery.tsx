import { useEffect, useState } from 'react'
import { X, Sparkles, Layers } from 'lucide-react'
import { Template, TemplateApplyResponse, listTemplates, applyTemplate } from '../services/templateService'
import { useUIStore } from '../stores/uiStore'

interface TemplateGalleryProps {
  isOpen: boolean
  onClose: () => void
  onApply: (payload: TemplateApplyResponse) => void
}

export default function TemplateGallery({ isOpen, onClose, onApply }: TemplateGalleryProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isApplying, setIsApplying] = useState<string | null>(null)
  const { addNotification } = useUIStore()

  useEffect(() => {
    if (!isOpen) return
    setIsLoading(true)
    listTemplates()
      .then(setTemplates)
      .catch((error) => {
        // Failed to load templates - show notification
        addNotification('error', 'Failed to load templates')
      })
      .finally(() => setIsLoading(false))
  }, [isOpen, addNotification])

  if (!isOpen) return null

  const handleApply = async (templateId: string) => {
    setIsApplying(templateId)
    try {
      const response = await applyTemplate(templateId)
      onApply(response)
      addNotification('success', `${response.template.name} template applied`)
      onClose()
    } catch (error) {
      // Failed to apply template - show notification
      addNotification('error', 'Failed to apply template')
    } finally {
      setIsApplying(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md animate-fade-in">
      <div className="glass-panel bg-card text-card-foreground border-2 border-border rounded-2xl shadow-floating w-full max-w-4xl max-h-[80vh] overflow-hidden flex flex-col animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary/10 border border-primary/20">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">Template Gallery</h2>
              <p className="text-xs text-muted-foreground">Kick-start your session with curated blueprints.</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 group" 
            aria-label="Close template gallery"
          >
            <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 custom-scrollbar bg-background/30">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="flex items-center gap-3 text-primary">
                <div className="animate-spin">⏳</div>
                <p className="text-sm font-medium">Loading templates…</p>
              </div>
            </div>
          ) : templates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Sparkles className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
              <p className="text-sm text-muted-foreground">No templates available</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {templates.map((template) => (
                <div 
                  key={template.id} 
                  className="glass-button border-2 border-border rounded-xl p-5 bg-background/50 space-y-4 hover:border-primary/30 hover:bg-primary/5 transition-all duration-300 group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <h3 className="font-bold text-foreground group-hover:text-primary transition-colors">
                        {template.name}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                        {template.description}
                      </p>
                    </div>
                    <span
                      className={`px-2.5 py-1 text-[10px] font-bold rounded-lg border whitespace-nowrap ${
                        template.complexity === 'high'
                          ? 'bg-destructive/10 text-destructive border-destructive/20'
                          : template.complexity === 'medium'
                            ? 'bg-warning/10 text-warning border-warning/20'
                            : 'bg-success/10 text-success border-success/20'
                      }`}
                    >
                      {template.complexity.toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="flex flex-wrap gap-1.5">
                    {template.tags.map((tag) => (
                      <span 
                        key={tag} 
                        className="text-[10px] px-2 py-1 bg-muted/50 rounded-md text-muted-foreground font-medium border border-border/50"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                  
                  <div className="text-xs text-muted-foreground flex items-center gap-2 px-3 py-2 bg-primary/5 rounded-lg border border-primary/10">
                    <Layers className="w-3.5 h-3.5 text-primary" />
                    <span className="font-medium">
                      Recommends <span className="text-primary font-bold">{template.recommended_artifacts.length}</span> artifacts
                    </span>
                  </div>
                  
                  <button
                    onClick={() => handleApply(template.id)}
                    disabled={isApplying === template.id}
                    className="w-full px-4 py-2.5 text-sm font-semibold bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-300 shadow-md hover:shadow-glow hover:scale-105 active:scale-95"
                  >
                    {isApplying === template.id ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="animate-spin">⏳</span>
                        Applying…
                      </span>
                    ) : (
                      'Apply Template'
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

