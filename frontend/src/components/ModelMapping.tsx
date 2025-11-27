import { useState, useEffect } from 'react'
import { useModelStore } from '../stores/modelStore'
import api from '../services/api'
import { Settings, Save, RefreshCw, Download, Search } from 'lucide-react'

interface ModelRouting {
  artifact_type: string
  primary_model: string
  fallback_models: string[]
  enabled: boolean
}

export default function ModelMapping() {
  const { models, fetchModels } = useModelStore()
  const [routings, setRoutings] = useState<Record<string, ModelRouting>>({})
  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [huggingfaceResults, setHuggingfaceResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)

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
      // Failed to load routings - handle in UI
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
      alert('Model routing updated successfully!')
      await loadRoutings() // Refresh to get updated data
    } catch (error) {
      // Failed to save routings - show user error
      alert('Failed to save model routing. Please check the console for details.')
    } finally {
      setLoading(false)
    }
  }

  const searchHuggingface = async () => {
    if (!searchQuery.trim()) return
    
    console.log('🔎 [HUGGINGFACE] Searching models for query:', searchQuery)
    setSearching(true)
    try {
      const response = await api.get('/api/huggingface/search', {
        params: { query: searchQuery, limit: 10 }
      })
      setHuggingfaceResults(response.data.results || [])
      console.log('🔎 [HUGGINGFACE] Search results:', response.data)
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
        alert('HuggingFace search rate limit reached (10/min). Please wait a bit before searching again.')
      } else {
        alert(`HuggingFace search error: ${detail}`)
      }
    } finally {
      setSearching(false)
    }
  }

  const downloadModel = async (modelId: string) => {
    try {
      // Use a much longer timeout for long-running downloads (e.g. 10 minutes)
      const response = await api.post(
        `/api/huggingface/download/${modelId}`,
        { convert_to_ollama: true },
        { timeout: 10 * 60 * 1000 }
      )
      
      if (response.data.success) {
        alert(`Download started for ${modelId}. This may take several minutes.`)
        
        // Poll for download status
        const checkStatus = async () => {
          try {
            const statusResponse = await api.get(`/api/huggingface/download/${modelId}/status`)
            const status = statusResponse.data
            
            if (status.status === 'completed') {
              alert(`Model ${modelId} downloaded successfully!`)
              fetchModels() // Refresh model list
            } else if (status.status === 'failed') {
              alert(`Download failed: ${status.error || 'Unknown error'}`)
            } else if (status.status === 'downloading') {
              // Check again in 5 seconds
              setTimeout(checkStatus, 5000)
            }
          } catch (error) {
            console.error('Error checking download status:', error)
          }
        }
        
        // Start checking status after 2 seconds
        setTimeout(checkStatus, 2000)
      } else {
        alert(`Download failed: ${response.data.error || 'Unknown error'}`)
      }
    } catch (error: any) {
      // Improve error message for timeouts vs real backend errors
      const isTimeout = error?.code === 'ECONNABORTED' || /timeout/i.test(error?.message || '')
      const errorMsg =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        (isTimeout ? 'Request timed out while starting download. The backend may still be working in the background; please check status after a moment.' : error?.message) ||
        'Failed to start download'

      alert(`Download error: ${errorMsg}`)
      console.error('Download error:', error)
    }
  }

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
    type.toLowerCase().includes(searchQuery.toLowerCase())
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
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
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
                  className="px-3 py-1 bg-primary text-primary-foreground rounded text-sm hover:bg-primary/90 flex items-center gap-1"
                >
                  <Download className="w-4 h-4" />
                  Download
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
                      <optgroup label="Ollama Models">
                        {ollamaModels.map(model => (
                          <option key={model.id} value={model.id}>
                            {model.name} ({model.provider})
                          </option>
                        ))}
                      </optgroup>
                      <optgroup label="Cloud Models">
                        {cloudModels.map(model => (
                          <option key={model.id} value={model.id}>
                            {model.name} ({model.provider})
                          </option>
                        ))}
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
                          <optgroup label="Ollama">
                            {ollamaModels.map(m => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                          </optgroup>
                          <optgroup label="Cloud">
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

