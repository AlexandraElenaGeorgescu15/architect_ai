import { Loader2, FileCode, Folder, GitBranch } from 'lucide-react'

interface KnowledgeGraphViewerProps {
  data: any
  isLoading: boolean
}

export default function KnowledgeGraphViewer({ data, isLoading }: KnowledgeGraphViewerProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!data || !data.components || data.components.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
          <GitBranch className="w-8 h-8 text-primary" />
        </div>
        <p className="text-foreground font-medium">No Knowledge Graph data</p>
        <p className="text-sm text-muted-foreground mt-2">
          Knowledge Graph will auto-build when you index your project
        </p>
      </div>
    )
  }

  const { components = [], relationships = [], summary = {} } = data

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
          <div className="text-2xl font-bold text-foreground">{summary.total_classes || 0}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Classes</div>
        </div>
        <div className="p-4 bg-accent/5 rounded-lg border border-accent/20">
          <div className="text-2xl font-bold text-foreground">{summary.total_functions || 0}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Functions</div>
        </div>
        <div className="p-4 bg-primary/5 rounded-lg border border-primary/20">
          <div className="text-2xl font-bold text-foreground">{relationships?.length || 0}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Relationships</div>
        </div>
      </div>

      {/* Components List */}
      <div>
        <h3 className="text-sm font-bold text-foreground mb-3 uppercase tracking-wider">Project Components</h3>
        <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
          {components.slice(0, 20).map((component: any, index: number) => (
            <div
              key={index}
              className="p-3 bg-card border border-border rounded-lg hover:border-primary/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  component.type === 'class' ? 'bg-primary/10 text-primary' :
                  component.type === 'function' ? 'bg-accent/10 text-accent' :
                  'bg-muted/10 text-foreground'
                }`}>
                  {component.type === 'class' ? <Folder className="w-4 h-4" /> : <FileCode className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-foreground truncate">{component.name}</div>
                  <div className="text-xs text-muted-foreground truncate">{component.file || 'Unknown file'}</div>
                </div>
                <div className="text-xs px-2 py-1 bg-primary/10 text-primary rounded">
                  {component.type}
                </div>
              </div>
            </div>
          ))}
        </div>
        {components.length > 20 && (
          <p className="text-xs text-muted-foreground mt-2">
            Showing 20 of {components.length} components
          </p>
        )}
      </div>
    </div>
  )
}

