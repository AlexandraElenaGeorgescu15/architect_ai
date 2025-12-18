/**
 * Interactive Prototype Editor with AI Chat
 * Allows users to modify visual prototypes and ALL HTML artifacts through natural language conversation
 */

import { useState, useEffect, useRef } from 'react'
import { Loader2, MessageSquare, Code, Eye, Send, Sparkles, RefreshCw } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { sendChatMessage } from '../services/chatService'
import { updateArtifact as updateArtifactAPI } from '../services/generationService'

interface InteractivePrototypeEditorProps {
  artifactType?: string  // Optional: specific artifact type to filter by
}

export default function InteractivePrototypeEditor({ artifactType }: InteractivePrototypeEditorProps) {
  const { artifacts, updateArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()

  // Get HTML artifacts - filter by specific type if provided, otherwise get all HTML types
  const prototypeArtifacts = artifacts.filter((a) => {
    if (artifactType) {
      return a.type === artifactType
    }
    // Default: get all HTML-like artifacts
    return a.type === 'dev_visual_prototype' || 
           a.type === 'html_prototype' || 
           a.type.startsWith('html_')
  })

  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState('')
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [isModifying, setIsModifying] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [chatHistoryByArtifact, setChatHistoryByArtifact] = useState<Record<string, Array<{ role: 'user' | 'assistant'; content: string }>>>({})
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Get selected artifact
  const selectedArtifact = selectedArtifactId
    ? artifacts.find((a) => a.id === selectedArtifactId)
    : prototypeArtifacts[0] || null

  // Initialize with first artifact
  useEffect(() => {
    if (prototypeArtifacts.length > 0 && !selectedArtifactId) {
      setSelectedArtifactId(prototypeArtifacts[0].id)
    }
  }, [prototypeArtifacts.length, selectedArtifactId])

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
            content: `Hi! I can help you modify this ${typeName}. Tell me what you'd like to change:\n\n• **Styles**: colors, fonts, spacing, layout\n• **Content**: text, images, placeholders\n• **Functionality**: buttons, forms, interactions\n• **Structure**: add/remove components\n\nJust describe what you want, and I'll update the HTML!`,
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

    try {
      // Build context-aware prompt
      const modificationPrompt = `
I have an HTML prototype that I want to modify. Here's the current code:

\`\`\`html
${htmlContent}
\`\`\`

User request: "${userMessage}"

Please provide the COMPLETE modified HTML code (not just the changes). Include all necessary HTML, CSS, and JavaScript. Make sure it's a full, working HTML document.

Return ONLY the HTML code, no explanations or markdown code blocks.
`

      // Call AI to generate modified prototype with extended timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout
      
      try {
        const response = await sendChatMessage({
          message: modificationPrompt,
          conversation_history: [],
          include_project_context: false,
        })
        clearTimeout(timeoutId)

      // Extract HTML from response - improved extraction to ignore explanatory text
      let modifiedHtml = extractHtmlFromResponse(response.message)

      // Sanitize and add viewport meta
      modifiedHtml = sanitizeHtmlContent(modifiedHtml)

      // Update HTML content
      setHtmlContent(modifiedHtml)

      // Update artifact in store
      updateArtifact(selectedArtifact.id, {
        content: modifiedHtml,
        updated_at: new Date().toISOString(),
      })

      // Add AI response to chat
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `I've updated the prototype based on your request. Check the preview to see the changes!`,
        },
      ])

        addNotification('success', 'Prototype updated successfully!')
      } catch (innerError: any) {
        console.error('Failed to modify prototype:', innerError)
        const errorMsg = innerError.name === 'AbortError' 
          ? 'Request timed out after 60 seconds. Please try a simpler modification.'
          : innerError.message
        setChatHistory((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `Sorry, I encountered an error: ${errorMsg}. Please try again.`,
          },
        ])
        addNotification('error', 'Failed to modify prototype')
      }
    } catch (error: any) {
      console.error('Failed to modify prototype:', error)
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
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
      'make-responsive': 'Make this prototype fully responsive for mobile devices',
      'improve-colors': 'Improve the color scheme and make it more modern',
      'add-animations': 'Add smooth animations and transitions',
      'dark-mode': 'Add dark mode support with a toggle button',
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

  // Empty state
  if (prototypeArtifacts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Sparkles className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-lg font-medium text-muted-foreground mb-2">No {getArtifactTypeName()} available</p>
          <p className="text-sm text-muted-foreground">
            Generate a {getArtifactTypeName().toLowerCase()} first to use this AI editor
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full w-full flex flex-col lg:flex-row gap-3 overflow-visible min-h-0 interactive-prototype-container" style={{ contain: 'layout style paint', isolation: 'isolate', height: '100%', minHeight: '500px' }}>
      {/* Left: Preview/Code View */}
      <div className="flex-[2] min-h-[200px] lg:min-h-0 min-w-0 flex flex-col bg-card border border-border rounded-xl overflow-auto shadow-lg" style={{ maxHeight: '100%' }}>
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/20 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-foreground">Interactive Prototype</h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('preview')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 transition-all ${
                viewMode === 'preview'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:text-foreground'
              }`}
            >
              <Eye size={14} />
              Preview
            </button>
            <button
              onClick={() => setViewMode('code')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 transition-all ${
                viewMode === 'code'
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
                <RefreshCw size={16} className="animate-spin" />
              ) : (
                <RefreshCw size={16} />
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
                // Update content without resetting chat history
                setHtmlContent(e.target.value)
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

      {/* Right: AI Chat Panel */}
      <div className="flex-1 lg:flex-none lg:w-80 xl:w-96 flex-shrink-0 flex flex-col bg-card border border-border rounded-xl overflow-hidden shadow-lg min-h-[200px] lg:min-h-0" style={{ maxHeight: '100%', height: '100%' }}>
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-border bg-secondary/20 flex-shrink-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-foreground">AI Modifier</h3>
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
              { id: 'make-responsive', label: '📱 Responsive' },
              { id: 'improve-colors', label: '🎨 Better Colors' },
              { id: 'add-animations', label: '✨ Animations' },
              { id: 'dark-mode', label: '🌙 Dark Mode' },
            ].map((action) => (
              <button
                key={action.id}
                onClick={() => handleQuickAction(action.id)}
                className="px-2 py-1 rounded-md text-xs bg-secondary hover:bg-secondary/80 text-foreground transition-all"
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
                className={`max-w-[80%] px-4 py-2 rounded-lg ${
                  msg.role === 'user'
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

