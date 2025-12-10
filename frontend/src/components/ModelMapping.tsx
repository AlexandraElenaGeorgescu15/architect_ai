import { useState, useEffect, useCallback } from 'react'
import { useModelStore } from '../stores/modelStore'
import { useUIStore } from '../stores/uiStore'
import api from '../services/api'
import { downloadHuggingFaceModel, getDownloadStatus } from '../services/huggingfaceService'
import { Settings, Save, RefreshCw, Download, Search, Loader2 } from 'lucide-react'

interface ModelRouting {
  artifact_type: string
  primary_model: string
  fallback_models: string[]
  enabled: boolean
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

  useEffect(() => {
    loadRoutings()
    fetchModels()
    
    // Auto-refresh models every 30 seconds to catch newly created fine-tuned models
    const interval = setInterval(() => {
      fetchModels()
      loadRoutings()
    }, 30000)
    
    return () => clearInterval(interval)
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
    } catch (error) {
      console.error('Failed to load model routing:', error)
      // Don't show notification on initial load - silent degradation
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
      addNotification('success', 'Model routing updated successfully!')
      await loadRoutings() // Refresh to get updated data
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
      setHuggingfaceResults(response.data.results || [])
      console.log('🔎 [HUGGINGFACE] Search results:', response.data)
      addNotification('info', `Found ${response.data.results?.length || 0} models for "${huggingfaceQuery}"`)
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
  }

  const filteredRoutings = Object.entries(routings).filter(([type]) =>
    type.toLowerCase().includes(routingFilter.toLowerCase())
  )

  const ollamaModels = models.filter(m => m.provider === 'ollama')
  const cloudModels = models.filter(m => m.provider !== 'ollama' && m.status === 'available')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Model-to-Artifact Mapping</h2>
          <p className="text-muted-foreground mt-1">
            Configure which models to use for each artifact type
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadRoutings}
            className="px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={saveRoutings}
            disabled={loading}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            Save
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
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold">Artifact Type</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Primary Model</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Fallback Models</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Enabled</th>
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
                       !cloudModels.some(m => m.id === routing.primary_model) && (
                        <option value={routing.primary_model} className="text-yellow-600">
                          ⚠️ {routing.primary_model} (configured but unavailable)
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
                    <div className="space-y-1">
                      {routing.fallback_models.map((model, idx) => (
                        <select
                          key={idx}
                          value={model}
                          onChange={(e) => {
                            const newFallbacks = [...routing.fallback_models]
                            newFallbacks[idx] = e.target.value
                            updateRouting(artifactType, 'fallback_models', newFallbacks)
                          }}
                          className="w-full px-2 py-1 text-sm border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition-all hover:border-primary/50"
                        >
                          <option value="">-- Select fallback --</option>
                          <optgroup label="Ollama (Local)">
                            {ollamaModels.map(m => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                          </optgroup>
                          <optgroup label="Cloud (API)">
                            {cloudModels.map(m => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                          </optgroup>
                        </select>
                      ))}
                      <button
                        onClick={() => {
                          const newFallbacks = [...routing.fallback_models, '']
                          updateRouting(artifactType, 'fallback_models', newFallbacks)
                        }}
                        className="text-xs text-primary hover:underline"
                      >
                        + Add Fallback
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

