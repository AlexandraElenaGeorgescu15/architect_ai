import { useState, useEffect, useCallback } from 'react'
import { 
  FolderGit2, Plus, Trash2, RefreshCw, Loader2, Check, AlertTriangle, 
  ExternalLink, Code2, Database, Globe 
} from 'lucide-react'
import api from '../services/api'

interface Repository {
  repo_id: string
  name: string
  path: string
  repo_type: 'frontend' | 'backend' | 'fullstack' | 'library' | 'other'
  language: string
  framework?: string
  indexed: boolean
  last_indexed?: string
  file_count: number
}

interface MultiRepoContext {
  repositories: Repository[]
  cross_repo_links: any[]
  technology_stack: Record<string, string[]>
  architecture_summary: string
}

const REPO_TYPES = [
  { value: 'frontend', label: 'Frontend', icon: Globe, color: 'text-blue-500' },
  { value: 'backend', label: 'Backend', icon: Database, color: 'text-green-500' },
  { value: 'fullstack', label: 'Full Stack', icon: Code2, color: 'text-purple-500' },
  { value: 'library', label: 'Library', icon: FolderGit2, color: 'text-orange-500' },
  { value: 'other', label: 'Other', icon: FolderGit2, color: 'text-gray-500' },
]

export default function MultiRepoManager() {
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [indexingRepo, setIndexingRepo] = useState<string | null>(null)
  
  // Form state
  const [newRepo, setNewRepo] = useState({
    name: '',
    path: '',
    repo_type: 'backend' as const,
    language: 'python',
    framework: ''
  })

  const loadRepositories = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.get<{ repositories: Repository[] }>('/api/multi-repo/repositories')
      setRepositories(response.data.repositories || [])
    } catch (err: any) {
      // If endpoint doesn't exist yet, show empty state
      if (err.response?.status === 404) {
        setRepositories([])
      } else {
        setError(err.response?.data?.detail || 'Failed to load repositories')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRepositories()
  }, [loadRepositories])

  const addRepository = async () => {
    if (!newRepo.name || !newRepo.path) {
      setError('Name and path are required')
      return
    }

    try {
      await api.post('/api/multi-repo/repositories', {
        ...newRepo,
        repo_id: newRepo.name.toLowerCase().replace(/\s+/g, '-')
      })
      setShowAddForm(false)
      setNewRepo({ name: '', path: '', repo_type: 'backend', language: 'python', framework: '' })
      loadRepositories()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add repository')
    }
  }

  const removeRepository = async (repoId: string) => {
    if (!confirm('Remove this repository from multi-repo analysis?')) return
    
    try {
      await api.delete(`/api/multi-repo/repositories/${repoId}`)
      loadRepositories()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove repository')
    }
  }

  const indexRepository = async (repoId: string) => {
    setIndexingRepo(repoId)
    try {
      await api.post(`/api/multi-repo/repositories/${repoId}/index`)
      loadRepositories()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to index repository')
    } finally {
      setIndexingRepo(null)
    }
  }

  const getRepoTypeInfo = (type: string) => {
    return REPO_TYPES.find(t => t.value === type) || REPO_TYPES[4]
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-destructive" />
          <span className="text-sm text-destructive">{error}</span>
        </div>
      )}

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Configure multiple repositories for cross-project architecture analysis
        </p>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Add Repository
        </button>
      </div>

      {showAddForm && (
        <div className="border border-border rounded-lg p-4 space-y-4 bg-secondary/20">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Repository Name</label>
              <input
                type="text"
                value={newRepo.name}
                onChange={(e) => setNewRepo({ ...newRepo, name: e.target.value })}
                placeholder="e.g., My Frontend"
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Path</label>
              <input
                type="text"
                value={newRepo.path}
                onChange={(e) => setNewRepo({ ...newRepo, path: e.target.value })}
                placeholder="e.g., C:/Projects/frontend"
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Type</label>
              <select
                value={newRepo.repo_type}
                onChange={(e) => setNewRepo({ ...newRepo, repo_type: e.target.value as any })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-sm"
              >
                {REPO_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Language</label>
              <select
                value={newRepo.language}
                onChange={(e) => setNewRepo({ ...newRepo, language: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-sm"
              >
                <option value="python">Python</option>
                <option value="typescript">TypeScript</option>
                <option value="javascript">JavaScript</option>
                <option value="csharp">C#</option>
                <option value="java">Java</option>
                <option value="go">Go</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Framework (Optional)</label>
              <input
                type="text"
                value={newRepo.framework}
                onChange={(e) => setNewRepo({ ...newRepo, framework: e.target.value })}
                placeholder="e.g., React, FastAPI"
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-sm"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={addRepository}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90"
            >
              Add Repository
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : repositories.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-lg">
          <FolderGit2 className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground mb-2">No repositories configured</p>
          <p className="text-xs text-muted-foreground">Add repositories to enable cross-project analysis</p>
        </div>
      ) : (
        <div className="space-y-2">
          {repositories.map((repo) => {
            const typeInfo = getRepoTypeInfo(repo.repo_type)
            const TypeIcon = typeInfo.icon
            return (
              <div
                key={repo.repo_id}
                className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-secondary/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg bg-secondary flex items-center justify-center ${typeInfo.color}`}>
                    <TypeIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{repo.name}</span>
                      <span className="text-xs px-2 py-0.5 bg-secondary rounded-full text-muted-foreground">
                        {repo.language}
                      </span>
                      {repo.framework && (
                        <span className="text-xs px-2 py-0.5 bg-primary/10 text-primary rounded-full">
                          {repo.framework}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{repo.path}</p>
                    <div className="flex items-center gap-3 mt-1">
                      {repo.indexed ? (
                        <span className="text-xs text-emerald-500 flex items-center gap-1">
                          <Check className="w-3 h-3" /> Indexed ({repo.file_count} files)
                        </span>
                      ) : (
                        <span className="text-xs text-amber-500 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> Not indexed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => indexRepository(repo.repo_id)}
                    disabled={indexingRepo === repo.repo_id}
                    className="p-2 hover:bg-secondary rounded-lg transition-colors disabled:opacity-50"
                    title="Index repository"
                  >
                    {indexingRepo === repo.repo_id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => removeRepository(repo.repo_id)}
                    className="p-2 hover:bg-destructive/10 text-destructive rounded-lg transition-colors"
                    title="Remove repository"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {repositories.length > 1 && (
        <div className="mt-4 p-4 border border-dashed border-primary/30 rounded-lg bg-primary/5">
          <div className="flex items-center gap-2 text-primary">
            <ExternalLink className="w-4 h-4" />
            <span className="text-sm font-medium">Cross-Repository Analysis Available</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            With multiple repositories configured, you can generate unified architecture diagrams
            and detect cross-repository dependencies. Use the generation panel with "Multi-Repo" context enabled.
          </p>
        </div>
      )}
    </div>
  )
}
