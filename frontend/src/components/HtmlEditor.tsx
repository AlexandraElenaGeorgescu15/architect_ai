/**
 * HtmlEditor - Code editor with live preview for HTML artifacts
 * 
 * Features:
 * - Monaco-based code editing with syntax highlighting
 * - Live preview panel with debounced updates
 * - Split/Editor/Preview layout modes
 * - AI improvement integration
 * - Version creation on save
 */

import { useState, useCallback, useEffect, useMemo } from 'react'
import Editor from '@monaco-editor/react'
import { 
  Save, Wand2, Columns, Code, Eye, Download, ExternalLink, 
  Loader2, CheckCircle, AlertCircle, RefreshCw 
} from 'lucide-react'
import { useUIStore } from '../stores/uiStore'
import api from '../services/api'

interface HtmlEditorProps {
  initialContent: string
  artifactId: string
  artifactType: string
  onSave?: (content: string) => Promise<void>
  onClose?: () => void
}

type LayoutMode = 'split' | 'editor' | 'preview'

export default function HtmlEditor({ 
  initialContent, 
  artifactId, 
  artifactType,
  onSave,
  onClose
}: HtmlEditorProps) {
  const { addNotification } = useUIStore()
  const [content, setContent] = useState(initialContent)
  const [previewContent, setPreviewContent] = useState(initialContent)
  const [layout, setLayout] = useState<LayoutMode>('split')
  const [isSaving, setIsSaving] = useState(false)
  const [isImproving, setIsImproving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [lastSaved, setLastSaved] = useState<Date | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  // Debounced preview update
  useEffect(() => {
    const timer = setTimeout(() => {
      setPreviewContent(content)
      setPreviewError(null)
    }, 500)
    return () => clearTimeout(timer)
  }, [content])

  // Track changes
  useEffect(() => {
    setHasChanges(content !== initialContent)
  }, [content, initialContent])

  // Prepare complete HTML document for preview
  const preparedPreview = useMemo(() => {
    if (!previewContent) return ''
    
    const trimmed = previewContent.trim().toLowerCase()
    if (trimmed.startsWith('<!doctype') || trimmed.startsWith('<html')) {
      return previewContent
    }
    
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { box-sizing: border-box; }
    body { 
      font-family: system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 1rem;
      line-height: 1.6;
    }
  </style>
</head>
<body>
${previewContent}
</body>
</html>`
  }, [previewContent])

  const handleChange = (value: string | undefined) => {
    setContent(value || '')
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      if (onSave) {
        await onSave(content)
      } else {
        // Default save: create new version via API
        await api.post(`/api/versions/${artifactType}/create`, {
          content: content,
          metadata: {
            edited_manually: true,
            editor: 'html_editor'
          }
        })
      }
      setLastSaved(new Date())
      setHasChanges(false)
      addNotification('success', 'Changes saved successfully!')
    } catch (error: any) {
      console.error('Save error:', error)
      addNotification('error', error?.response?.data?.detail || 'Failed to save changes')
    } finally {
      setIsSaving(false)
    }
  }

  const handleAIImprove = async () => {
    setIsImproving(true)
    try {
      const response = await api.post('/api/generation/improve', {
        artifact_type: artifactType,
        content: content,
        improvement_type: 'html',
        instructions: 'Improve this HTML artifact for better accessibility, semantic markup, and modern best practices while preserving the original design intent.'
      })
      
      if (response.data?.improved_content) {
        setContent(response.data.improved_content)
        addNotification('success', 'AI improvements applied!')
      } else {
        addNotification('info', 'No improvements suggested')
      }
    } catch (error: any) {
      console.error('AI improve error:', error)
      addNotification('error', error?.response?.data?.detail || 'AI improvement failed')
    } finally {
      setIsImproving(false)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifactType.replace(/_/g, '-')}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleOpenExternal = () => {
    const blob = new Blob([preparedPreview], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const handleFormat = async () => {
    // Use Monaco's built-in formatting
    // This is handled by the editor automatically, but we can trigger it
    addNotification('info', 'Use Shift+Alt+F to format in editor')
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Toolbar */}
      <div className="flex-shrink-0 flex items-center justify-between p-3 border-b border-border bg-card">
        <div className="flex items-center gap-2">
          {/* Layout Toggle */}
          <div className="flex items-center bg-muted rounded-lg p-0.5">
            <button
              onClick={() => setLayout('split')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                layout === 'split' 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Split view"
            >
              <Columns className="w-3.5 h-3.5" />
              Split
            </button>
            <button
              onClick={() => setLayout('editor')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                layout === 'editor' 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Editor only"
            >
              <Code className="w-3.5 h-3.5" />
              Editor
            </button>
            <button
              onClick={() => setLayout('preview')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                layout === 'preview' 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Preview only"
            >
              <Eye className="w-3.5 h-3.5" />
              Preview
            </button>
          </div>
          
          {/* Status */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground ml-2">
            {hasChanges && (
              <span className="flex items-center gap-1 text-amber-500">
                <AlertCircle className="w-3 h-3" />
                Unsaved
              </span>
            )}
            {lastSaved && !hasChanges && (
              <span className="flex items-center gap-1 text-green-500">
                <CheckCircle className="w-3 h-3" />
                Saved
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Utility Actions */}
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Download HTML"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={handleOpenExternal}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
          
          <div className="w-px h-6 bg-border mx-1" />
          
          {/* AI Improve */}
          <button
            onClick={handleAIImprove}
            disabled={isImproving}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-accent/10 text-accent hover:bg-accent/20 rounded-lg transition-colors disabled:opacity-50"
            title="AI Improve"
          >
            {isImproving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
            {isImproving ? 'Improving...' : 'AI Improve'}
          </button>
          
          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={isSaving || !hasChanges}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50"
            title="Save changes"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Editor + Preview Area */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Code Editor Panel */}
        {layout !== 'preview' && (
          <div className={`${layout === 'split' ? 'w-1/2' : 'w-full'} h-full border-r border-border`}>
            <Editor
              height="100%"
              defaultLanguage="html"
              value={content}
              onChange={handleChange}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "'Fira Code', 'Consolas', monospace",
                wordWrap: 'on',
                automaticLayout: true,
                scrollBeyondLastLine: false,
                renderWhitespace: 'selection',
                tabSize: 2,
                lineNumbers: 'on',
                folding: true,
                bracketPairColorization: { enabled: true },
                formatOnPaste: true,
                formatOnType: true
              }}
              loading={
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              }
            />
          </div>
        )}

        {/* Live Preview Panel */}
        {layout !== 'editor' && (
          <div className={`${layout === 'split' ? 'w-1/2' : 'w-full'} h-full bg-white flex flex-col`}>
            {/* Preview Header */}
            <div className="flex-shrink-0 flex items-center justify-between px-3 py-2 border-b border-border bg-muted/30">
              <span className="text-xs font-medium text-muted-foreground">Live Preview</span>
              <button
                onClick={() => setPreviewContent(content)}
                className="p-1 hover:bg-muted rounded transition-colors"
                title="Refresh preview"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
            
            {/* Preview Iframe */}
            <div className="flex-1 min-h-0 overflow-auto">
              {previewError ? (
                <div className="flex items-center justify-center h-full p-4 text-destructive">
                  <AlertCircle className="w-5 h-5 mr-2" />
                  <span className="text-sm">{previewError}</span>
                </div>
              ) : (
                <iframe
                  srcDoc={preparedPreview}
                  sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                  className="w-full h-full border-0"
                  title="HTML Preview"
                />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer with keyboard shortcuts hint */}
      <div className="flex-shrink-0 px-3 py-1.5 border-t border-border bg-muted/30 text-[10px] text-muted-foreground">
        <span className="mr-4"><kbd className="px-1 py-0.5 bg-muted rounded">Ctrl+S</kbd> Save</span>
        <span className="mr-4"><kbd className="px-1 py-0.5 bg-muted rounded">Shift+Alt+F</kbd> Format</span>
        <span><kbd className="px-1 py-0.5 bg-muted rounded">Ctrl+Z</kbd> Undo</span>
      </div>
    </div>
  )
}

