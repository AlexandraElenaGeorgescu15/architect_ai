import { useState } from 'react'
import { Download, FileText, Image, FileCode, FileJson, Loader2, Check } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import api from '../services/api'

type ExportFormat = 'png' | 'svg' | 'pdf' | 'markdown' | 'code' | 'confluence' | 'jira'

interface ExportOption {
  format: ExportFormat
  label: string
  icon: any
  description: string
  mimeType: string
}

interface ExtendedExportOption extends ExportOption {
  enabled: boolean
  comingSoon?: boolean
}

const exportOptions: ExtendedExportOption[] = [
  { format: 'markdown', label: 'Markdown', icon: FileText, description: 'Export as Markdown document', mimeType: 'text/markdown', enabled: true },
  { format: 'svg', label: 'SVG', icon: Image, description: 'Export as SVG image (for diagrams)', mimeType: 'image/svg+xml', enabled: true },
  { format: 'png', label: 'PNG', icon: Image, description: 'Export as PNG image (for diagrams)', mimeType: 'image/png', enabled: true },
  { format: 'pdf', label: 'PDF', icon: FileText, description: 'Export as PDF document', mimeType: 'application/pdf', enabled: true },
  { format: 'code', label: 'Code File', icon: FileCode, description: 'Export as code file', mimeType: 'text/plain', enabled: true },
  { format: 'confluence', label: 'Confluence', icon: FileJson, description: 'Confluence integration (Coming Soon)', mimeType: 'application/json', enabled: false, comingSoon: true },
  { format: 'jira', label: 'Jira', icon: FileJson, description: 'Jira integration (Coming Soon)', mimeType: 'application/json', enabled: false, comingSoon: true },
]

export default function ExportManager() {
  const { artifacts } = useArtifactStore()
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null)
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('markdown')
  const [isExporting, setIsExporting] = useState(false)
  const [exported, setExported] = useState(false)
  const [confluenceSpace, setConfluenceSpace] = useState('ARCH')
  const [confluencePageTitle, setConfluencePageTitle] = useState('')
  const [jiraProject, setJiraProject] = useState('ARCH')
  const [jiraIssueType, setJiraIssueType] = useState('Task')
  const [jiraSummary, setJiraSummary] = useState('')

  const selectedArtifactData = artifacts.find(a => a.id === selectedArtifact)

  const handleExport = async () => {
    if (!selectedArtifactData) return

    setIsExporting(true)
    setExported(false)

    try {
      const isConnector = selectedFormat === 'confluence' || selectedFormat === 'jira'
      const connectorOptions =
        selectedFormat === 'confluence'
          ? {
              space_key: confluenceSpace,
              page_title: confluencePageTitle || selectedArtifactData.id.replace(/_/g, ' '),
            }
          : selectedFormat === 'jira'
            ? {
                project_key: jiraProject,
                issue_type: jiraIssueType,
                summary: jiraSummary || `${selectedArtifactData.type} for ${selectedArtifactData.id}`,
              }
            : {}

      const response = await api.post(
        '/api/export/artifact',
        {
          artifact_id: selectedArtifactData.id,
          artifact_type: selectedArtifactData.type,
          content: selectedArtifactData.content,
          export_format: selectedFormat,
          options: {
            ...(isConnector
              ? connectorOptions
              : {
                  language: detectLanguage(selectedArtifactData.content),
                  metadata: {
                    generated_at: selectedArtifactData.created_at,
                    validation_score: selectedArtifactData.score,
                  },
                }),
          },
        },
        isConnector ? {} : { responseType: 'blob' }
      )

      if (isConnector) {
        alert(response.data?.message || 'Export request sent.')
        setExported(true)
        setTimeout(() => setExported(false), 3000)
      } else {
        const blob = new Blob([response.data], { type: response.headers['content-type'] || 'application/octet-stream' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        
        const extension = selectedFormat === 'code' 
          ? getCodeExtension(selectedArtifactData.content)
          : selectedFormat === 'markdown' ? 'md' : selectedFormat
        
        a.download = `${selectedArtifactData.id}.${extension}`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        setExported(true)
        setTimeout(() => setExported(false), 3000)
      }
    } catch (error: any) {
      // Export error - handle based on status
      if (error.response?.status === 501) {
        alert('This export format is not yet fully implemented. Please try Markdown or SVG.')
      } else {
        alert('Failed to export artifact')
      }
    } finally {
      setIsExporting(false)
    }
  }

  const detectLanguage = (content: string): string => {
    if (content.includes('def ') || content.includes('import ')) return 'python'
    if (content.includes('function ') || content.includes('const ')) return 'javascript'
    if (content.includes('class ') && content.includes('public ')) return 'java'
    return 'text'
  }

  const getCodeExtension = (content: string): string => {
    const lang = detectLanguage(content)
    const extensions: Record<string, string> = {
      python: 'py',
      javascript: 'js',
      java: 'java',
      typescript: 'ts',
      go: 'go',
      rust: 'rs',
      php: 'php'
    }
    return extensions[lang] || 'txt'
  }

  const canExportFormat = (format: ExportFormat, artifactType: string): boolean => {
    // First check if the format is enabled at all
    const option = exportOptions.find(o => o.format === format)
    if (option && !option.enabled) {
      return false
    }
    
    // Then check artifact type compatibility
    if (format === 'svg' || format === 'png') {
      return artifactType.startsWith('mermaid_') || artifactType.startsWith('html_')
    }
    return true
  }

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Download className="w-5 h-5" />
          Export Artifacts
        </h2>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Artifact Selection */}
        <div className="col-span-4 bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3 text-muted-foreground">Select Artifact</h3>
          {artifacts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No artifacts to export</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
              {artifacts.map((artifact) => (
                <button
                  key={artifact.id}
                  onClick={() => setSelectedArtifact(artifact.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${
                    selectedArtifact === artifact.id
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:bg-accent/50 hover:border-primary/50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    <span className="text-sm font-medium truncate">{artifact.type}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(artifact.created_at).toLocaleDateString()}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Export Options */}
        <div className="col-span-8 bg-card border border-border rounded-lg p-4">
          {selectedArtifactData ? (
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold mb-3 text-muted-foreground">Export Format</h3>
                <div className="grid grid-cols-2 gap-3">
                  {exportOptions.map((option) => {
                    const Icon = option.icon
                    const canExport = canExportFormat(option.format, selectedArtifactData.type)
                    const isComingSoon = option.comingSoon
                    return (
                      <button
                        key={option.format}
                        onClick={() => canExport && setSelectedFormat(option.format)}
                        disabled={!canExport}
                        className={`p-4 rounded-lg border transition-all duration-200 text-left relative ${
                          selectedFormat === option.format
                            ? 'border-primary bg-primary/10 text-primary'
                            : canExport
                            ? 'border-border hover:bg-accent/50 hover:border-primary/50'
                            : 'border-border opacity-50 cursor-not-allowed'
                        }`}
                      >
                        {isComingSoon && (
                          <span className="absolute -top-2 -right-2 px-2 py-0.5 bg-amber-500 text-white text-[10px] font-bold rounded-full shadow-sm">
                            Soon
                          </span>
                        )}
                        <div className="flex items-center gap-3">
                          <Icon className={`w-5 h-5 ${isComingSoon ? 'opacity-50' : ''}`} />
                          <div className="flex-1">
                            <p className={`font-medium text-sm ${isComingSoon ? 'opacity-70' : ''}`}>{option.label}</p>
                            <p className="text-xs text-muted-foreground mt-1">{option.description}</p>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {(selectedFormat === 'confluence' || selectedFormat === 'jira') && (
                <div className="space-y-4 border border-dashed border-border rounded-lg p-4">
                  {selectedFormat === 'confluence' ? (
                    <>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Space Key</label>
                        <input
                          value={confluenceSpace}
                          onChange={(e) => setConfluenceSpace(e.target.value)}
                          className="w-full border border-border rounded px-3 py-2 mt-1 text-sm bg-background"
                        />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Page Title</label>
                        <input
                          value={confluencePageTitle}
                          onChange={(e) => setConfluencePageTitle(e.target.value)}
                          placeholder={selectedArtifactData.id.replace(/_/g, ' ')}
                          className="w-full border border-border rounded px-3 py-2 mt-1 text-sm bg-background"
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-medium text-muted-foreground">Project Key</label>
                          <input
                            value={jiraProject}
                            onChange={(e) => setJiraProject(e.target.value)}
                            className="w-full border border-border rounded px-3 py-2 mt-1 text-sm bg-background"
                          />
                        </div>
                        <div>
                          <label className="text-xs font-medium text-muted-foreground">Issue Type</label>
                          <input
                            value={jiraIssueType}
                            onChange={(e) => setJiraIssueType(e.target.value)}
                            className="w-full border border-border rounded px-3 py-2 mt-1 text-sm bg-background"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Summary</label>
                        <input
                          value={jiraSummary}
                          onChange={(e) => setJiraSummary(e.target.value)}
                          placeholder={`${selectedArtifactData.type} for ${selectedArtifactData.id}`}
                          className="w-full border border-border rounded px-3 py-2 mt-1 text-sm bg-background"
                        />
                      </div>
                    </>
                  )}
                </div>
              )}

              <div className="pt-4 border-t border-border">
                <button
                  onClick={handleExport}
                  disabled={isExporting || !selectedFormat}
                  className="w-full px-6 py-4 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-lg font-semibold shadow-xl hover:shadow-primary/50 transition-all"
                >
                  {isExporting ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Exporting...
                    </>
                  ) : exported ? (
                    <>
                      <Check className="w-5 h-5" />
                      Exported!
                    </>
                  ) : (
                    <>
                      <Download className="w-5 h-5" />
                      Export as {exportOptions.find(o => o.format === selectedFormat)?.label}
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-muted-foreground">
              <div className="text-center">
                <Download className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-medium mb-2">No artifact selected</p>
                <p className="text-sm">Select an artifact to export</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

