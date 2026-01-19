import { useState, useEffect, useCallback } from 'react'
import { 
  Link2, ArrowRight, AlertTriangle, CheckCircle2, Clock, RefreshCw, 
  Loader2, ChevronDown, ChevronRight, FileText, Database, Code 
} from 'lucide-react'
import api from '../services/api'
import { useArtifactStore } from '../stores/artifactStore'

interface ArtifactLink {
  source_id: string
  source_type: string
  target_id: string
  target_type: string
  link_type: 'depends_on' | 'derived_from' | 'complements'
  created_at: string
}

interface StalenessReport {
  artifact_id: string
  artifact_type: string
  is_stale: boolean
  reason: string
  stale_since?: string
  upstream_changes: any[]
  recommendation: string
}

// Dependency rules: which artifact types depend on which
const DEPENDENCY_RULES: Record<string, { downstream: string[], reason: string }> = {
  'mermaid_erd': {
    downstream: ['api_docs', 'code_prototype', 'mermaid_sequence', 'mermaid_class'],
    reason: 'ERD defines the data model used by these artifacts'
  },
  'mermaid_architecture': {
    downstream: ['mermaid_component', 'mermaid_sequence', 'mermaid_data_flow', 'code_prototype'],
    reason: 'Architecture defines the system structure these build on'
  },
  'api_docs': {
    downstream: ['code_prototype', 'dev_visual_prototype'],
    reason: 'API docs define the contracts implemented by code'
  }
}

const TYPE_ICONS: Record<string, typeof FileText> = {
  'mermaid_erd': Database,
  'mermaid_architecture': FileText,
  'mermaid_sequence': ArrowRight,
  'api_docs': FileText,
  'code_prototype': Code,
}

export default function ArtifactDependencies() {
  const { artifacts } = useArtifactStore()
  const [links, setLinks] = useState<ArtifactLink[]>([])
  const [stalenessReports, setStalenessReports] = useState<StalenessReport[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['mermaid_erd', 'mermaid_architecture']))

  const loadDependencies = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Try to load from backend
      const [linksRes, stalenessRes] = await Promise.allSettled([
        api.get<{ links: ArtifactLink[] }>('/api/artifacts/links'),
        api.get<{ reports: StalenessReport[] }>('/api/artifacts/staleness')
      ])
      
      if (linksRes.status === 'fulfilled') {
        setLinks(linksRes.value.data.links || [])
      }
      if (stalenessRes.status === 'fulfilled') {
        setStalenessReports(stalenessRes.value.data.reports || [])
      }
    } catch (err: any) {
      // If endpoints don't exist, compute dependencies client-side
      computeClientSideDependencies()
    } finally {
      setIsLoading(false)
    }
  }, [artifacts])

  const computeClientSideDependencies = useCallback(() => {
    // Compute dependencies based on artifact types present
    const computedLinks: ArtifactLink[] = []
    const computedStaleness: StalenessReport[] = []
    
    artifacts.forEach(artifact => {
      const rules = DEPENDENCY_RULES[artifact.type]
      if (rules) {
        rules.downstream.forEach(downstreamType => {
          // Find downstream artifacts of this type
          const downstreamArtifacts = artifacts.filter(a => a.type === downstreamType)
          downstreamArtifacts.forEach(downstream => {
            computedLinks.push({
              source_id: artifact.id,
              source_type: artifact.type,
              target_id: downstream.id,
              target_type: downstream.type,
              link_type: 'depends_on',
              created_at: new Date().toISOString()
            })
            
            // Check if downstream is older than upstream
            if (downstream.created_at && artifact.created_at) {
              const upstreamDate = new Date(artifact.created_at)
              const downstreamDate = new Date(downstream.created_at)
              
              if (downstreamDate < upstreamDate) {
                computedStaleness.push({
                  artifact_id: downstream.id,
                  artifact_type: downstream.type,
                  is_stale: true,
                  reason: `Generated before ${artifact.type} was updated`,
                  stale_since: artifact.created_at,
                  upstream_changes: [{ artifact_id: artifact.id, artifact_type: artifact.type }],
                  recommendation: `Regenerate ${downstream.type} to reflect changes in ${artifact.type}`
                })
              }
            }
          })
        })
      }
    })
    
    setLinks(computedLinks)
    setStalenessReports(computedStaleness)
  }, [artifacts])

  useEffect(() => {
    loadDependencies()
  }, [loadDependencies])

  const toggleExpand = (type: string) => {
    const newExpanded = new Set(expandedTypes)
    if (newExpanded.has(type)) {
      newExpanded.delete(type)
    } else {
      newExpanded.add(type)
    }
    setExpandedTypes(newExpanded)
  }

  const getTypeIcon = (type: string) => {
    return TYPE_ICONS[type] || FileText
  }

  // Group artifacts by type for display
  const groupedArtifacts = artifacts.reduce((acc, artifact) => {
    if (!acc[artifact.type]) {
      acc[artifact.type] = []
    }
    acc[artifact.type].push(artifact)
    return acc
  }, {} as Record<string, typeof artifacts>)

  // Get upstream/downstream for each type
  const getDependencyInfo = (type: string) => {
    const upstream: string[] = []
    const downstream: string[] = []
    
    // Find what this type depends on
    Object.entries(DEPENDENCY_RULES).forEach(([upstreamType, rules]) => {
      if (rules.downstream.includes(type)) {
        upstream.push(upstreamType)
      }
    })
    
    // Find what depends on this type
    if (DEPENDENCY_RULES[type]) {
      downstream.push(...DEPENDENCY_RULES[type].downstream)
    }
    
    return { upstream, downstream }
  }

  const staleArtifactIds = new Set(stalenessReports.filter(r => r.is_stale).map(r => r.artifact_id))

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-destructive" />
          <span className="text-sm text-destructive">{error}</span>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            Track relationships between artifacts and detect when regeneration is needed
          </p>
          {stalenessReports.filter(r => r.is_stale).length > 0 && (
            <p className="text-xs text-amber-500 mt-1 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              {stalenessReports.filter(r => r.is_stale).length} artifact(s) may need regeneration
            </p>
          )}
        </div>
        <button
          onClick={loadDependencies}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg hover:bg-secondary/50 transition-colors text-sm"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh
        </button>
      </div>

      {/* Dependency Rules Reference */}
      <div className="border border-dashed border-border rounded-lg p-4 bg-secondary/10">
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Link2 className="w-4 h-4" />
          Dependency Rules
        </h4>
        <div className="space-y-2 text-xs text-muted-foreground">
          {Object.entries(DEPENDENCY_RULES).map(([type, rules]) => (
            <div key={type} className="flex items-center gap-2">
              <span className="font-medium text-foreground">{type.replace(/_/g, ' ')}</span>
              <ArrowRight className="w-3 h-3" />
              <span>{rules.downstream.map(d => d.replace(/_/g, ' ')).join(', ')}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Artifact List with Dependencies */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : Object.keys(groupedArtifacts).length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-lg">
          <Link2 className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground mb-2">No artifacts to analyze</p>
          <p className="text-xs text-muted-foreground">Generate artifacts to see their dependencies</p>
        </div>
      ) : (
        <div className="space-y-2">
          {Object.entries(groupedArtifacts).map(([type, typeArtifacts]) => {
            const Icon = getTypeIcon(type)
            const depInfo = getDependencyInfo(type)
            const isExpanded = expandedTypes.has(type)
            const hasStale = typeArtifacts.some(a => staleArtifactIds.has(a.id))
            
            return (
              <div key={type} className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => toggleExpand(type)}
                  className="w-full flex items-center justify-between p-4 hover:bg-secondary/30 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${hasStale ? 'bg-amber-500/10 text-amber-500' : 'bg-secondary text-muted-foreground'}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="font-medium">{type.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase())}</span>
                      <span className="text-xs text-muted-foreground ml-2">({typeArtifacts.length})</span>
                      {hasStale && (
                        <span className="ml-2 text-xs text-amber-500 flex items-center gap-1 inline-flex">
                          <Clock className="w-3 h-3" /> Needs update
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {depInfo.upstream.length > 0 && (
                      <span className="text-xs text-muted-foreground">
                        ← Depends on: {depInfo.upstream.length}
                      </span>
                    )}
                    {depInfo.downstream.length > 0 && (
                      <span className="text-xs text-muted-foreground">
                        → Feeds into: {depInfo.downstream.length}
                      </span>
                    )}
                    {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </div>
                </button>
                
                {isExpanded && (
                  <div className="border-t border-border p-4 bg-secondary/10 space-y-2">
                    {typeArtifacts.map(artifact => {
                      const isStale = staleArtifactIds.has(artifact.id)
                      const stalenessReport = stalenessReports.find(r => r.artifact_id === artifact.id)
                      
                      return (
                        <div 
                          key={artifact.id}
                          className={`flex items-center justify-between p-3 rounded-lg ${
                            isStale ? 'bg-amber-500/5 border border-amber-500/20' : 'bg-background border border-border'
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {isStale ? (
                              <AlertTriangle className="w-4 h-4 text-amber-500" />
                            ) : (
                              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                            )}
                            <span className="text-sm font-medium truncate max-w-[200px]">{artifact.id}</span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {artifact.created_at && new Date(artifact.created_at).toLocaleDateString()}
                          </div>
                        </div>
                      )
                    })}
                    
                    {depInfo.upstream.length > 0 && (
                      <div className="pt-2 border-t border-border mt-2">
                        <p className="text-xs text-muted-foreground mb-1">Depends on:</p>
                        <div className="flex flex-wrap gap-2">
                          {depInfo.upstream.map(upType => (
                            <span key={upType} className="text-xs px-2 py-1 bg-blue-500/10 text-blue-500 rounded">
                              {upType.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {depInfo.downstream.length > 0 && (
                      <div className="pt-2 border-t border-border mt-2">
                        <p className="text-xs text-muted-foreground mb-1">Affects:</p>
                        <div className="flex flex-wrap gap-2">
                          {depInfo.downstream.map(downType => (
                            <span key={downType} className="text-xs px-2 py-1 bg-green-500/10 text-green-500 rounded">
                              {downType.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
