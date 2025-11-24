/**
 * Interactive Prototype Editor with AI Chat
 * Allows users to modify visual prototypes through natural language conversation
 */

import { useState, useEffect, useRef } from 'react'
import { Loader2, Wand2, MessageSquare, Code, Eye, Send, Sparkles, Download, RefreshCw } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { sendChatMessage } from '../services/chatService'

export default function InteractivePrototypeEditor() {
  const { artifacts, updateArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()

  // Get visual prototype artifacts
  const prototypeArtifacts = artifacts.filter(
    (a) => a.type === 'dev_visual_prototype' || a.type === 'html_prototype'
  )

  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [htmlContent, setHtmlContent] = useState('')
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [isModifying, setIsModifying] = useState(false)
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

  // Load artifact content
  useEffect(() => {
    if (selectedArtifact) {
      setHtmlContent(selectedArtifact.content)
      setChatHistory([
        {
          role: 'assistant',
          content: `Hi! I can help you modify this prototype. Tell me what you'd like to change - styles, layout, functionality, content, or anything else!`,
        },
      ])
    }
  }, [selectedArtifact?.id])

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatHistory])

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

      // Call AI to generate modified prototype
      const response = await sendChatMessage({
        message: modificationPrompt,
        conversation_history: [],
        include_project_context: false,
      })

      // Extract HTML from response (remove markdown if present)
      let modifiedHtml = response.message.trim()
      modifiedHtml = modifiedHtml.replace(/```html\n?/g, '').replace(/```\n?/g, '').trim()

      // Update HTML content
      setHtmlContent(modifiedHtml)

      // Update artifact in store
      updateArtifact(selectedArtifact.id, {
        content: modifiedHtml,
        lastModified: new Date().toISOString(),
      })

      // Add AI response to chat
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `I've updated the prototype based on your request. Check the preview to see the changes!`,
        },
      ])

      addNotification({
        type: 'success',
        message: 'Prototype updated successfully!',
      })
    } catch (error: any) {
      console.error('Failed to modify prototype:', error)
      setChatHistory((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
        },
      ])
      addNotification({
        type: 'error',
        message: 'Failed to modify prototype',
      })
    } finally {
      setIsModifying(false)
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

  /**
   * Download prototype as HTML file
   */
  const handleDownload = () => {
    if (!selectedArtifact) return

    const blob = new Blob([htmlContent], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedArtifact.id}-prototype.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    addNotification({
      type: 'success',
      message: 'Prototype downloaded!',
    })
  }

  // Empty state
  if (prototypeArtifacts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Sparkles className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p className="text-lg font-medium text-muted-foreground mb-2">No prototypes available</p>
          <p className="text-sm text-muted-foreground">
            Generate a visual prototype first to use this editor
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex gap-4">
      {/* Left: Preview/Code View */}
      <div className="flex-1 flex flex-col bg-card border border-border rounded-xl overflow-hidden shadow-lg">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-secondary/20">
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
              onClick={handleDownload}
              className="px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-1.5 bg-background text-muted-foreground hover:text-foreground transition-all"
              title="Download HTML"
            >
              <Download size={14} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto bg-background">
          {viewMode === 'preview' ? (
            <iframe
              ref={iframeRef}
              srcDoc={htmlContent}
              className="w-full h-full border-0"
              title="Prototype Preview"
              sandbox="allow-scripts"
            />
          ) : (
            <textarea
              value={htmlContent}
              onChange={(e) => setHtmlContent(e.target.value)}
              className="w-full h-full p-4 font-mono text-sm resize-none bg-background text-foreground focus:outline-none"
              spellCheck={false}
            />
          )}
        </div>
      </div>

      {/* Right: AI Chat Panel */}
      <div className="w-96 flex flex-col bg-card border border-border rounded-xl overflow-hidden shadow-lg">
        {/* Chat Header */}
        <div className="px-4 py-3 border-b border-border bg-secondary/20">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" />
            <h3 className="font-bold text-foreground">AI Modifier</h3>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Tell me what you want to change
          </p>
        </div>

        {/* Quick Actions */}
        <div className="px-4 py-3 border-b border-border bg-background/50">
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
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
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
        <div className="p-4 border-t border-border bg-background/50">
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

