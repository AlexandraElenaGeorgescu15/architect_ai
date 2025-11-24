import { useEffect, useState } from 'react'
import { useModelStore } from '../stores/modelStore'
import { useTrainingStore } from '../stores/trainingStore'
import { useTraining } from '../hooks/useTraining'
import { listModels } from '../services/modelService'
import { listTrainingJobs, triggerTraining } from '../services/trainingService'
import ModelMapping from '../components/ModelMapping'
import { Loader2, Brain, Database, Play, RefreshCw, Network, Search as SearchIcon, Sparkles, Trash2, GraduationCap, AlertCircle, CheckCircle, TrendingUp } from 'lucide-react'
import KnowledgeGraphViewer from '../components/KnowledgeGraphViewer'
import PatternMiningResults from '../components/PatternMiningResults'
import { generateSyntheticData, getAllStats, clearSynthetic, SyntheticStats } from '../services/syntheticDataService'
import { useUIStore } from '../stores/uiStore'

export default function Intelligence() {
  const { models, setModels } = useModelStore()
  const { jobs, setJobs, getActiveJobs } = useTrainingStore()
  const { isTraining, progress, startTraining, refreshJobs } = useTraining()
  const [isLoading, setIsLoading] = useState(true)
  const [selectedProvider, setSelectedProvider] = useState<'all' | 'ollama' | 'cloud'>('all')
  const [showUnconfiguredModels, setShowUnconfiguredModels] = useState(false)
  
  // Universal Context state
  const [universalContextStatus, setUniversalContextStatus] = useState<any>(null)
  const [isLoadingUniversalContext, setIsLoadingUniversalContext] = useState(false)
  
  // Knowledge Graph and Pattern Mining state
  const [kgData, setKgData] = useState<any>(null)
  const [pmData, setPmData] = useState<any>(null)
  const [isLoadingKG, setIsLoadingKG] = useState(false)
  const [isLoadingPM, setIsLoadingPM] = useState(false)
  
  // Synthetic data state
  const [syntheticStats, setSyntheticStats] = useState<Record<string, SyntheticStats> | null>(null)
  const [isGenerating, setIsGenerating] = useState<string | null>(null)
  const { addNotification } = useUIStore()

  useEffect(() => {
    loadData()
    loadUniversalContext()
    loadKnowledgeGraph()
    loadPatternMining()
    loadSyntheticStats()
  }, [])
  
  const loadUniversalContext = async () => {
    setIsLoadingUniversalContext(true)
    try {
      const response = await fetch('/api/universal-context/status')
      if (response.ok) {
        const data = await response.json()
        setUniversalContextStatus(data)
      }
    } catch (error) {
      console.error('Failed to load Universal Context status:', error)
    } finally {
      setIsLoadingUniversalContext(false)
    }
  }
  
  const rebuildUniversalContext = async () => {
    setIsLoadingUniversalContext(true)
    try {
      const response = await fetch('/api/universal-context/rebuild', { method: 'POST' })
      if (response.ok) {
        addNotification({
          id: Date.now().toString(),
          type: 'success',
          message: 'Universal Context rebuild started. This will take a few moments...'
        })
        // Poll for completion
        setTimeout(() => loadUniversalContext(), 5000)
      }
    } catch (error) {
      addNotification({
        id: Date.now().toString(),
        type: 'error',
        message: 'Failed to rebuild Universal Context'
      })
    } finally {
      setIsLoadingUniversalContext(false)
    }
  }
  
  const loadKnowledgeGraph = async () => {
    setIsLoadingKG(true)
    try {
      // Call backend API to get knowledge graph
      const response = await fetch('/api/knowledge-graph/current')
      if (response.ok) {
        const data = await response.json()
        setKgData(data)
      }
    } catch (error) {
      // Failed to load KG
    } finally {
      setIsLoadingKG(false)
    }
  }
  
  const loadPatternMining = async () => {
    setIsLoadingPM(true)
    try {
      // Call backend API to get pattern mining results
      const response = await fetch('/api/analysis/patterns/current')
      if (response.ok) {
        const data = await response.json()
        setPmData(data)
      }
    } catch (error) {
      // Failed to load PM
    } finally {
      setIsLoadingPM(false)
    }
  }
  
  const loadSyntheticStats = async () => {
    try {
      const stats = await getAllStats()
      setSyntheticStats(stats)
    } catch (error) {
      // Failed to load synthetic stats
    }
  }
  
  const handleGenerateBootstrap = async (artifactType: string) => {
    setIsGenerating(artifactType)
    try {
      const result = await generateSyntheticData({
        artifact_type: artifactType,
        target_count: 50,
        model_backend: 'auto',
        complexity: 'Mixed',
        auto_integrate: true
      })
      
      if (result.success) {
        addNotification('success', `Generated ${result.generated_count} ${artifactType} examples using ${result.backend_used}!`)
        await loadSyntheticStats()
      } else {
        addNotification('error', `Failed to generate synthetic data: ${result.errors.join(', ')}`)
      }
    } catch (error: any) {
      addNotification('error', `Error: ${error.message}`)
    } finally {
      setIsGenerating(null)
    }
  }
  
  const handleClearSynthetic = async (artifactType: string) => {
    if (!confirm(`Remove all synthetic examples for ${artifactType}? This will keep only real feedback examples.`)) {
      return
    }
    
    try {
      const result = await clearSynthetic(artifactType)
      if (result.success) {
        addNotification('success', `Removed ${result.removed_count} synthetic examples. ${result.remaining_count} real examples remain.`)
        await loadSyntheticStats()
      }
    } catch (error: any) {
      addNotification('error', `Failed to clear synthetic data: ${error.message}`)
    }
  }

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [modelsData, jobsData] = await Promise.all([
        listModels(),
        listTrainingJobs(),
      ])
      setModels(modelsData)
      setJobs(jobsData)
    } catch (error) {
      // Failed to load data
    } finally {
      setIsLoading(false)
    }
  }

  const handleTriggerTraining = async () => {
    try {
      await startTraining()
      await refreshJobs()
    } catch (error) {
      // Failed to trigger training
    }
  }

  // First filter by provider
  let filteredModels = selectedProvider === 'all'
    ? models
    : selectedProvider === 'cloud'
      ? models.filter(m => m.provider !== 'ollama') // Cloud = anything that's not Ollama
      : models.filter(m => m.provider === selectedProvider)
  
  // Then filter by API key status (unless user wants to see unconfigured models)
  if (!showUnconfiguredModels) {
    filteredModels = filteredModels.filter(m => m.status !== 'no_api_key')
  }
  
  // Separate available and unconfigured models for display
  const availableModels = filteredModels.filter(m => m.status !== 'no_api_key')
  const unconfiguredModels = models.filter(m => m.status === 'no_api_key')

  const activeJobs = getActiveJobs()
  const completedJobs = jobs.filter(j => j.status === 'completed')

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-6 space-y-6">
      {/* Header with Stats */}
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Brain className="w-8 h-8" />
          Intelligence
        </h1>
        <p className="text-foreground mt-2">
          AI models, knowledge graph, pattern mining, and training
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel rounded-2xl p-6 text-center hover:border-primary/30 transition-all">
          <div className="text-4xl font-black text-foreground mb-2">{availableModels.length}</div>
          <div className="text-xs font-bold text-foreground uppercase tracking-widest">Available Models</div>
          {unconfiguredModels.length > 0 && (
            <div className="text-xs text-muted-foreground mt-1">
              +{unconfiguredModels.length} need config
            </div>
          )}
        </div>
        <div className="glass-panel rounded-2xl p-6 text-center hover:border-primary/30 transition-all">
          <div className="text-4xl font-black text-foreground mb-2">{activeJobs.length}</div>
          <div className="text-xs font-bold text-foreground uppercase tracking-widest">Active Training</div>
        </div>
        <div className="glass-panel rounded-2xl p-6 text-center hover:border-primary/30 transition-all">
          <div className="text-4xl font-black text-foreground mb-2">{kgData?.components?.length || 0}</div>
          <div className="text-xs font-bold text-foreground uppercase tracking-widest">KG Components</div>
        </div>
        <div className="glass-panel rounded-2xl p-6 text-center hover:border-primary/30 transition-all">
          <div className="text-4xl font-black text-foreground mb-2">{pmData?.patterns?.length || 0}</div>
          <div className="text-xs font-bold text-foreground uppercase tracking-widest">Patterns Found</div>
        </div>
      </div>

      {/* 🚀 Universal Context Section - The Powerhouse! */}
      <div className="glass-panel rounded-2xl p-8 border-2 border-primary/30 bg-gradient-to-br from-primary/5 to-primary/10">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-lg">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-2xl font-bold text-foreground">Universal Context</h2>
                <span className="px-2 py-0.5 bg-primary text-white text-xs font-bold rounded uppercase">Powerhouse</span>
              </div>
              <p className="text-sm text-foreground mt-1">Knows your entire project by heart - baseline context for everything</p>
            </div>
          </div>
          <button
            onClick={rebuildUniversalContext}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors font-medium"
            disabled={isLoadingUniversalContext}
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingUniversalContext ? 'animate-spin' : ''}`} />
            Rebuild
          </button>
        </div>
        
        {isLoadingUniversalContext && !universalContextStatus ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : universalContextStatus ? (
          <div className="space-y-6">
            {/* Status Banner */}
            <div className="flex items-center gap-3 bg-green-500/10 border border-green-500/30 rounded-xl p-4">
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-sm font-bold text-foreground">Universal Context Active</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  Built {universalContextStatus.built_at ? new Date(universalContextStatus.built_at).toLocaleString() : 'recently'}
                  {universalContextStatus.build_duration_seconds && ` in ${universalContextStatus.build_duration_seconds.toFixed(1)}s`}
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-card/50 rounded-xl p-4 border border-border/50">
                <div className="text-3xl font-bold text-primary mb-1">{universalContextStatus.total_files || 0}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-wider">Files Indexed</div>
              </div>
              <div className="bg-card/50 rounded-xl p-4 border border-border/50">
                <div className="text-3xl font-bold text-primary mb-1">{universalContextStatus.kg_nodes || 0}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-wider">KG Nodes</div>
              </div>
              <div className="bg-card/50 rounded-xl p-4 border border-border/50">
                <div className="text-3xl font-bold text-primary mb-1">{universalContextStatus.patterns_found || 0}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-wider">Patterns</div>
              </div>
              <div className="bg-card/50 rounded-xl p-4 border border-border/50">
                <div className="text-3xl font-bold text-primary mb-1">{universalContextStatus.key_entities_count || 0}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-wider">Key Entities</div>
              </div>
            </div>

            {/* Project Directories */}
            {universalContextStatus.project_directories && universalContextStatus.project_directories.length > 0 && (
              <div className="bg-card/30 rounded-xl p-4 border border-border/50">
                <div className="text-sm font-bold text-foreground mb-3 flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Project Directories Indexed
                </div>
                <div className="space-y-2">
                  {universalContextStatus.project_directories.map((dir: string, idx: number) => (
                    <div key={idx} className="text-xs font-mono text-muted-foreground bg-card/50 px-3 py-2 rounded border border-border/30">
                      {dir}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Info Box */}
            <div className="flex items-start gap-3 bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
              <AlertCircle className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-foreground">
                <div className="font-semibold mb-1">What is Universal Context?</div>
                <div className="text-xs text-muted-foreground leading-relaxed">
                  The Universal Context is the <span className="font-bold text-primary">RAG Powerhouse</span> that indexes and knows your <span className="font-bold">entire project by heart</span>.
                  It provides baseline context to: floating chat, knowledge graph, pattern mining, artifact generation, and everything else.
                  Files are ranked by importance (main workflow &gt; utilities &gt; UI components) to prioritize the most relevant code.
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="text-muted-foreground text-sm">Universal Context not yet built</div>
            <button
              onClick={rebuildUniversalContext}
              className="mt-4 px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
            >
              Build Now
            </button>
          </div>
        )}
      </div>

      {/* Knowledge Graph Section */}
      <div className="glass-panel rounded-2xl p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
              <Network className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Knowledge Graph</h2>
              <p className="text-xs text-foreground uppercase tracking-wider">Project Structure & Relationships</p>
            </div>
          </div>
          <button
            onClick={loadKnowledgeGraph}
            className="p-2 border border-border rounded-lg hover:bg-primary/10 transition-colors"
            disabled={isLoadingKG}
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingKG ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <KnowledgeGraphViewer data={kgData} isLoading={isLoadingKG} />
      </div>

      {/* Pattern Mining Section */}
      <div className="glass-panel rounded-2xl p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center border border-accent/20">
              <SearchIcon className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Pattern Mining</h2>
              <p className="text-xs text-foreground uppercase tracking-wider">Design Patterns Detected</p>
            </div>
          </div>
          <button
            onClick={loadPatternMining}
            className="p-2 border border-border rounded-lg hover:bg-accent/10 transition-colors"
            disabled={isLoadingPM}
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingPM ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <PatternMiningResults data={pmData} isLoading={isLoadingPM} />
      </div>

      {/* Training Data Management Section - INTEGRATED */}
      {syntheticStats && (
        <div className="glass-panel rounded-2xl p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center border border-primary/30">
                <Database className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Training Data Management</h2>
                <p className="text-xs text-muted-foreground">Real feedback examples + synthetic bootstrap data</p>
              </div>
            </div>
            <button
              onClick={loadSyntheticStats}
              className="p-2 border border-border rounded-lg hover:bg-primary/10 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(syntheticStats).map(([artifactType, stats]) => (
              <div
                key={artifactType}
                className={`bg-card border rounded-lg p-4 transition-all ${
                  stats.ready_for_training
                    ? 'border-green-500/30 bg-green-500/5'
                    : stats.needs_bootstrap
                    ? 'border-yellow-500/30 bg-yellow-500/5'
                    : 'border-border'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="font-semibold text-foreground capitalize text-sm">
                      {artifactType.replace(/_/g, ' ')}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      {stats.ready_for_training ? (
                        <CheckCircle className="w-3 h-3 text-green-500" />
                      ) : stats.needs_bootstrap ? (
                        <AlertCircle className="w-3 h-3 text-yellow-500" />
                      ) : (
                        <TrendingUp className="w-3 h-3 text-blue-500" />
                      )}
                      <span className="text-xs text-muted-foreground">
                        {stats.ready_for_training
                          ? 'Ready to train'
                          : stats.needs_bootstrap
                          ? 'Bootstrap recommended'
                          : 'Collecting data'}
                      </span>
                    </div>
                  </div>
                  {stats.ready_for_graduation && (
                    <GraduationCap className="w-4 h-4 text-purple-500" title="Ready to graduate to pure feedback data" />
                  )}
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Real (feedback):</span>
                    <span className="font-mono font-semibold text-green-500">{stats.real_examples}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Synthetic:</span>
                    <span className="font-mono font-semibold text-blue-500">{stats.synthetic_examples}</span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-border">
                    <span className="text-foreground font-medium">Total:</span>
                    <span className="font-mono font-bold text-foreground">{stats.total_examples}/50</span>
                  </div>
                  {stats.synthetic_percentage > 0 && (
                    <div className="text-[10px] text-muted-foreground">
                      {stats.synthetic_percentage}% synthetic
                    </div>
                  )}
                </div>

                <div className="mt-4 flex flex-col gap-2">
                  {stats.needs_bootstrap && (
                    <button
                      onClick={() => handleGenerateBootstrap(artifactType)}
                      disabled={isGenerating === artifactType}
                      className="w-full py-2 px-3 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 text-primary-foreground rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isGenerating === artifactType ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3 h-3" />
                          Generate Bootstrap ({50 - stats.total_examples})
                        </>
                      )}
                    </button>
                  )}

                  {stats.ready_for_graduation && stats.synthetic_examples > 0 && (
                    <button
                      onClick={() => handleClearSynthetic(artifactType)}
                      className="w-full py-2 px-3 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 border border-purple-500/30 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 transition-all"
                    >
                      <GraduationCap className="w-3 h-3" />
                      Graduate ({stats.real_examples} real)
                    </button>
                  )}

                  {stats.synthetic_examples > 0 && !stats.ready_for_graduation && (
                    <button
                      onClick={() => handleClearSynthetic(artifactType)}
                      className="w-full py-1.5 px-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-[10px] font-medium flex items-center justify-center gap-1 transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                      Clear Synthetic
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model Mapping - Consolidated HuggingFace Search */}
      <ModelMapping />

      {/* Models and Training Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Models Section */}
        <div className="glass-panel rounded-2xl p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center border border-accent/20">
                <Database className="w-5 h-5 text-accent" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Models</h2>
                <p className="text-xs text-foreground uppercase tracking-wider">Available AI Models</p>
              </div>
            </div>
            <div className="flex gap-2">
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value as any)}
                className="px-3 py-1.5 border border-border rounded-lg bg-card text-foreground text-sm"
              >
                <option value="all">All Providers</option>
                <option value="ollama">Ollama</option>
                <option value="cloud">Cloud</option>
              </select>
              <button
                onClick={loadData}
                className="p-1.5 border border-border rounded-lg hover:bg-primary/10"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {unconfiguredModels.length > 0 && (
            <div className="mb-4 flex items-center gap-2 text-sm">
              <label className="flex items-center gap-2 text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                <input
                  type="checkbox"
                  checked={showUnconfiguredModels}
                  onChange={(e) => setShowUnconfiguredModels(e.target.checked)}
                  className="w-4 h-4 rounded border-border text-primary focus:ring-2 focus:ring-primary/50"
                />
                Show models needing API keys ({unconfiguredModels.length})
              </label>
            </div>
          )}

          <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
            {filteredModels.length === 0 ? (
              <div className="text-center py-8 text-foreground">
                <p>No models found</p>
                <p className="text-xs mt-2 text-foreground">
                  {selectedProvider === 'cloud' 
                    ? 'Cloud models will appear when API keys are configured.'
                    : selectedProvider === 'ollama'
                    ? 'Ollama models will appear when Ollama is running.'
                    : 'Make sure API keys are configured or Ollama is running'}
                </p>
              </div>
            ) : (
              filteredModels.map((model) => (
                <div
                  key={model.id}
                  className="p-4 border border-border rounded-lg hover:bg-primary/5 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex-1">
                      <span className="font-medium text-foreground">{model.name}</span>
                      {model.status === 'no_api_key' && (
                        <span className="ml-2 text-xs text-foreground">
                          (API key needed)
                        </span>
                      )}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded ${
                      model.status === 'available' ? 'bg-green-500/20 text-green-500' :
                      model.status === 'downloading' ? 'bg-yellow-500/20 text-yellow-500' :
                      model.status === 'no_api_key' ? 'bg-yellow-500/20 text-yellow-500' :
                      'bg-red-500/20 text-red-500'
                    }`}>
                      {model.status === 'no_api_key' ? 'API Key Needed' : model.status}
                    </span>
                  </div>
                  <div className="text-sm text-foreground">
                    Provider: {model.provider}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Training Section */}
        <div className="glass-panel rounded-2xl p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
                <Play className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Training</h2>
                <p className="text-xs text-foreground uppercase tracking-wider">Model Fine-tuning</p>
              </div>
            </div>
            <button
              onClick={handleTriggerTraining}
              disabled={isTraining}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isTraining ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {isTraining ? 'Training...' : 'Start Training'}
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-semibold mb-2 text-foreground">Active Jobs</h3>
              {activeJobs.length === 0 ? (
                <p className="text-sm text-foreground">No active training jobs</p>
              ) : (
                <div className="space-y-2">
                  {activeJobs.map((job) => (
                    <div key={job.id} className="p-3 border border-border rounded-lg bg-primary/5">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-foreground">{job.artifact_type}</span>
                        <span className="text-xs text-foreground">{job.status}</span>
                      </div>
                      {job.progress !== undefined && (
                        <div className="mt-2 h-2 bg-background rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-primary transition-all" 
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-2 text-foreground">Completed Jobs ({completedJobs.length})</h3>
              <div className="text-sm text-foreground">
                Successfully completed training jobs
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

