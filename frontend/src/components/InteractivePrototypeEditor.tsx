/**
 * Interactive Prototype Editor with AI Chat
 * Allows users to modify visual prototypes and ALL HTML artifacts through natural language conversation
 */

import { useState, useEffect, useRef, useMemo } from 'react'
import { Loader2, MessageSquare, Code, Eye, Send, Sparkles, RefreshCw, PanelRightClose, PanelRightOpen, X, Save } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { sendChatMessage } from '../services/chatService'
import { updateArtifact as updateArtifactAPI } from '../services/generationService'

interface InteractivePrototypeEditorProps {
  artifactType?: string  // Optional: specific artifact type to filter by
}

// Skeleton loader for HTML prototype viewer
function PrototypeSkeleton() {
  return (
    <div className="h-full flex items-center justify-center p-8 animate-pulse">
      <div className="text-center max-w-md w-full">
        {/* Browser window placeholder */}
        <div className="mx-auto mb-6 w-full max-w-lg">
          <div className="bg-muted/40 rounded-xl overflow-hidden">
            {/* Browser chrome */}
            <div className="bg-muted/60 px-4 py-2 flex items-center gap-2">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-muted/80" />
                <div className="w-3 h-3 rounded-full bg-muted/80" />
                <div className="w-3 h-3 rounded-full bg-muted/80" />
              </div>
              <div className="flex-1 h-5 bg-muted/80 rounded mx-4" />
            </div>
            {/* Content area */}
            <div className="p-6 space-y-4">
              <div className="h-8 bg-muted/50 rounded w-3/4" />
              <div className="h-4 bg-muted/50 rounded w-full" />
              <div className="h-4 bg-muted/50 rounded w-5/6" />
              <div className="h-32 bg-muted/50 rounded" />
              <div className="flex gap-2">
                <div className="h-10 bg-muted/50 rounded flex-1" />
                <div className="h-10 bg-muted/50 rounded flex-1" />
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-center gap-2">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
          <span className="text-sm text-muted-foreground font-medium">Loading prototype...</span>
        </div>
      </div>
    </div>
  )
}

export default function InteractivePrototypeEditor({ artifactType }: InteractivePrototypeEditorProps) {
  // CRITICAL: Use reactive selector pattern to ensure component re-renders when artifacts change
  // This fixes the bug where generated content doesn't show immediately
  const artifacts = useArtifactStore(state => state.artifacts)
  const updateArtifact = useArtifactStore(state => state.updateArtifact)
  const isLoading = useArtifactStore(state => state.isLoading)
  const { addNotification } = useUIStore()

  // DEBUG: Log on mount/unmount to verify component lifecycle
  useEffect(() => {
    console.log(`🟢 [InteractivePrototypeEditor] MOUNTED for type: "${artifactType}"`)
    return () => {
      console.log(`🔴 [InteractivePrototypeEditor] UNMOUNTED for type: "${artifactType}"`)
    }
  }, [artifactType])

  // Get HTML artifacts - filter by specific type if provided, otherwise get all HTML types
  // CRITICAL: This must be computed from the reactive artifacts array
  const prototypeArtifacts = useMemo(() => {
    const filtered = artifacts.filter((a) => {
      if (artifactType) {
        return a.type === artifactType
      }
      // Default: get all HTML-like artifacts
      return a.type === 'dev_visual_prototype' ||
        a.type === 'html_prototype' ||
        a.type.startsWith('html_')
    }).sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))

    console.log(`📦 [InteractivePrototypeEditor] Filtered for "${artifactType}": found ${filtered.length} artifacts`,
      filtered.map(a => ({ id: a.id, type: a.type })))

    return filtered
  }, [artifacts, artifactType])

  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState('')
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [isModifying, setIsModifying] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [chatHistoryByArtifact, setChatHistoryByArtifact] = useState<Record<string, Array<{ role: 'user' | 'assistant'; content: string }>>>({})
  // AI panel collapsed by default to maximize preview space
  // Users can expand it when they want to use the AI modifier
  const [isAIPanelOpen, setIsAIPanelOpen] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // CRITICAL FIX: Reset selection when artifact type changes
  // This prevents showing the wrong artifact when switching between types
  useEffect(() => {
    console.log('📦 [InteractivePrototypeEditor] Artifact type changed to:', artifactType, '- resetting selection')
    setSelectedArtifactId(null)
    setHtmlContent('')
    setChatHistory([])
  }, [artifactType])

  // Get selected artifact - MUST search within filtered prototypeArtifacts, not ALL artifacts
  const selectedArtifact = selectedArtifactId
    ? prototypeArtifacts.find((a) => a.id === selectedArtifactId) || prototypeArtifacts[0] || null
    : prototypeArtifacts[0] || null

  // Auto-select the latest artifact when a new one is generated
  useEffect(() => {
    if (prototypeArtifacts.length > 0) {
      const latestArtifact = prototypeArtifacts[0]
      // Always update to latest if no selection or if current selection is not in filtered list
      if (!selectedArtifactId || !prototypeArtifacts.find(a => a.id === selectedArtifactId)) {
        console.log('📦 [InteractivePrototypeEditor] Auto-selecting latest artifact:', latestArtifact.id, 'for type:', artifactType)
        setSelectedArtifactId(latestArtifact.id)
      }
    }
  }, [prototypeArtifacts.length, prototypeArtifacts[0]?.id, selectedArtifactId, artifactType])

  // Helper function to sanitize HTML content and add viewport meta
  const sanitizeHtmlContent = (html: string): string => {
    // Check if HTML already has a viewport meta tag
    const hasViewport = /<meta[^>]*name=["']viewport["'][^>]*>/i.test(html)

    // If it has a viewport tag, replace it with one that prevents zoom
    if (hasViewport) {
      html = html.replace(
        /<meta[^>]*name=["']viewport["'][^>]*>/i,
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=contain">'
      )
    } else {
      // If no viewport tag, add one to the head
      if (html.includes('<head>')) {
        html = html.replace(
          '<head>',
          '<head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=contain">'
        )
      } else if (html.includes('<html>')) {
        html = html.replace(
          '<html>',
          '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=contain"></head>'
        )
      } else {
        // If no HTML structure, wrap it
        html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=contain"></head><body>${html}</body></html>`
      }
    }

    // Add CSS to prevent zoom in the iframe content
    const preventZoomCSS = `
      <style>
        * {
          -webkit-user-select: none;
          -moz-user-select: none;
          -ms-user-select: none;
          user-select: none;
        }
        html, body {
          zoom: 1 !important;
          transform: scale(1) !important;
          overflow: auto;
        }
      </style>
    `

    if (html.includes('</head>')) {
      html = html.replace('</head>', `${preventZoomCSS}</head>`)
    } else if (html.includes('<head>')) {
      html = html.replace('<head>', `<head>${preventZoomCSS}`)
    }

    return html
  }

  // Load artifact content and restore chat history
  useEffect(() => {
    if (selectedArtifact) {
      console.log('Loading artifact:', selectedArtifact.id, 'Content length:', selectedArtifact.content?.length || 0)
      if (selectedArtifact.content) {
        const sanitized = sanitizeHtmlContent(selectedArtifact.content)
        setHtmlContent(sanitized)
        console.log('HTML content set, length:', sanitized.length)
      } else {
        console.warn('Selected artifact has no content')
        setHtmlContent('')
      }

      // Restore chat history for this artifact, or initialize if new
      if (chatHistoryByArtifact[selectedArtifact.id]) {
        setChatHistory(chatHistoryByArtifact[selectedArtifact.id])
      } else {
        const typeName = selectedArtifact.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        const initialHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [
          {
            role: 'assistant' as const,
            content: `👋 Hi! I can help you modify this ${typeName}.\n\n**Quick actions above** for common changes, or describe what you want:\n\n• "Make it look more professional"\n• "Change the colors to blue and white"\n• "Add a header with a logo"\n• "Make the buttons bigger"\n\n💡 **Tip:** For big redesigns, I'll take 1-2 minutes. For small tweaks, just a few seconds!`,
          },
        ]
        setChatHistory(initialHistory)
        setChatHistoryByArtifact(prev => ({
          ...prev,
          [selectedArtifact.id]: initialHistory
        }))
      }
    } else {
      console.log('No artifact selected, prototypeArtifacts:', prototypeArtifacts.length)
      setHtmlContent('')
    }
  }, [selectedArtifact?.id, selectedArtifact?.content])

  // Save chat history when it changes (but not when switching view modes)
  useEffect(() => {
    if (selectedArtifact && chatHistory.length > 0) {
      setChatHistoryByArtifact(prev => ({
        ...prev,
        [selectedArtifact.id]: chatHistory
      }))
    }
  }, [chatHistory, selectedArtifact?.id])

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

  // Prevent zoom issues and reset on unmount
  useEffect(() => {
    // Reset any zoom/transform on body/html. Bail early if values already correct to avoid needless writes.
    const resetZoom = () => {
      const bodyStyles = window.getComputedStyle(document.body)
      const htmlStyles = window.getComputedStyle(document.documentElement)

      if (bodyStyles.zoom !== '1') document.body.style.zoom = '1'
      if (htmlStyles.zoom !== '1') document.documentElement.style.zoom = '1'
      if (bodyStyles.transform !== 'none') document.body.style.transform = 'scale(1)'
      if (htmlStyles.transform !== 'none') document.documentElement.style.transform = 'scale(1)'

      document.body.style.maxWidth = '100%'
      document.body.style.overflowX = 'hidden'
      document.body.style.position = 'relative'
      document.documentElement.style.maxWidth = '100%'
      document.documentElement.style.overflowX = 'hidden'
      document.documentElement.style.position = 'relative'

      const viewportMeta = document.querySelector('meta[name="viewport"]')
      if (viewportMeta) {
        viewportMeta.setAttribute(
          'content',
          'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no'
        )
      }
    }

    // Run once on mount
    resetZoom()

    // Light-touch listeners instead of tight polling/MutationObservers
    const handleVisibilityChange = () => {
      if (!document.hidden) resetZoom()
    }
    const handleFocus = () => resetZoom()
    const handlePopState = () => resetZoom()
    const handleResize = () => resetZoom()
    const preventZoom = (e: WheelEvent | TouchEvent) => {
      if (e.ctrlKey || (e as TouchEvent).touches?.length > 1) {
        e.preventDefault()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('focus', handleFocus)
    window.addEventListener('popstate', handlePopState)
    window.addEventListener('resize', handleResize)
    window.addEventListener('wheel', preventZoom, { passive: false })
    window.addEventListener('touchstart', preventZoom, { passive: false })
    window.addEventListener('touchmove', preventZoom, { passive: false })

    return () => {
      resetZoom()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('focus', handleFocus)
      window.removeEventListener('popstate', handlePopState)
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('wheel', preventZoom)
      window.removeEventListener('touchstart', preventZoom)
      window.removeEventListener('touchmove', preventZoom)
    }
  }, [])

  /**
   * Handle AI chat message to modify prototype
   */
  const handleSendMessage = async () => {
    if (!chatMessage.trim() || !selectedArtifact) return

    const userMessage = chatMessage.trim()
    setChatMessage('')
    setIsModifying(true)

    // Add user message to chat
    setChatHistory((prev) => [...prev, { role: 'user', content: userMessage }])

    // Detect if this is a complex request (needs full redesign)
    const complexKeywords = ['redesign', 'completely', 'entire', 'full', 'whole', 'pretty', 'beautiful', 'modern', 'professional', 'overhaul', 'rework', 'redo']
    const isComplexRequest = complexKeywords.some(kw => userMessage.toLowerCase().includes(kw))

    // Use longer timeout for complex requests
    const timeoutMs = isComplexRequest ? 180000 : 90000 // 3 min for complex, 90s for simple

    // Add progress message for complex requests
    if (isComplexRequest) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `🎨 This looks like a bigger change - I'm working on a complete redesign. This may take up to 2-3 minutes...`,
        },
      ])
    }

    try {
      // Build context-aware prompt - optimized for efficiency
      const modificationPrompt = isComplexRequest
        ? `You are a professional UI/UX designer. Transform this basic HTML prototype into a beautiful, modern, polished design.

CURRENT HTML:
\`\`\`html
${htmlContent}
\`\`\`

USER REQUEST: "${userMessage}"

REQUIREMENTS:
1. Keep the same basic structure and functionality
2. Add modern styling: gradients, shadows, rounded corners, smooth transitions
3. Use a cohesive color palette (suggest using blues/purples for professional look, or warm colors for friendly feel)
4. Add proper spacing, padding, and typography
5. Make it responsive and visually appealing
6. Include CSS animations/transitions where appropriate
7. Use flexbox/grid for proper layout

OUTPUT: Return ONLY the complete, working HTML document. No explanations.`
        : `Modify this HTML based on the user's request.

HTML:
\`\`\`html
${htmlContent}
\`\`\`

REQUEST: "${userMessage}"

Return ONLY the complete modified HTML. No explanations or markdown.`

      // Call AI with timeout handling
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error(`Request timed out after ${timeoutMs / 1000} seconds.`)), timeoutMs)
      })

      const response = await Promise.race([
        sendChatMessage({
          message: modificationPrompt,
          conversation_history: [],
          include_project_context: false,
        }),
        timeoutPromise
      ])

      // Validate response
      if (!response || !response.message) {
        throw new Error('AI service returned empty response. Please try again.')
      }

      // Extract HTML from response - improved extraction to ignore explanatory text
      let modifiedHtml = extractHtmlFromResponse(response.message)

      // Validate we got actual HTML
      if (!modifiedHtml || modifiedHtml.length < 20) {
        throw new Error('AI could not generate valid HTML. Please try rephrasing your request.')
      }

      // Sanitize and add viewport meta
      modifiedHtml = sanitizeHtmlContent(modifiedHtml)

      // Update HTML content
      setHtmlContent(modifiedHtml)

      // Update artifact in store
      updateArtifact(selectedArtifact.id, {
        content: modifiedHtml,
        updated_at: new Date().toISOString(),
      })

      // AUTO-SAVE FIX: Persist to backend immediately to prevent changes disappearing
      // Previously, users would lose changes if navigating away before clicking Save
      try {
        await updateArtifactAPI(selectedArtifact.id, modifiedHtml, {
          source: 'interactive_editor_ai',
          auto_saved: true,
          saved_at: new Date().toISOString(),
        })
        console.log('✅ [InteractivePrototypeEditor] Auto-saved AI modification to backend')
      } catch (saveError) {
        console.warn('⚠️ [InteractivePrototypeEditor] Failed to auto-save:', saveError)
        // Don't show error to user - changes are still in local store
        // They can manually save with the Save button
      }

      // Add AI response to chat
      const successMessage = isComplexRequest
        ? `✨ I've completely redesigned your prototype with modern styling! Check the preview to see the transformation.`
        : `✅ Done! I've updated the prototype. Check the preview to see the changes.`

      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: successMessage,
        },
      ])

      addNotification('success', 'Prototype updated and saved!')
    } catch (error: any) {
      console.error('Failed to modify prototype:', error)

      // Build user-friendly error message
      let errorMsg = error.message || 'Unknown error occurred'
      let tip = 'Try simpler requests like "make the button blue" or "add a header".'

      if (error.message?.includes('timeout')) {
        errorMsg = 'Request timed out. The AI service may be overloaded.'
        tip = isComplexRequest
          ? 'For big redesigns, try breaking it into smaller steps: first colors, then layout, then animations.'
          : 'Try a simpler request or wait a moment and try again.'
      } else if (error.message?.includes('Network') || error.message?.includes('fetch')) {
        errorMsg = 'Network error. Please check your connection.'
        tip = 'Check your internet connection and try again.'
      } else if (error.response?.status === 500) {
        errorMsg = 'Server error. The AI service may be temporarily unavailable.'
        tip = 'Wait a moment and try again.'
      }

      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `❌ ${errorMsg}\n\n💡 **Tip:** ${tip}`,
        },
      ])
      addNotification('error', 'Failed to modify prototype')
    } finally {
      setIsModifying(false)
    }
  }

  /**
   * Extract HTML code from AI response, ignoring explanatory text
   */
  const extractHtmlFromResponse = (response: string): string => {
    let html = response.trim()

    // Step 1: Try to extract from markdown code blocks (```html or ```)
    const htmlCodeBlockPattern = /```(?:html)?\s*\n([\s\S]*?)```/i
    const codeBlockMatch = html.match(htmlCodeBlockPattern)
    if (codeBlockMatch && codeBlockMatch[1]) {
      html = codeBlockMatch[1].trim()
    } else {
      // Try generic code block
      const genericCodeBlockPattern = /```\s*\n([\s\S]*?)```/
      const genericMatch = html.match(genericCodeBlockPattern)
      if (genericMatch && genericMatch[1] && (genericMatch[1].includes('<!DOCTYPE') || genericMatch[1].includes('<html'))) {
        html = genericMatch[1].trim()
      }
    }

    // Step 2: Find HTML start (DOCTYPE or <html> tag)
    const doctypeIndex = html.indexOf('<!DOCTYPE')
    const htmlIndex = html.toLowerCase().indexOf('<html')

    if (doctypeIndex >= 0 || htmlIndex >= 0) {
      const startIndex = doctypeIndex >= 0 ? doctypeIndex : htmlIndex
      // Remove everything before HTML starts
      html = html.substring(startIndex)

      // Find HTML end
      const htmlEndIndex = html.toLowerCase().lastIndexOf('</html>')
      if (htmlEndIndex > 0) {
        html = html.substring(0, htmlEndIndex + 7)
      }
    } else {
      // Step 3: If no DOCTYPE/html tag, look for first HTML tag
      const firstTagIndex = html.indexOf('<')
      if (firstTagIndex > 0) {
        // Check if there's explanatory text before
        const before = html.substring(0, firstTagIndex).trim()
        // If it looks like explanatory text (not a comment), remove it
        if (before && !before.startsWith('<!--') && before.length > 10) {
          html = html.substring(firstTagIndex)
        }
      }

      // Remove trailing explanations after last tag
      const lastTagIndex = html.lastIndexOf('>')
      if (lastTagIndex > 0 && lastTagIndex < html.length - 1) {
        const after = html.substring(lastTagIndex + 1).trim()
        // If there's text after last tag that doesn't look like HTML, remove it
        if (after && !after.startsWith('<') && after.length > 10) {
          html = html.substring(0, lastTagIndex + 1)
        }
      }
    }

    // Step 4: Clean up any remaining markdown artifacts
    html = html.replace(/^```[\w\-]*\s*\n?/gm, '').replace(/\n?```\s*$/gm, '').trim()
    html = html.replace(/^`+/gm, '').replace(/`+$/gm, '').trim()

    return html
  }

  /**
   * Save current version of the artifact
   */
  const handleSave = async () => {
    if (!selectedArtifact || !htmlContent) {
      addNotification('error', 'No artifact or content to save')
      return
    }

    try {
      setIsSaving(true)

      // Update artifact in store
      updateArtifact(selectedArtifact.id, {
        content: htmlContent,
        updated_at: new Date().toISOString(),
      })

      // Save to backend
      await updateArtifactAPI(selectedArtifact.id, htmlContent, {
        source: 'interactive_editor',
        saved_at: new Date().toISOString(),
      })

      // Also create a new version
      try {
        const { default: api } = await import('../services/api')
        await api.post('/api/versions/create', {
          artifact_id: selectedArtifact.type,
          artifact_type: selectedArtifact.type,
          content: htmlContent,
          metadata: {
            source: 'interactive_editor',
            model_used: 'manual_edit',
            validation_score: 100,
            is_valid: true
          }
        })
        addNotification('success', 'Artifact saved as new version!')
      } catch (versionError) {
        console.warn('Failed to create version (version API may not exist):', versionError)
        addNotification('success', 'Artifact saved successfully!')
      }
    } catch (error: any) {
      console.error('Failed to save artifact:', error)
      addNotification('error', `Failed to save: ${error.message || 'Unknown error'}`)
    } finally {
      setIsSaving(false)
    }
  }

  /**
   * Handle quick actions
   */
  const handleQuickAction = (action: string) => {
    const quickPrompts: Record<string, string> = {
      'make-pretty': 'Make this look professional and modern with better colors, spacing, shadows, and typography',
      'make-responsive': 'Make this fully responsive for mobile devices',
      'add-animations': 'Add smooth hover effects and transitions',
      'dark-mode': 'Convert to a dark theme with good contrast',
    }
    setChatMessage(quickPrompts[action] || action)
  }


  // Get artifact type display name
  const getArtifactTypeName = () => {
    if (artifactType) {
      return artifactType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
    }
    return 'HTML Artifact'
  }

  // CRITICAL: Show skeleton while loading to prevent race condition
  // This fixes the bug where "No artifact" shows before data loads
  if (isLoading && prototypeArtifacts.length === 0) {
    return <PrototypeSkeleton />
  }

  // Empty state - only show after loading is complete
  if (prototypeArtifacts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Sparkles className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-lg font-medium text-muted-foreground mb-2">No {getArtifactTypeName()} available</p>
          <p className="text-sm text-muted-foreground mb-4">
            Generate a {getArtifactTypeName().toLowerCase()} first to use this AI editor
          </p>
          {/* Debug info */}
          <div className="flex items-center justify-center gap-2">
            <span className="px-2 py-1 rounded text-xs font-mono bg-green-500/20 text-green-600 dark:text-green-400">
              InteractivePrototypeEditor
            </span>
            <span className="px-2 py-1 rounded text-xs font-mono bg-gray-500/20 text-gray-600 dark:text-gray-400">
              type: {artifactType || 'none'}
            </span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full w-full flex flex-col lg:flex-row gap-3 overflow-visible min-h-0 interactive-prototype-container" style={{ contain: 'layout style paint', isolation: 'isolate', height: '100%', minHeight: '500px' }}>
      {/* Left: Preview/Code View - Full width when AI panel is closed */}
      <div className={`${isAIPanelOpen ? 'flex-[2]' : 'flex-1'} min-h-[200px] lg:min-h-0 min-w-0 flex flex-col bg-card border border-border rounded-xl overflow-auto shadow-lg transition-all duration-300`} style={{ maxHeight: '100%' }}>
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/20 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-foreground">{getArtifactTypeName()}</h3>
            {/* Debug badge showing actual type */}
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-green-500/20 text-green-600 dark:text-green-400">
              {artifactType || 'html'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('preview')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 transition-all ${viewMode === 'preview'
                ? 'bg-primary text-primary-foreground'
                : 'bg-background text-muted-foreground hover:text-foreground'
                }`}
            >
              <Eye size={14} />
              Preview
            </button>
            <button
              onClick={() => setViewMode('code')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 transition-all ${viewMode === 'code'
                ? 'bg-primary text-primary-foreground'
                : 'bg-background text-muted-foreground hover:text-foreground'
                }`}
            >
              <Code size={14} />
              Code
            </button>
            <div className="w-px h-6 bg-border mx-2"></div>
            <button
              onClick={handleSave}
              disabled={isSaving || !htmlContent}
              className="p-2 hover:bg-accent rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Save current version"
            >
              {isSaving ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Save size={16} />
              )}
            </button>
            <div className="w-px h-6 bg-border mx-2"></div>
            {/* Toggle AI Panel Button - More prominent when closed */}
            <button
              onClick={() => setIsAIPanelOpen(!isAIPanelOpen)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all ${isAIPanelOpen
                ? 'hover:bg-accent text-muted-foreground'
                : 'bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-lg hover:shadow-xl hover:scale-105'
                }`}
              title={isAIPanelOpen ? 'Hide AI Panel' : 'Open AI Modifier'}
            >
              {isAIPanelOpen ? (
                <PanelRightClose size={16} />
              ) : (
                <>
                  <Sparkles size={14} className="animate-pulse" />
                  <span className="text-sm font-medium hidden sm:inline">AI Modifier</span>
                  <PanelRightOpen size={16} />
                </>
              )}
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 overflow-auto bg-background relative" style={{ contain: 'layout style paint', maxHeight: '100%' }}>
          {!htmlContent ? (
            <div className="h-full flex items-center justify-center p-8">
              <div className="text-center">
                <Sparkles className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-lg font-medium text-muted-foreground mb-2">No HTML Content</p>
                <p className="text-sm text-muted-foreground">
                  {prototypeArtifacts.length === 0
                    ? 'Generate an HTML artifact first to use this editor'
                    : 'Select an artifact or generate a new one'}
                </p>
              </div>
            </div>
          ) : viewMode === 'preview' ? (
            <iframe
              ref={iframeRef}
              srcDoc={htmlContent}
              className="w-full h-full border-0"
              title="Prototype Preview"
              sandbox="allow-scripts"
              style={{
                transform: 'scale(1)',
                transformOrigin: 'top left',
                width: '100%',
                height: '100%',
                maxWidth: '100%',
                maxHeight: '100%',
                display: 'block',
                position: 'relative',
                contain: 'layout style paint',
              }}
              onLoad={() => {
                // Reset zoom when iframe loads
                try {
                  const iframe = iframeRef.current
                  if (iframe?.contentWindow) {
                    iframe.contentWindow.document.body.style.zoom = '1'
                    iframe.contentWindow.document.documentElement.style.zoom = '1'
                    iframe.contentWindow.document.body.style.transform = 'scale(1)'
                    iframe.contentWindow.document.documentElement.style.transform = 'scale(1)'
                  }
                } catch (e) {
                  // Cross-origin restrictions might prevent this
                  console.debug('Could not access iframe content:', e)
                }
                // Also reset parent page zoom
                document.body.style.zoom = '1'
                document.documentElement.style.zoom = '1'
                document.body.style.transform = 'scale(1)'
                document.documentElement.style.transform = 'scale(1)'
              }}
            />
          ) : (
            <textarea
              value={htmlContent}
              onChange={(e) => {
                const newContent = e.target.value
                setHtmlContent(newContent)

                // Debounced auto-save for manual edits (2s delay)
                // Clear existing timer
                if ((window as any)._autoSaveTimer) {
                  clearTimeout((window as any)._autoSaveTimer)
                }

                // Set new timer
                (window as any)._autoSaveTimer = setTimeout(async () => {
                  if (!selectedArtifact) return

                  console.log('💾 [InteractivePrototypeEditor] Auto-saving manual edits...')
                  try {
                    // Update store
                    updateArtifact(selectedArtifact.id, {
                      content: newContent,
                      updated_at: new Date().toISOString(),
                    })

                    // Save to backend
                    await updateArtifactAPI(selectedArtifact.id, newContent, {
                      source: 'interactive_editor_manual',
                      auto_saved: true,
                      saved_at: new Date().toISOString(),
                    })
                    console.log('✅ [InteractivePrototypeEditor] Manual edit auto-saved')
                  } catch (err) {
                    console.error('❌ [InteractivePrototypeEditor] Auto-save failed:', err)
                  }
                }, 2000)
              }}
              onBlur={() => {
                // Sanitize on blur to ensure viewport meta is present
                if (viewMode === 'code' && htmlContent) {
                  const sanitized = sanitizeHtmlContent(htmlContent)
                  if (sanitized !== htmlContent) {
                    setHtmlContent(sanitized)
                  }
                }
              }}
              className="w-full h-full p-4 font-mono text-sm resize-none bg-background text-foreground focus:outline-none overflow-auto"
              spellCheck={false}
            />
          )}
        </div>
      </div>

      {/* Right: AI Chat Panel - Collapsible */}
      <div className={`${isAIPanelOpen ? 'flex-1 lg:flex-none lg:w-80 xl:w-96' : 'hidden'} flex-shrink-0 flex flex-col bg-card border border-border rounded-xl overflow-hidden shadow-lg min-h-[200px] lg:min-h-0 transition-all duration-300`} style={{ maxHeight: '100%', height: '100%' }}>
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-border bg-secondary/20 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="w-5 h-5 text-primary" />
              <h3 className="font-bold text-foreground">AI Modifier</h3>
            </div>
            {/* Close Button */}
            <button
              onClick={() => setIsAIPanelOpen(false)}
              className="p-1.5 hover:bg-destructive/10 rounded-lg transition-colors text-muted-foreground hover:text-destructive"
              title="Close AI Panel"
            >
              <X size={18} />
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Tell me what you want to change
          </p>
        </div>

        {/* Quick Actions */}
        <div className="px-4 py-3 border-b border-border bg-background/50 flex-shrink-0">
          <p className="text-xs font-medium text-muted-foreground mb-2">Quick Actions:</p>
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'make-pretty', label: '✨ Make Pretty' },
              { id: 'make-responsive', label: '📱 Responsive' },
              { id: 'add-animations', label: '🎬 Animations' },
              { id: 'dark-mode', label: '🌙 Dark Theme' },
            ].map((action) => (
              <button
                key={action.id}
                onClick={() => handleQuickAction(action.id)}
                disabled={isModifying}
                className="px-2 py-1 rounded-md text-xs bg-secondary hover:bg-secondary/80 text-foreground transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4" style={{ WebkitOverflowScrolling: 'touch', overflowY: 'auto', maxHeight: '100%' }}>
          {chatHistory.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 rounded-lg ${msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-foreground'
                  }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {isModifying && (
            <div className="flex justify-start">
              <div className="bg-secondary px-4 py-2 rounded-lg">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Chat Input */}
        <div className="p-4 border-t border-border bg-background/50 flex-shrink-0">
          <div className="flex gap-2">
            <input
              type="text"
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
              placeholder="E.g., make the buttons bigger and blue..."
              className="flex-1 px-3 py-2 rounded-md border border-border bg-background text-foreground text-sm focus:outline-none focus:border-primary"
              disabled={isModifying}
            />
            <button
              onClick={handleSendMessage}
              disabled={!chatMessage.trim() || isModifying}
              className="px-4 py-2 rounded-md bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isModifying ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Send size={16} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

