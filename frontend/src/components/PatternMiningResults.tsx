import { Loader2, Layers, CheckCircle2, AlertCircle } from 'lucide-react'

interface PatternMiningResultsProps {
  data: any
  isLoading: boolean
}

export default function PatternMiningResults({ data, isLoading }: PatternMiningResultsProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    )
  }

  if (!data || !data.patterns || data.patterns.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent/10 flex items-center justify-center">
          <Layers className="w-8 h-8 text-accent" />
        </div>
        <p className="text-foreground font-medium">No design patterns detected</p>
        <p className="text-sm text-muted-foreground mt-2">
          Pattern Mining will auto-analyze when you index your project
        </p>
      </div>
    )
  }

  const { patterns = [], summary = {} } = data

  // Group patterns by type
  const patternGroups: Record<string, any[]> = {}
  patterns.forEach((pattern: any) => {
    const type = pattern.pattern_type || 'Other'
    if (!patternGroups[type]) {
      patternGroups[type] = []
    }
    patternGroups[type].push(pattern)
  })

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 bg-accent/5 rounded-lg border border-accent/20">
          <div className="text-2xl font-bold text-foreground">{patterns.length}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Total Patterns</div>
        </div>
        <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
          <div className="text-2xl font-bold text-foreground">{Object.keys(patternGroups).length}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Pattern Types</div>
        </div>
        <div className="p-4 bg-accent/5 rounded-lg border border-accent/20">
          <div className="text-2xl font-bold text-foreground">{summary.confidence_avg?.toFixed(1) || 'N/A'}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Avg Confidence</div>
        </div>
      </div>

      {/* Patterns by Type */}
      <div>
        <h3 className="text-sm font-bold text-foreground mb-3 uppercase tracking-wider">Detected Patterns</h3>
        <div className="space-y-4">
          {Object.entries(patternGroups).map(([type, patternsInGroup]) => (
            <div key={type} className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Layers className="w-4 h-4 text-accent" />
                </div>
                <div>
                  <div className="font-bold text-foreground">{type}</div>
                  <div className="text-xs text-muted-foreground">{patternsInGroup.length} instance{patternsInGroup.length > 1 ? 's' : ''}</div>
                </div>
              </div>
              <div className="space-y-2">
                {patternsInGroup.slice(0, 3).map((pattern: any, index: number) => (
                  <div key={index} className="p-3 bg-background rounded-lg border border-border">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground truncate">{pattern.name || 'Unnamed'}</div>
                        <div className="text-xs text-muted-foreground truncate mt-1">{pattern.file || 'Unknown file'}</div>
                        {pattern.description && (
                          <div className="text-xs text-muted-foreground mt-2">{pattern.description}</div>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {pattern.confidence >= 0.8 ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-yellow-500" />
                        )}
                        <span className="text-xs text-muted-foreground">{(pattern.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
                {patternsInGroup.length > 3 && (
                  <p className="text-xs text-muted-foreground text-center py-2">
                    + {patternsInGroup.length - 3} more
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

