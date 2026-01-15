/**
 * Project Indicator - Shows which projects are being indexed by RAG
 * 
 * This is a read-only indicator that shows all projects automatically indexed.
 * RAG indexes ALL projects in the parent directory (except Architect.AI itself).
 */

import { useState, useEffect } from 'react'
import { Folder, FolderOpen, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react'
import { getProjectInfo, clearAnalysisCache, ProjectInfo } from '../../services/projectService'
import { useUIStore } from '../../stores/uiStore'

export default function ProjectIndicator() {
  const [projects, setProjects] = useState<ProjectInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isExpanded, setIsExpanded] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const { addNotification } = useUIStore()

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setIsLoading(true)
    try {
      const data = await getProjectInfo()
      setProjects(data.available_projects)
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearCache = async () => {
    setIsClearing(true)
    try {
      const result = await clearAnalysisCache()
      if (result.success) {
        addNotification('success', `Cleared ${result.cleared_files.length} cache files. Rebuild Universal Context to re-analyze.`)
      }
    } catch (error) {
      addNotification('error', 'Failed to clear cache')
    } finally {
      setIsClearing(false)
    }
  }

  // Get marker badge color
  const getMarkerColor = (marker: string) => {
    const colors: Record<string, string> = {
      'Angular': 'bg-red-500/20 text-red-500',
      'Node.js': 'bg-green-500/20 text-green-500',
      'Python': 'bg-blue-500/20 text-blue-500',
      '.NET': 'bg-purple-500/20 text-purple-500',
      '.NET Solution': 'bg-purple-500/20 text-purple-500',
      'Maven': 'bg-orange-500/20 text-orange-500',
      'Gradle': 'bg-orange-500/20 text-orange-500',
      'Rust': 'bg-amber-500/20 text-amber-500',
      'Go': 'bg-cyan-500/20 text-cyan-500',
    }
    return colors[marker] || 'bg-muted text-muted-foreground'
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span>Loading projects...</span>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Compact indicator button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-card/50 hover:bg-card hover:border-primary/30 transition-all text-sm group"
        title={`${projects.length} projects indexed by RAG`}
      >
        {isExpanded ? (
          <FolderOpen className="w-4 h-4 text-primary" />
        ) : (
          <Folder className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        )}
        <span className="font-medium text-foreground">
          {projects.length} {projects.length === 1 ? 'Project' : 'Projects'}
        </span>
        <CheckCircle className="w-3.5 h-3.5 text-green-500" />
      </button>

      {/* Expanded dropdown showing all projects */}
      {isExpanded && (
        <div className="absolute top-full left-0 mt-2 w-80 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-muted/30 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Indexed Projects</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  RAG automatically indexes all projects
                </p>
              </div>
              <button
                onClick={handleClearCache}
                disabled={isClearing}
                className="p-1.5 rounded-lg hover:bg-primary/10 transition-colors"
                title="Clear analysis cache"
              >
                <RefreshCw className={`w-4 h-4 text-muted-foreground ${isClearing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Project list */}
          <div className="max-h-64 overflow-y-auto">
            {projects.length === 0 ? (
              <div className="px-4 py-6 text-center">
                <AlertCircle className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No projects found</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Place projects in the same directory as Architect.AI
                </p>
              </div>
            ) : (
              <div className="py-2">
                {projects.map((project, idx) => (
                  <div
                    key={project.path}
                    className="px-4 py-2.5 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Folder className="w-4 h-4 text-primary flex-shrink-0" />
                      <span className="font-medium text-sm text-foreground truncate">
                        {project.name}
                      </span>
                    </div>
                    
                    {/* Project markers/badges */}
                    {project.markers.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5 ml-6">
                        {project.markers.slice(0, 4).map((marker, mIdx) => (
                          <span
                            key={mIdx}
                            className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${getMarkerColor(marker)}`}
                          >
                            {marker}
                          </span>
                        ))}
                        {project.markers.length > 4 && (
                          <span className="px-1.5 py-0.5 text-[10px] text-muted-foreground">
                            +{project.markers.length - 4} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2.5 bg-muted/20 border-t border-border">
            <p className="text-[10px] text-muted-foreground text-center">
              💡 All projects are indexed automatically. Rebuild Universal Context to refresh.
            </p>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isExpanded && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsExpanded(false)}
        />
      )}
    </div>
  )
}
