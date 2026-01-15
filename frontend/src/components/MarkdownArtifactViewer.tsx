/**
 * Markdown Artifact Viewer
 * Renders PM artifacts (Jira, Backlog, Personas, etc.) as formatted Markdown
 * Uses a simple Markdown-to-HTML converter for basic rendering
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { Copy, Check, FileText, RefreshCw, Sparkles, Loader2 } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'

interface MarkdownArtifactViewerProps {
  artifactType: string
}

// Simple Markdown to HTML converter
function markdownToHtml(markdown: string): string {
  if (!markdown) return ''
  
  let html = markdown
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    
    // Headers
    .replace(/^######\s+(.*)$/gm, '<h6 class="text-sm font-semibold text-foreground mt-4 mb-2">$1</h6>')
    .replace(/^#####\s+(.*)$/gm, '<h5 class="text-base font-semibold text-foreground mt-4 mb-2">$1</h5>')
    .replace(/^####\s+(.*)$/gm, '<h4 class="text-lg font-semibold text-foreground mt-5 mb-2">$1</h4>')
    .replace(/^###\s+(.*)$/gm, '<h3 class="text-xl font-bold text-foreground mt-6 mb-3">$1</h3>')
    .replace(/^##\s+(.*)$/gm, '<h2 class="text-2xl font-bold text-foreground mt-6 mb-3 pb-2 border-b border-border">$1</h2>')
    .replace(/^#\s+(.*)$/gm, '<h1 class="text-3xl font-bold text-foreground mt-6 mb-4 pb-2 border-b-2 border-primary">$1</h1>')
    
    // Bold and Italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="font-bold text-foreground">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em class="italic">$1</em>')
    .replace(/___(.+?)___/g, '<strong><em>$1</em></strong>')
    .replace(/__(.+?)__/g, '<strong class="font-bold text-foreground">$1</strong>')
    .replace(/_(.+?)_/g, '<em class="italic">$1</em>')
    
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 bg-muted rounded text-sm font-mono text-primary">$1</code>')
    
    // Code blocks (triple backticks)
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre class="bg-muted/50 border border-border rounded-lg p-4 overflow-x-auto my-4"><code class="text-sm font-mono text-foreground">${code.trim()}</code></pre>`
    })
    
    // Blockquotes
    .replace(/^>\s+(.*)$/gm, '<blockquote class="border-l-4 border-primary pl-4 py-1 my-3 text-muted-foreground italic">$1</blockquote>')
    
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="my-6 border-t border-border" />')
    .replace(/^\*\*\*$/gm, '<hr class="my-6 border-t border-border" />')
    
    // Unordered lists (handle nested levels)
    .replace(/^(\s*)[-*]\s+(.*)$/gm, (_, indent, content) => {
      const level = indent.length / 2
      const marginClass = level > 0 ? `ml-${Math.min(level * 4, 12)}` : ''
      return `<li class="flex items-start gap-2 my-1 ${marginClass}"><span class="text-primary mt-1.5">•</span><span>${content}</span></li>`
    })
    
    // Ordered lists
    .replace(/^(\d+)\.\s+(.*)$/gm, '<li class="flex items-start gap-2 my-1"><span class="text-primary font-semibold min-w-[1.5rem]">$1.</span><span>$2</span></li>')
    
    // Checkboxes
    .replace(/\[ \]/g, '<span class="inline-flex items-center justify-center w-4 h-4 border border-border rounded mr-1">☐</span>')
    .replace(/\[x\]/gi, '<span class="inline-flex items-center justify-center w-4 h-4 bg-primary text-primary-foreground rounded mr-1">✓</span>')
    
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-primary underline hover:text-primary/80" target="_blank" rel="noopener">$1</a>')
    
    // Tables (basic support)
    .replace(/^\|(.+)\|$/gm, (match, content) => {
      const cells = content.split('|').map((cell: string) => cell.trim())
      const isHeader = cells.some((cell: string) => cell.match(/^-+$/))
      if (isHeader) return '' // Skip separator row
      
      const cellHtml = cells.map((cell: string) => 
        `<td class="px-4 py-2 border border-border">${cell}</td>`
      ).join('')
      return `<tr class="hover:bg-muted/30">${cellHtml}</tr>`
    })
    
    // Wrap paragraphs (lines that aren't already wrapped)
    .replace(/^(?!<[a-z])((?!\s*$).+)$/gm, '<p class="my-2 text-foreground leading-relaxed">$1</p>')
    
    // Clean up empty paragraphs
    .replace(/<p class="[^"]*"><\/p>/g, '')
    
  return html
}

// Skeleton loader
function MarkdownSkeleton() {
  return (
    <div className="h-full flex items-center justify-center p-8 animate-pulse">
      <div className="text-center max-w-md w-full">
        <div className="mx-auto mb-6 w-full max-w-lg space-y-4">
          <div className="h-8 bg-muted/50 rounded w-3/4" />
          <div className="h-4 bg-muted/50 rounded w-full" />
          <div className="h-4 bg-muted/50 rounded w-5/6" />
          <div className="h-4 bg-muted/50 rounded w-4/5" />
          <div className="h-24 bg-muted/50 rounded" />
          <div className="h-4 bg-muted/50 rounded w-full" />
          <div className="h-4 bg-muted/50 rounded w-3/4" />
        </div>
        <div className="flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground font-medium">Loading content...</span>
        </div>
      </div>
    </div>
  )
}

export default function MarkdownArtifactViewer({ artifactType }: MarkdownArtifactViewerProps) {
  const artifacts = useArtifactStore(state => state.artifacts)
  const isLoading = useArtifactStore(state => state.isLoading)
  const { addNotification } = useUIStore()
  
  const [copied, setCopied] = useState(false)
  
  // Debug: Log when artifact type changes
  useEffect(() => {
    console.log('📄 [MarkdownArtifactViewer] Rendering for type:', artifactType)
  }, [artifactType])
  
  // Get artifacts of this type - STRICTLY filter by exact type match
  const typeArtifacts = useMemo(() => {
    const filtered = artifacts.filter(a => a.type === artifactType)
    console.log(`📄 [MarkdownArtifactViewer] Found ${filtered.length} artifacts for type "${artifactType}"`)
    return filtered.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
  }, [artifacts, artifactType])
  
  const selectedArtifact = typeArtifacts[0] || null
  const content = selectedArtifact?.content || ''
  
  // Convert Markdown to HTML
  const htmlContent = useMemo(() => markdownToHtml(content), [content])
  
  // Get friendly type name
  const typeName = useMemo(() => {
    const names: Record<string, string> = {
      'jira': 'JIRA Tasks',
      'backlog': 'Product Backlog',
      'personas': 'User Personas',
      'workflows': 'Workflows',
      'estimations': 'Estimations',
      'feature_scoring': 'Feature Scoring',
      'api_docs': 'API Documentation',
    }
    return names[artifactType] || artifactType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }, [artifactType])
  
  // Copy to clipboard
  const handleCopy = useCallback(async () => {
    if (!content) return
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      addNotification('success', 'Copied to clipboard!')
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      addNotification('error', 'Failed to copy')
    }
  }, [content, addNotification])
  
  // Show skeleton while loading
  if (isLoading && !selectedArtifact) {
    return <MarkdownSkeleton />
  }
  
  // Empty state
  if (!selectedArtifact || !content) {
    return (
      <div className="h-full flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold text-muted-foreground mb-2">No {typeName} Generated Yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Click "Generate" to create your {typeName.toLowerCase()}
          </p>
          {/* Debug info */}
          <div className="flex items-center justify-center gap-2">
            <span className="px-2 py-1 rounded text-xs font-mono bg-blue-500/20 text-blue-600 dark:text-blue-400">
              MarkdownArtifactViewer
            </span>
            <span className="px-2 py-1 rounded text-xs font-mono bg-gray-500/20 text-gray-600 dark:text-gray-400">
              type: {artifactType}
            </span>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/20 flex-shrink-0">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          <h3 className="font-bold text-foreground">{typeName}</h3>
          {/* Debug badge showing actual type */}
          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/20 text-blue-600 dark:text-blue-400">
            {artifactType}
          </span>
          {selectedArtifact.score !== undefined && (
            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${
              selectedArtifact.score >= 80 ? 'bg-green-500/20 text-green-500' :
              selectedArtifact.score >= 60 ? 'bg-yellow-500/20 text-yellow-500' :
              'bg-red-500/20 text-red-500'
            }`}>
              {selectedArtifact.score}% quality
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-secondary hover:bg-secondary/80 text-foreground transition-colors"
            title="Copy to clipboard"
          >
            {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-auto p-6 bg-background">
        <div 
          className="max-w-4xl mx-auto prose prose-sm dark:prose-invert"
          dangerouslySetInnerHTML={{ __html: htmlContent }}
        />
      </div>
      
      {/* Footer */}
      <div className="border-t border-border px-4 py-2 bg-secondary/10 flex items-center justify-between flex-shrink-0">
        <span className="text-xs text-muted-foreground">
          {content.split('\n').length} lines • {content.length} characters
        </span>
        {selectedArtifact.model_used && (
          <span className="text-xs text-muted-foreground">
            Generated by <strong>{selectedArtifact.model_used}</strong>
          </span>
        )}
      </div>
    </div>
  )
}
