import { useState, useEffect, useCallback, useMemo } from 'react'
import { useModelStore } from '../stores/modelStore'
import { useUIStore } from '../stores/uiStore'
import api from '../services/api'
import { downloadHuggingFaceModel, getDownloadStatus } from '../services/huggingfaceService'
import { Settings, Save, RefreshCw, Download, Search, Loader2, Plus, Trash2, Sparkles, CheckCircle } from 'lucide-react'

interface ModelRouting {
  artifact_type: string
  primary_model: string
  fallback_models: string[]
  enabled: boolean
}

interface AISuggestion {
  suggested_primary: string | null
  suggested_fallbacks: string[]
  reasoning: string
  confidence: number
}

export default function ModelMapping() {
  const { models, fetchModels } = useModelStore()
  const { addNotification } = useUIStore()
  const [routings, setRoutings] = useState<Record<string, ModelRouting>>({})
  const [loading, setLoading] = useState(false)
  const [routingFilter, setRoutingFilter] = useState('')  // Filter for routing table
  const [huggingfaceQuery, setHuggingfaceQuery] = useState('')  // Search query for HuggingFace
  const [huggingfaceResults, setHuggingfaceResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)
  const [downloadingModels, setDownloadingModels] = useState<Set<string>>(new Set())
  const [isAutoRefreshing, setIsAutoRefreshing] = useState(false)
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)  // Track unsaved changes
  const [initialRoutings, setInitialRoutings] = useState<Record<string, ModelRouting>>({})  // Track original state
  const [suggestingFor, setSuggestingFor] = useState<string | null>(null)  // Track which artifact is being suggested
  const [suggestions, setSuggestions] = useState<Record<string, AISuggestion>>({})  // Store AI suggestions

  // Check if there are any unavailable configured models
  const hasUnavailableModels = useMemo(() => {
    const ollamaModels = models.filter(m => m.provider === 'ollama')
    const huggingfaceModels = models.filter(m => m.provider === 'huggingface' && (m.status === 'downloaded' || m.status === 'available'))
    const cloudModels = models.filter(m => m.provider !== 'ollama' && m.provider !== 'huggingface' && m.status === 'available')
    
    return Object.values(routings).some(routing => {
      if (!routing.primary_model) return false
      return !ollamaModels.some(m => m.id === routing.primary_model) && 
             !huggingfaceModels.some(m => m.id === routing.primary_model) &&
             !cloudModels.some(m => m.id === routing.primary_model)
    })
  }, [routings, models])

  // Load data on mount and set up periodic model refresh (not routing refresh!)
  // Routing should only refresh on manual action to prevent overwriting user changes
  useEffect(() => {
    loadRoutings()
    fetchModels()
    
    // Only refresh models periodically (60 seconds) - NOT routings
    // User's routing changes should persist until they manually refresh
    const interval = setInterval(async () => {
      setIsAutoRefreshing(true)
      await fetchModels()
      // DON'T refresh routings automatically - this was overwriting user changes
      setIsAutoRefreshing(false)
    }, 60000) // 60 seconds - less aggressive
    
    // On visibility change, only refresh models (not routings)
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        setIsAutoRefreshing(true)
        fetchModels().finally(() => {
          setIsAutoRefreshing(false)
        })
      }
    }
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadRoutings = async () => {
    try {
      const response = await api.get('/api/models/routing')
      // Backend returns Dict[str, ModelRoutingDTO], convert to our format
      const routingDict: Record<string, ModelRouting> = {}
      Object.entries(response.data).forEach(([artifactType, routing]: [string, any]) => {
        routingDict[artifactType] = {
          artifact_type: artifactType,
          primary_model: routing.primary_model || '',
          fallback_models: routing.fallback_models || [],
          enabled: routing.enabled !== false
        }
      })
      setRoutings(routingDict)
      setInitialRoutings(routingDict)  // Track initial state for change detection
      setHasUnsavedChanges(false)  // Reset unsaved changes flag
    } catch (error) {
      console.error('Failed to load model routing:', error)
      // Don't show notification on initial load - silent degradation
    }
  }

  const handleManualRefresh = async () => {
    setIsAutoRefreshing(true)
    try {
      await Promise.all([fetchModels(), loadRoutings()])
      addNotification('success', 'Models refreshed successfully')
    } catch (error) {
      addNotification('error', 'Failed to refresh models')
    } finally {
      setIsAutoRefreshing(false)
    }
  }

  const saveRoutings = async () => {
    setLoading(true)
    try {
      // Convert to format expected by backend: List[ModelRoutingDTO]
      const routingList = Object.entries(routings).map(([artifactType, routing]) => ({
        artifact_type: artifactType, // Backend will convert string to ArtifactType enum
        primary_model: routing.primary_model,
        fallback_models: routing.fallback_models.filter(m => m.trim() !== ''),
        enabled: routing.enabled
      }))
      
      await api.put('/api/models/routing', { routings: routingList })
      addNotification('success', 'Model routing saved! Your preferences are now persisted.')
      setHasUnsavedChanges(false)  // Reset unsaved changes flag
      setInitialRoutings({ ...routings })  // Update initial state to current (deep copy)
      
      // DON'T reload immediately after saving - this was causing race conditions
      // where the file hadn't been fully written yet. Trust the save was successful.
      // The periodic refresh (30s when models are available) will sync if needed.
    } catch (error: any) {
      // Failed to save routings - show user error
      addNotification('error', error?.response?.data?.detail || 'Failed to save model routing')
    } finally {
      setLoading(false)
    }
  }

  const searchHuggingface = async () => {
    if (!huggingfaceQuery.trim()) return
    
    console.log('🔎 [HUGGINGFACE] Searching models for query:', huggingfaceQuery)
    setSearching(true)
    try {
      const response = await api.get('/api/huggingface/search', {
        params: { query: huggingfaceQuery, limit: 10 }
      })
      // Guard against unexpected API response shape to prevent crashes
      const data = response?.data
      const results = Array.isArray(data?.results) ? data.results : []
      setHuggingfaceResults(results)
      if (!Array.isArray(data?.results)) {
        console.warn('[ModelMapping] Unexpected HuggingFace response shape:', data)
      }
      console.log('🔎 [HUGGINGFACE] Search results:', data)
      addNotification('info', `Found ${results.length} models for "${huggingfaceQuery}"`)
    } catch (error: any) {
      console.error('❌ [HUGGINGFACE] Search failed:', error)
      const status = error?.response?.status
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Failed to search HuggingFace'

      // Surface rate-limit and server errors so user understands why nothing changed
      if (status === 429) {
        addNotification('warning', 'HuggingFace search rate limit reached (10/min). Please wait a bit.')
      } else {
        addNotification('error', `HuggingFace search error: ${detail}`)
      }
    } finally {
      setSearching(false)
    }
  }

  const downloadModel = useCallback(async (modelId: string) => {
    // Prevent duplicate downloads
    if (downloadingModels.has(modelId)) {
      addNotification('info', `Download already in progress for ${modelId}`)
      return
    }
    
    try {
      // Mark as downloading
      setDownloadingModels(prev => new Set(prev).add(modelId))
      addNotification('info', `Starting download for ${modelId}...`)
      
      // Use the service function which handles URL encoding
      const result = await downloadHuggingFaceModel(modelId, true)
      
      if (result.success) {
        addNotification('info', `Download started for ${modelId}. This may take several minutes.`)
        
        // Poll for download status with progress updates
        // Timeout after 30 minutes (360 polls at 5 second intervals)
        let pollCount = 0
        const maxPolls = 360
        
        const checkStatus = async () => {
          pollCount++
          
          // Timeout protection
          if (pollCount > maxPolls) {
            addNotification('warning', `Download for ${modelId} is taking longer than expected. Check the Intelligence page later.`)
            setDownloadingModels(prev => {
              const next = new Set(prev)
              next.delete(modelId)
              return next
            })
            return
          }
          
          try {
            const status = await getDownloadStatus(modelId)
            
            if (status.status === 'completed') {
              addNotification('success', `Model ${modelId} downloaded successfully!`)
              setDownloadingModels(prev => {
                const next = new Set(prev)
                next.delete(modelId)
                return next
              })
              fetchModels() // Refresh model list
            } else if (status.status === 'failed') {
              addNotification('error', `Download failed: ${status.error || 'Unknown error'}`)
              setDownloadingModels(prev => {
                const next = new Set(prev)
                next.delete(modelId)
                return next
              })
            } else if (status.status === 'downloading') {
              // Show progress if available
              if (status.progress > 0) {
                console.log(`📥 [HF_DOWNLOAD] ${modelId}: ${Math.round(status.progress * 100)}%`)
              }
              // Check again in 5 seconds
              setTimeout(checkStatus, 5000)
            } else {
              // Unknown status or not_started, check again
              setTimeout(checkStatus, 3000)
            }
          } catch (error) {
            console.error('Error checking download status:', error)
            // Don't stop polling on temporary errors, but count them
            setTimeout(checkStatus, 5000)
          }
        }
        
        // Start checking status after 2 seconds
        setTimeout(checkStatus, 2000)
      } else {
        addNotification('error', `Download failed: ${result.error || 'Unknown error'}`)
        setDownloadingModels(prev => {
          const next = new Set(prev)
          next.delete(modelId)
          return next
        })
      }
    } catch (error: any) {
      // Improve error message for timeouts vs real backend errors
      const isTimeout = error?.code === 'ECONNABORTED' || /timeout/i.test(error?.message || '')
      const errorMsg =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        (isTimeout ? 'Request timed out. The backend may still be downloading in background.' : error?.message) ||
        'Failed to start download'

      addNotification('error', `Download error: ${errorMsg}`)
      console.error('Download error:', error)
      setDownloadingModels(prev => {
        const next = new Set(prev)
        next.delete(modelId)
        return next
      })
    }
  }, [downloadingModels, addNotification, fetchModels])

  const updateRouting = (artifactType: string, field: keyof ModelRouting, value: any) => {
    setRoutings(prev => ({
      ...prev,
      [artifactType]: {
        ...prev[artifactType],
        [field]: value
      }
    }))
    setHasUnsavedChanges(true)  // Mark as having unsaved changes
  }

  // Get AI suggestion for model routing
  const getAISuggestion = useCallback(async (artifactType: string) => {
    setSuggestingFor(artifactType)
    try {
      const response = await api.post('/api/models/suggest-routing', null, {
        params: { artifact_type: artifactType }
      })
      
      if (response.data.success) {
        const suggestion: AISuggestion = {
          suggested_primary: response.data.suggested_primary,
          suggested_fallbacks: response.data.suggested_fallbacks || [],
          reasoning: response.data.reasoning,
          confidence: response.data.confidence
        }
        setSuggestions(prev => ({ ...prev, [artifactType]: suggestion }))
        addNotification('success', `AI suggests: ${suggestion.suggested_primary || 'No primary model'} (${Math.round(suggestion.confidence * 100)}% confidence)`)
      } else {
        addNotification('error', response.data.error || 'Failed to get AI suggestion')
      }
    } catch (error: any) {
      console.error('AI suggestion error:', error)
      addNotification('error', error?.response?.data?.detail || 'Failed to get AI suggestion')
    } finally {
      setSuggestingFor(null)
    }
  }, [addNotification])

  // Apply AI suggestion to routing
  const applySuggestion = useCallback((artifactType: string) => {
    const suggestion = suggestions[artifactType]
    if (!suggestion) return
    
    setRoutings(prev => ({
      ...prev,
      [artifactType]: {
        ...prev[artifactType],
        primary_model: suggestion.suggested_primary || prev[artifactType]?.primary_model || '',
        fallback_models: suggestion.suggested_fallbacks.length > 0 
          ? suggestion.suggested_fallbacks 
          : prev[artifactType]?.fallback_models || []
      }
    }))
    setHasUnsavedChanges(true)
    addNotification('success', `Applied AI suggestion for ${artifactType.replace(/_/g, ' ')}`)
    
    // Clear the suggestion after applying
    setSuggestions(prev => {
      const newSuggestions = { ...prev }
      delete newSuggestions[artifactType]
      return newSuggestions
    })
  }, [suggestions, addNotification])

  const filteredRoutings = Object.entries(routings).filter(([type]) =>
    type.toLowerCase().includes(routingFilter.toLowerCase())
  )

  const ollamaModels = models.filter(m => m.provider === 'ollama')
  const huggingfaceModels = models.filter(m => m.provider === 'huggingface' && (m.status === 'downloaded' || m.status === 'available'))
  const cloudModels = models.filter(m => m.provider !== 'ollama' && m.provider !== 'huggingface' && m.status === 'available')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Model-to-Artifact Mapping</h2>
          <p className="text-muted-foreground mt-1">
            Configure which models to use for each artifact type
            {hasUnavailableModels && (
              <span className="ml-2 text-xs text-muted-foreground">
                (Some local models may not be detected - cloud fallbacks will be used)
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2 items-center">
          {hasUnsavedChanges && (
            <span className="text-xs text-yellow-600 dark:text-yellow-500 font-medium">
              ⚠️ Unsaved changes
            </span>
          )}
          <button
            onClick={handleManualRefresh}
            disabled={isAutoRefreshing || hasUnsavedChanges}
            className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 flex items-center gap-2 disabled:opacity-50"
            title={hasUnsavedChanges ? 'Save changes before refreshing' : (hasUnavailableModels ? 'Auto-refreshing every 10 seconds (unavailable models detected)' : 'Auto-refreshing every 30 seconds')}
          >
            <RefreshCw className={`w-4 h-4 ${isAutoRefreshing ? 'animate-spin' : ''}`} />
            {isAutoRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button
            onClick={saveRoutings}
            disabled={loading || !hasUnsavedChanges}
            className={`px-4 py-2 rounded-md flex items-center gap-2 disabled:opacity-50 transition-colors ${
              hasUnsavedChanges 
                ? 'bg-primary text-primary-foreground hover:bg-primary/90 animate-pulse' 
                : 'bg-secondary text-secondary-foreground'
            }`}
          >
            <Save className="w-4 h-4" />
            {hasUnsavedChanges ? 'Save Changes' : 'Saved'}
          </button>
        </div>
      </div>

      {/* HuggingFace Model Search */}
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Search className="w-5 h-5" />
          Search & Download Models from HuggingFace
        </h3>
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={huggingfaceQuery}
            onChange={(e) => setHuggingfaceQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && searchHuggingface()}
            placeholder="Search for models (e.g., codellama, mistral)..."
            className="flex-1 px-4 py-2 border border-border rounded-md bg-background text-foreground"
          />
          <button
            onClick={searchHuggingface}
            disabled={searching}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {huggingfaceResults.length > 0 && (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {huggingfaceResults.map((model) => (
              <div
                key={model.id}
                className="flex items-center justify-between p-3 bg-background rounded border border-border"
              >
                <div>
                  <div className="font-medium">{model.id}</div>
                  <div className="text-sm text-muted-foreground">
                    {model.downloads?.toLocaleString()} downloads • {model.likes} likes
                  </div>
                </div>
                <button
                  onClick={() => downloadModel(model.id)}
                  disabled={downloadingModels.has(model.id)}
                  className="px-3 py-1 bg-primary text-primary-foreground rounded text-sm hover:bg-primary/90 flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {downloadingModels.has(model.id) ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4" />
                      Download
                    </>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model Routing Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        {/* Validation info banner */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800 px-4 py-2 text-sm">
          <span className="text-blue-700 dark:text-blue-300">
            💡 <strong>How fallback works:</strong> If the primary model's output scores below 80/100 on validation, 
            the system automatically tries the fallback models in order until one succeeds.
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">Artifact Type</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Primary Model</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">
                  Fallback Models
                  <span className="ml-1 text-xs font-normal text-muted-foreground">(used if primary &lt; 80)</span>
                </th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Enabled</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">
                  <span className="flex items-center gap-1">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    Ask AI
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredRoutings.map(([artifactType, routing]) => (
                <tr key={artifactType} className="border-t border-border hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{artifactType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={routing.primary_model}
                      onChange={(e) => updateRouting(artifactType, 'primary_model', e.target.value)}
                      className="w-full px-3 py-1 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition-all hover:border-primary/50"
                    >
                      <option value="">-- Select a model --</option>
                      {/* Show current model if not in the list (unavailable but configured) */}
                      {routing.primary_model && 
                       !ollamaModels.some(m => m.id === routing.primary_model) && 
                       !huggingfaceModels.some(m => m.id === routing.primary_model) &&
                       !cloudModels.some(m => m.id === routing.primary_model) && (
                        <option value={routing.primary_model}>
                          {routing.primary_model} (custom)
                        </option>
                      )}
                      <optgroup label="Ollama Models (Local)">
                        {ollamaModels.length === 0 ? (
                          <option disabled>No Ollama models found - install models first</option>
                        ) : (
                          ollamaModels.map(model => (
                            <option key={model.id} value={model.id}>
                              {model.name} ({model.provider})
                            </option>
                          ))
                        )}
                      </optgroup>
                      <optgroup label="HuggingFace Models (Local)">
                        {huggingfaceModels.length === 0 ? (
                          <option disabled>No HuggingFace models - download models first</option>
                        ) : (
                          huggingfaceModels.map(model => (
                            <option key={model.id} value={model.id}>
                              {model.name} ({model.provider})
                            </option>
                          ))
                        )}
                      </optgroup>
                      <optgroup label="Cloud Models (API)">
                        {cloudModels.length === 0 ? (
                          <option disabled>No cloud models - configure API keys</option>
                        ) : (
                          cloudModels.map(model => (
                            <option key={model.id} value={model.id}>
                              {model.name} ({model.provider})
                            </option>
                          ))
                        )}
                      </optgroup>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <div className="space-y-2">
                      {routing.fallback_models.map((model, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <select
                            value={model}
                            onChange={(e) => {
                              const newFallbacks = [...routing.fallback_models]
                              newFallbacks[idx] = e.target.value
                              updateRouting(artifactType, 'fallback_models', newFallbacks)
                            }}
                            className="flex-1 px-2 py-1 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition-all hover:border-primary/50"
                          >
                            <option value="">-- Select fallback --</option>
                            <optgroup label="Ollama (Local)">
                              {ollamaModels.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                              ))}
                            </optgroup>
                            <optgroup label="HuggingFace (Local)">
                              {huggingfaceModels.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                              ))}
                            </optgroup>
                            <optgroup label="Cloud (API)">
                              {cloudModels.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                              ))}
                            </optgroup>
                          </select>
                          {/* Remove button - only show if more than 1 fallback */}
                          {routing.fallback_models.length > 1 && (
                            <button
                              onClick={() => {
                                const newFallbacks = routing.fallback_models.filter((_, i) => i !== idx)
                                updateRouting(artifactType, 'fallback_models', newFallbacks)
                              }}
                              className="p-1 text-red-500 hover:text-red-700 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                              title="Remove this fallback"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      ))}
                      <button
                        onClick={() => {
                          const newFallbacks = [...routing.fallback_models, '']
                          updateRouting(artifactType, 'fallback_models', newFallbacks)
                        }}
                        className="flex items-center gap-1 text-xs text-primary hover:underline mt-1"
                      >
                        <Plus className="w-3 h-3" />
                        Add Fallback
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={routing.enabled}
                      onChange={(e) => updateRouting(artifactType, 'enabled', e.target.checked)}
                      className="w-4 h-4"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-2">
                      {/* Ask AI Button */}
                      <button
                        onClick={() => getAISuggestion(artifactType)}
                        disabled={suggestingFor === artifactType}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-gradient-to-r from-amber-500/10 to-orange-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 rounded hover:from-amber-500/20 hover:to-orange-500/20 disabled:opacity-50 transition-all"
                        title="Get AI recommendation for this artifact type"
                      >
                        {suggestingFor === artifactType ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            Thinking...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3 h-3" />
                            Ask AI
                          </>
                        )}
                      </button>
                      
                      {/* Show AI suggestion if available */}
                      {suggestions[artifactType] && (
                        <div className="text-xs bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-2">
                          <div className="font-medium text-green-700 dark:text-green-300 mb-1">
                            AI Suggestion ({Math.round(suggestions[artifactType].confidence * 100)}%)
                          </div>
                          <div className="text-green-600 dark:text-green-400 mb-1">
                            Primary: {suggestions[artifactType].suggested_primary || 'None'}
                          </div>
                          {suggestions[artifactType].suggested_fallbacks.length > 0 && (
                            <div className="text-green-600 dark:text-green-400 mb-1">
                              Fallbacks: {suggestions[artifactType].suggested_fallbacks.join(', ')}
                            </div>
                          )}
                          <div className="text-green-600/80 dark:text-green-400/80 italic mb-2 text-[10px]">
                            {suggestions[artifactType].reasoning}
                          </div>
                          <button
                            onClick={() => applySuggestion(artifactType)}
                            className="flex items-center gap-1 px-2 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600 transition-colors"
                          >
                            <CheckCircle className="w-3 h-3" />
                            Apply
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

