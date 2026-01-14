import { useState, useEffect, useCallback } from 'react'
import {
  Lightbulb,
  GitBranch,
  Package,
  FileText,
  Database,
  FolderGit2,
  Shield,
  MessageSquareText,
  ChevronDown,
  ChevronRight,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Zap,
  ArrowRight,
  RefreshCw,
  Loader2,
  Copy,
  Download,
  ExternalLink
} from 'lucide-react'
import api from '../services/api'

interface Suggestion {
  artifact_type: string
  reason: string
  priority: 'high' | 'medium' | 'low'
  context: string
  estimated_value: string
  dependencies: string[]
}

interface StalenessReport {
  artifact_id: string
  artifact_type: string
  is_stale: boolean
  reason: string
  recommendation: string
  upstream_changes: Array<{
    artifact_id: string
    artifact_type: string
    updated_at: string
  }>
}

interface ParsedMeetingNotes {
  feature_name: string
  feature_description: string
  entities: Array<{
    name: string
    fields: Array<{ name: string; type: string; constraints: string }>
    confidence: number
  }>
  endpoints: Array<{
    method: string
    path: string
    description: string
    confidence: number
  }>
  ui_components: Array<{
    component_type: string
    description: string
    fields: string[]
    confidence: number
  }>
  action_items: Array<{
    task: string
    assignee: string | null
    deadline: string | null
  }>
  suggestions: string[]
  parsing_confidence: number
}

interface MigrationResult {
  framework: string
  migration_name: string
  content: string
  entities_created: string[]
  relationships_created: string[]
  notes: string[]
}

interface PackagePreset {
  id: string
  name: string
  description: string
  artifact_count: number
  estimated_time_minutes: number
  artifacts: string[]
}

export default function SmartAssistant() {
  const [activeTab, setActiveTab] = useState<string>('suggestions')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Suggestions state
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [existingArtifacts, setExistingArtifacts] = useState<string[]>([])
  const [meetingNotes, setMeetingNotes] = useState('')
  
  // Staleness state
  const [stalenessReports, setStalenessReports] = useState<StalenessReport[]>([])
  
  // Meeting notes parser state
  const [parsedNotes, setParsedNotes] = useState<ParsedMeetingNotes | null>(null)
  const [notesToParse, setNotesToParse] = useState('')
  
  // Migration state
  const [erdContent, setErdContent] = useState('')
  const [selectedFramework, setSelectedFramework] = useState('ef_core')
  const [migrationResult, setMigrationResult] = useState<MigrationResult | null>(null)
  const [frameworks, setFrameworks] = useState<Array<{ id: string; name: string; language: string }>>([])
  
  // Sprint package state
  const [packagePresets, setPackagePresets] = useState<PackagePreset[]>([])
  const [selectedPreset, setSelectedPreset] = useState('full')
  const [packageNotes, setPackageNotes] = useState('')
  
  // Load initial data
  useEffect(() => {
    loadFrameworks()
    loadPackagePresets()
  }, [])
  
  const loadFrameworks = async () => {
    try {
      const response = await api.get('/api/assistant/migration/frameworks')
      setFrameworks(response.data.frameworks || [])
    } catch (err) {
      console.error('Failed to load frameworks:', err)
    }
  }
  
  const loadPackagePresets = async () => {
    try {
      const response = await api.get('/api/assistant/sprint-package/presets')
      setPackagePresets(response.data.presets || [])
    } catch (err) {
      console.error('Failed to load presets:', err)
    }
  }
  
  const getSuggestions = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.post('/api/assistant/suggestions', {
        existing_artifact_types: existingArtifacts,
        meeting_notes: meetingNotes,
        max_suggestions: 5
      })
      setSuggestions(response.data.suggestions || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to get suggestions')
    } finally {
      setIsLoading(false)
    }
  }, [existingArtifacts, meetingNotes])
  
  const checkStaleness = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/assistant/artifacts/stale')
      setStalenessReports(response.data.stale_artifacts || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to check staleness')
    } finally {
      setIsLoading(false)
    }
  }, [])
  
  const parseMeetingNotes = useCallback(async () => {
    if (!notesToParse.trim()) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.post('/api/assistant/meeting-notes/parse', {
        meeting_notes: notesToParse
      })
      setParsedNotes(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to parse meeting notes')
    } finally {
      setIsLoading(false)
    }
  }, [notesToParse])
  
  const generateMigration = useCallback(async () => {
    if (!erdContent.trim()) return
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.post('/api/assistant/migration/generate', {
        erd_content: erdContent,
        framework: selectedFramework
      })
      setMigrationResult(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate migration')
    } finally {
      setIsLoading(false)
    }
  }, [erdContent, selectedFramework])
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }
  
  const downloadMigration = () => {
    if (!migrationResult) return
    const blob = new Blob([migrationResult.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${migrationResult.migration_name}.${selectedFramework === 'ef_core' ? 'cs' : selectedFramework === 'django' ? 'py' : 'sql'}`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  const priorityColors = {
    high: 'text-red-400 bg-red-500/10 border-red-500/30',
    medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
    low: 'text-green-400 bg-green-500/10 border-green-500/30'
  }
  
  const tabs = [
    { id: 'suggestions', label: 'Smart Suggestions', icon: Lightbulb },
    { id: 'staleness', label: 'Artifact Health', icon: GitBranch },
    { id: 'parser', label: 'Notes Parser', icon: FileText },
    { id: 'migration', label: 'Migration Gen', icon: Database },
    { id: 'package', label: 'Sprint Package', icon: Package },
  ]
  
  return (
    <div className="h-full flex flex-col bg-slate-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            Intelligent Assistant
          </h2>
        </div>
        
        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto pb-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap transition-all
                ${activeTab === tab.id 
                  ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}
        
        {/* Smart Suggestions Tab */}
        {activeTab === 'suggestions' && (
          <div className="space-y-4">
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <h3 className="text-sm font-medium text-slate-300 mb-2">What artifacts do you have?</h3>
              <div className="flex flex-wrap gap-2 mb-3">
                {['mermaid_erd', 'mermaid_architecture', 'mermaid_sequence', 'api_docs', 'code_prototype', 'dev_visual_prototype', 'jira'].map(type => (
                  <button
                    key={type}
                    onClick={() => {
                      setExistingArtifacts(prev => 
                        prev.includes(type) 
                          ? prev.filter(t => t !== type)
                          : [...prev, type]
                      )
                    }}
                    className={`px-2 py-1 text-xs rounded border transition-all
                      ${existingArtifacts.includes(type)
                        ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                        : 'bg-slate-700/50 border-slate-600 text-slate-400 hover:text-slate-200'}`}
                  >
                    {type.replace('mermaid_', '').replace('_', ' ')}
                  </button>
                ))}
              </div>
              
              <textarea
                placeholder="Paste your meeting notes for smarter suggestions..."
                value={meetingNotes}
                onChange={e => setMeetingNotes(e.target.value)}
                className="w-full h-20 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-purple-500"
              />
              
              <button
                onClick={getSuggestions}
                disabled={isLoading}
                className="mt-3 flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lightbulb className="w-4 h-4" />}
                Get Suggestions
              </button>
            </div>
            
            {/* Suggestions Results */}
            {suggestions.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-400" />
                  Recommended Next Steps
                </h3>
                {suggestions.map((suggestion, idx) => (
                  <div key={idx} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-purple-500/30 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-slate-200">
                            {suggestion.artifact_type.replace('mermaid_', '').replace('_', ' ').toUpperCase()}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded border ${priorityColors[suggestion.priority]}`}>
                            {suggestion.priority}
                          </span>
                        </div>
                        <p className="text-sm text-slate-400">{suggestion.reason}</p>
                        <p className="text-xs text-slate-500 mt-1">{suggestion.context}</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-purple-400 flex-shrink-0 mt-1" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Artifact Health Tab */}
        {activeTab === 'staleness' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-slate-300">Artifact Health Check</h3>
              <button
                onClick={checkStaleness}
                disabled={isLoading}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm transition-colors"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Check Now
              </button>
            </div>
            
            {stalenessReports.length === 0 ? (
              <div className="p-8 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
                <p className="text-slate-300">All artifacts are up to date!</p>
                <p className="text-sm text-slate-500 mt-1">No stale artifacts detected</p>
              </div>
            ) : (
              <div className="space-y-2">
                {stalenessReports.map((report, idx) => (
                  <div key={idx} className="p-3 bg-slate-800/50 rounded-lg border border-yellow-500/30">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />
                      <div>
                        <div className="font-medium text-slate-200">{report.artifact_type}</div>
                        <p className="text-sm text-slate-400">{report.reason}</p>
                        <p className="text-xs text-yellow-400 mt-1">{report.recommendation}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Meeting Notes Parser Tab */}
        {activeTab === 'parser' && (
          <div className="space-y-4">
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <h3 className="text-sm font-medium text-slate-300 mb-2">Paste Meeting Notes</h3>
              <textarea
                placeholder="Paste your meeting notes to extract structured information..."
                value={notesToParse}
                onChange={e => setNotesToParse(e.target.value)}
                className="w-full h-40 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-purple-500"
              />
              <button
                onClick={parseMeetingNotes}
                disabled={isLoading || !notesToParse.trim()}
                className="mt-3 flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                Parse Notes
              </button>
            </div>
            
            {parsedNotes && (
              <div className="space-y-3">
                <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <h4 className="text-sm font-medium text-purple-300 mb-2">Feature Detected</h4>
                  <div className="text-lg font-bold text-slate-200">{parsedNotes.feature_name}</div>
                  <p className="text-sm text-slate-400 mt-1">{parsedNotes.feature_description}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-slate-500">Confidence:</span>
                    <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${parsedNotes.parsing_confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400">{Math.round(parsedNotes.parsing_confidence * 100)}%</span>
                  </div>
                </div>
                
                {parsedNotes.entities.length > 0 && (
                  <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                    <h4 className="text-sm font-medium text-green-300 mb-2">📊 Entities Detected ({parsedNotes.entities.length})</h4>
                    <div className="space-y-2">
                      {parsedNotes.entities.map((entity, idx) => (
                        <div key={idx} className="text-sm">
                          <span className="font-mono text-green-400">{entity.name}</span>
                          {entity.fields.length > 0 && (
                            <span className="text-slate-500 ml-2">
                              ({entity.fields.map(f => f.name).join(', ')})
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {parsedNotes.endpoints.length > 0 && (
                  <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                    <h4 className="text-sm font-medium text-blue-300 mb-2">🔌 Endpoints Detected ({parsedNotes.endpoints.length})</h4>
                    <div className="space-y-1">
                      {parsedNotes.endpoints.map((endpoint, idx) => (
                        <div key={idx} className="text-sm font-mono">
                          <span className="text-blue-400">{endpoint.method}</span>
                          <span className="text-slate-300 ml-2">{endpoint.path}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {parsedNotes.ui_components.length > 0 && (
                  <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                    <h4 className="text-sm font-medium text-pink-300 mb-2">🎨 UI Components ({parsedNotes.ui_components.length})</h4>
                    <div className="flex flex-wrap gap-2">
                      {parsedNotes.ui_components.map((comp, idx) => (
                        <span key={idx} className="px-2 py-1 bg-pink-500/20 text-pink-300 rounded text-sm">
                          {comp.component_type}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {parsedNotes.suggestions.length > 0 && (
                  <div className="p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
                    <h4 className="text-sm font-medium text-yellow-300 mb-2">💡 Suggestions</h4>
                    <ul className="space-y-1">
                      {parsedNotes.suggestions.map((suggestion, idx) => (
                        <li key={idx} className="text-sm text-yellow-200">• {suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Migration Generator Tab */}
        {activeTab === 'migration' && (
          <div className="space-y-4">
            <div className="p-4 bg-slate-800/50 rounded-lg border border-slate-700">
              <h3 className="text-sm font-medium text-slate-300 mb-2">Paste ERD Diagram</h3>
              <textarea
                placeholder="Paste your Mermaid ERD diagram here..."
                value={erdContent}
                onChange={e => setErdContent(e.target.value)}
                className="w-full h-32 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm font-mono resize-none focus:outline-none focus:border-purple-500"
              />
              
              <div className="mt-3 flex items-center gap-3">
                <select
                  value={selectedFramework}
                  onChange={e => setSelectedFramework(e.target.value)}
                  className="bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-purple-500"
                >
                  {frameworks.map(fw => (
                    <option key={fw.id} value={fw.id}>{fw.name}</option>
                  ))}
                </select>
                
                <button
                  onClick={generateMigration}
                  disabled={isLoading || !erdContent.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
                  Generate Migration
                </button>
              </div>
            </div>
            
            {migrationResult && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-slate-300">Generated Migration</h3>
                  <div className="flex gap-2">
                    <button
                      onClick={() => copyToClipboard(migrationResult.content)}
                      className="flex items-center gap-1 px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs"
                    >
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                    <button
                      onClick={downloadMigration}
                      className="flex items-center gap-1 px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded text-xs"
                    >
                      <Download className="w-3 h-3" /> Download
                    </button>
                  </div>
                </div>
                
                <pre className="p-4 bg-slate-950 rounded-lg border border-slate-700 overflow-x-auto text-xs font-mono text-slate-300 max-h-96">
                  {migrationResult.content}
                </pre>
                
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="px-2 py-1 bg-green-500/20 text-green-300 rounded">
                    ✓ {migrationResult.entities_created.length} tables created
                  </span>
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded">
                    ✓ {migrationResult.relationships_created.length} relationships
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Sprint Package Tab */}
        {activeTab === 'package' && (
          <div className="space-y-4">
            <div className="p-4 bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-lg border border-purple-500/30">
              <h3 className="text-lg font-bold text-purple-300 mb-2">🚀 One-Click Sprint Package</h3>
              <p className="text-sm text-slate-400">
                Generate a complete set of artifacts from your meeting notes in one click.
              </p>
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              {packagePresets.map(preset => (
                <button
                  key={preset.id}
                  onClick={() => setSelectedPreset(preset.id)}
                  className={`p-3 rounded-lg border text-left transition-all
                    ${selectedPreset === preset.id
                      ? 'bg-purple-500/20 border-purple-500/50'
                      : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'}`}
                >
                  <div className="font-medium text-sm text-slate-200">{preset.name}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{preset.description}</div>
                  <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                    <span>{preset.artifact_count} artifacts</span>
                    <span>•</span>
                    <span>~{preset.estimated_time_minutes} min</span>
                  </div>
                </button>
              ))}
            </div>
            
            <textarea
              placeholder="Paste your meeting notes for the sprint package..."
              value={packageNotes}
              onChange={e => setPackageNotes(e.target.value)}
              className="w-full h-32 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:border-purple-500"
            />
            
            <button
              disabled={!packageNotes.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-lg text-sm font-bold transition-all disabled:opacity-50"
            >
              <Package className="w-5 h-5" />
              Generate {packagePresets.find(p => p.id === selectedPreset)?.name || 'Sprint Package'}
            </button>
            
            <p className="text-xs text-center text-slate-500">
              This will generate all artifacts in the selected package sequentially.
              Progress will be shown via WebSocket updates.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
