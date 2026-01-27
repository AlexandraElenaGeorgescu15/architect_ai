import { useState, useRef, useEffect, useCallback, memo } from 'react'
import { createPortal } from 'react-dom'
import { MessageSquare, X, Send, Bot, FileCode, GitBranch, Sparkles, Trash2, Zap, Search, Edit3, AlertTriangle } from 'lucide-react'
import {
  sendChatMessage,
  streamChatMessage,
  getProjectSummary,
  ProjectSummary,
  getOrCreateSessionId,
  saveConversationToStorage,
  loadConversationFromStorage,
  clearChatSession,
  ChatMessage as ServiceChatMessage
} from '../services/chatService'
import { useArtifactStore } from '../stores/artifactStore'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const DEFAULT_GREETING = "Hello! I'm Architect.AI. Ask me anything about your codebase, architecture, or requirements!"

// Memoized message component to prevent re-renders
const ChatMessage = memo(function ChatMessage({ message }: { message: Message }) {
  return (
    <div
      className={`flex gap-3 animate-fade-in-up ${message.role === 'user' ? 'justify-end' : 'justify-start'
        }`}
    >
      {message.role === 'assistant' && (
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center flex-shrink-0 border border-primary/30 shadow-md">
          <Bot className="w-5 h-5 text-primary" />
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-2xl p-4 shadow-elegant transition-all duration-300 hover:shadow-elevated backdrop-blur-sm ${message.role === 'user'
            ? 'bg-gradient-to-br from-primary to-primary/90 text-primary-foreground shadow-primary/20 rounded-tr-none'
            : 'bg-card/80 text-foreground border border-border/50 rounded-tl-none'
          }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed break-words">{message.content}</p>
        <p className="text-[10px] opacity-70 mt-2 text-right font-mono">
          {message.timestamp.toLocaleTimeString()}
        </p>
      </div>
      {message.role === 'user' && (
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center flex-shrink-0 shadow-lg shadow-primary/30">
          <div className="w-5 h-5 rounded-full bg-primary-foreground/30" />
        </div>
      )}
    </div>
  )
})

function FloatingChat() {
  const [portalEl, setPortalEl] = useState<HTMLElement | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null)
  const [summaryLoaded, setSummaryLoaded] = useState(false)
  const [sessionId] = useState<string>(() => getOrCreateSessionId())
  const [messagesLoaded, setMessagesLoaded] = useState(false)

  // Get current folder ID from artifact store for meeting notes context
  const { currentFolderId } = useArtifactStore()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: DEFAULT_GREETING,
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agenticMode, setAgenticMode] = useState(() => {
    const saved = localStorage.getItem('chat_agentic_mode')
    return saved !== null ? JSON.parse(saved) : true
  })
  const [writeMode, setWriteMode] = useState(() => {
    const saved = localStorage.getItem('chat_write_mode')
    return saved !== null ? JSON.parse(saved) : false
  })
  const [currentToolStatus, setCurrentToolStatus] = useState<string | null>(null)
  const [showWriteConfirm, setShowWriteConfirm] = useState(false)  // Confirmation dialog for write mode

  // Persist mode settings
  useEffect(() => {
    localStorage.setItem('chat_agentic_mode', JSON.stringify(agenticMode))
  }, [agenticMode])

  useEffect(() => {
    localStorage.setItem('chat_write_mode', JSON.stringify(writeMode))
  }, [writeMode])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load conversation from storage on mount (session persistence)
  useEffect(() => {
    if (!messagesLoaded) {
      const savedMessages = loadConversationFromStorage()
      if (savedMessages.length > 0) {
        // Convert saved format to our Message format
        const restored: Message[] = savedMessages.map((msg, idx) => ({
          id: `restored_${idx}`,
          role: msg.role,
          content: msg.content,
          timestamp: new Date()
        }))
        // Add greeting if first message isn't from assistant
        // Note: restored.length > 0 is guaranteed since savedMessages.length > 0
        if (restored[0].role !== 'assistant') {
          restored.unshift({
            id: '1',
            role: 'assistant',
            content: DEFAULT_GREETING,
            timestamp: new Date()
          })
        }
        setMessages(restored)
        console.log(`[FloatingChat] Restored ${savedMessages.length} messages from session ${sessionId}`)
      }
      setMessagesLoaded(true)
    }
  }, [messagesLoaded, sessionId])

  // Save conversation to storage whenever messages change
  useEffect(() => {
    if (messagesLoaded && messages.length > 1) {
      const toSave: ServiceChatMessage[] = messages
        .filter(m => m.role === 'user' || (m.role === 'assistant' && m.content !== DEFAULT_GREETING))
        .map(m => ({ role: m.role, content: m.content }))
      saveConversationToStorage(toSave)
    }
  }, [messages, messagesLoaded])

  // Handler to clear conversation
  const handleClearConversation = useCallback(() => {
    clearChatSession()
    setMessages([{
      id: '1',
      role: 'assistant',
      content: DEFAULT_GREETING,
      timestamp: new Date()
    }])
    setSummaryLoaded(false) // Re-fetch summary for fresh greeting
  }, [])

  // Mount a portal so chat always sits above page content
  useEffect(() => {
    const el = document.createElement('div')
    el.id = 'floating-chat-portal'
    el.style.position = 'fixed'
    el.style.top = '0'
    el.style.left = '0'
    el.style.width = '0'
    el.style.height = '0'
    el.style.pointerEvents = 'none'
    el.style.zIndex = '9999'
    el.style.overflow = 'visible'
    document.body.appendChild(el)
    setPortalEl(el)
    return () => {
      if (document.body.contains(el)) {
        document.body.removeChild(el)
      }
    }
  }, [])

  // Fetch project summary when chat is first opened
  useEffect(() => {
    if (isOpen && !summaryLoaded) {
      const fetchSummary = async () => {
        try {
          const summary = await getProjectSummary()
          setProjectSummary(summary)

          // Update the greeting message with project-specific info
          if (summary.greeting_message) {
            setMessages(prev => {
              const newMessages = [...prev]
              if (newMessages.length > 0 && newMessages[0].role === 'assistant') {
                newMessages[0] = {
                  ...newMessages[0],
                  content: summary.greeting_message
                }
              }
              return newMessages
            })
          }
        } catch (error) {
          console.warn('Could not fetch project summary:', error)
          // Keep default greeting on error
        } finally {
          setSummaryLoaded(true)
        }
      }
      fetchSummary()
    }
  }, [isOpen, summaryLoaded])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    if (isOpen) {
      scrollToBottom()
    }
  }, [messages, isOpen, scrollToBottom])

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const currentInput = input
    setInput('')
    setIsLoading(true)

    const assistantMessageId = (Date.now() + 1).toString()
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, assistantMessage])

    try {
      // Build conversation history for context
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      try {
        let fullResponse = ''
        setCurrentToolStatus(null)

        // Pass session_id for persistent context across messages
        // Use agentic mode if enabled, and write mode if both agentic and write are enabled
        // Include folder_id for meeting notes context
        for await (const chunk of streamChatMessage({
          message: currentInput,
          conversation_history: conversationHistory,
          include_project_context: true,
          session_id: sessionId,
          folder_id: currentFolderId || undefined
        }, agenticMode, writeMode)) {
          if (chunk.type === 'status') {
            // Tool status update - show what the agent is doing
            const statusIcon = chunk.is_write_tool ? '✏️' : '🔍'
            setCurrentToolStatus(`${statusIcon} ${chunk.content}`)
          } else if (chunk.type === 'chunk') {
            // Clear tool status when content starts flowing
            setCurrentToolStatus(null)
            fullResponse += chunk.content
            setMessages((prev) => prev.map(msg =>
              msg.id === assistantMessageId
                ? { ...msg, content: fullResponse }
                : msg
            ))
          }
        }
        setCurrentToolStatus(null)
      } catch (streamError) {
        // Streaming failed, using non-streaming fallback
        setCurrentToolStatus(null)
        const response = await sendChatMessage({
          message: currentInput,
          conversation_history: conversationHistory,
          include_project_context: true,
          session_id: sessionId,
          folder_id: currentFolderId || undefined
        })
        setMessages((prev) => prev.map(msg =>
          msg.id === assistantMessageId
            ? { ...msg, content: response.message }
            : msg
        ))
      }
    } catch (error) {
      // Chat error - update message state
      setMessages((prev) => prev.map(msg =>
        msg.id === assistantMessageId
          ? { ...msg, content: 'Sorry, I encountered an error. Please try again.' }
          : msg
      ))
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, messages])

  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  // If portal not ready yet, render inline fallback
  if (!portalEl) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-[2100] w-16 h-16 bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-full shadow-[0_8px_32px_rgba(37,99,235,0.4)] hover:shadow-[0_16px_48px_rgba(37,99,235,0.6)] flex items-center justify-center transition-all duration-500 hover:scale-110 hover:rotate-12 group border border-primary/20 animate-pulse"
        aria-label="Open chat"
      >
        <MessageSquare className="w-7 h-7 group-hover:scale-125 transition-transform duration-300" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-background animate-pulse shadow-[0_0_12px_rgba(34,197,94,0.8)]" />
      </button>
    )
  }

  const launcher = (
    <button
      onClick={() => setIsOpen(true)}
      className="pointer-events-auto fixed bottom-6 right-6 z-[2100] w-16 h-16 bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-full shadow-[0_8px_32px_rgba(37,99,235,0.4)] hover:shadow-[0_16px_48px_rgba(37,99,235,0.6)] flex items-center justify-center transition-all duration-500 hover:scale-110 hover:rotate-12 group border border-primary/20 animate-pulse"
      aria-label="Open chat"
    >
      <MessageSquare className="w-7 h-7 group-hover:scale-125 transition-transform duration-300" />
      <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-background animate-pulse shadow-[0_0_12px_rgba(34,197,94,0.8)]" />
    </button>
  )

  const chatWindow = (
    <div
      className="pointer-events-auto fixed bottom-6 right-6 z-[2100] transition-all duration-500 ease-out w-[420px] h-[650px] animate-in slide-in-from-bottom-8 fade-in duration-700"
    >
      <div className="h-full glass-panel border border-primary/30 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.3)] hover:shadow-[0_24px_72px_rgba(0,0,0,0.4)] flex flex-col overflow-hidden backdrop-blur-xl bg-card/95 dark:bg-card/95 transition-shadow duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border/30 bg-muted/20 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center animate-pulse-glow border border-primary/30 shadow-lg">
              <Bot className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="font-black text-foreground text-lg">
                {projectSummary?.project_name || 'Architect.AI'}
              </h3>
              {projectSummary && projectSummary.indexed_files > 0 ? (
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1 bg-primary/10 px-1.5 py-0.5 rounded-full">
                    <FileCode className="w-3 h-3 text-primary" />
                    <span className="font-bold text-primary">{projectSummary.indexed_files}</span> files
                  </span>
                  {projectSummary.knowledge_graph_stats.nodes > 0 && (
                    <span className="flex items-center gap-1 bg-green-500/10 px-1.5 py-0.5 rounded-full">
                      <GitBranch className="w-3 h-3 text-green-500" />
                      <span className="font-bold text-green-500">{projectSummary.knowledge_graph_stats.nodes}</span> nodes
                    </span>
                  )}
                </div>
              ) : (
                <p className="text-[10px] text-amber-500 uppercase tracking-widest font-bold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                  ⚠️ Not indexed - Go to Intelligence → Reindex Projects
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Clear conversation button */}
            <button
              onClick={handleClearConversation}
              className="p-2.5 hover:bg-orange-500/20 rounded-xl transition-all duration-300 text-muted-foreground hover:text-orange-500 shadow-sm hover:shadow-md group"
              aria-label="Clear conversation"
              title="Clear conversation and start fresh"
            >
              <Trash2 className="w-4 h-4 group-hover:scale-110 transition-transform" />
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-2.5 hover:bg-destructive/20 rounded-xl transition-all duration-300 text-muted-foreground hover:text-destructive shadow-sm hover:shadow-md group"
              aria-label="Close chat"
            >
              <X className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar bg-gradient-to-b from-background/10 to-background/5">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {isLoading && (
            <div className="flex gap-3 justify-start animate-fade-in-up">
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center border border-primary/30 shadow-md">
                <Bot className="w-5 h-5 text-primary animate-pulse" />
              </div>
              <div className="bg-card/80 rounded-2xl p-4 border border-border/50 shadow-md">
                {currentToolStatus ? (
                  // Show what the agent is doing
                  <div className="flex items-center gap-2 text-sm text-primary">
                    <Search className="w-4 h-4 animate-pulse" />
                    <span className="font-medium">{currentToolStatus}</span>
                  </div>
                ) : (
                  // Default typing indicator
                  <div className="flex gap-2">
                    <div className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-sm" style={{ animationDelay: '0ms' }} />
                    <div className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-sm" style={{ animationDelay: '150ms' }} />
                    <div className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-sm" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-5 border-t border-border/30 bg-gradient-to-r from-background/30 to-background/10 backdrop-blur-md">
          {/* Mode Toggles */}
          <div className="flex items-center justify-between mb-3 px-1 gap-2">
            <div className="flex items-center gap-2">
              {/* Agentic Mode Toggle */}
              <button
                onClick={() => setAgenticMode(!agenticMode)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${agenticMode
                    ? 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-500 border border-amber-500/30 shadow-sm'
                    : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                  }`}
                title={agenticMode ? 'Agent mode: AI will search codebase when needed' : 'Basic mode: Uses pre-loaded context only'}
              >
                <Zap className={`w-3.5 h-3.5 ${agenticMode ? 'animate-pulse' : ''}`} />
                {agenticMode ? 'Agent' : 'Basic'}
              </button>

              {/* Write Mode Toggle - Only visible in agentic mode */}
              {agenticMode && (
                <button
                  onClick={() => {
                    if (!writeMode) {
                      setShowWriteConfirm(true)
                    } else {
                      setWriteMode(false)
                    }
                  }}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${writeMode
                      ? 'bg-gradient-to-r from-red-500/20 to-orange-500/20 text-red-500 border border-red-500/30 shadow-sm'
                      : 'bg-muted/50 text-muted-foreground hover:bg-muted'
                    }`}
                  title={writeMode ? 'Write mode: AI can modify artifacts (click to disable)' : 'Enable write mode to let AI modify artifacts'}
                >
                  <Edit3 className={`w-3 h-3 ${writeMode ? 'animate-pulse' : ''}`} />
                  {writeMode ? 'Write' : 'Read'}
                </button>
              )}
            </div>
            <span className="text-[10px] text-muted-foreground">
              {writeMode ? '✏️ Can modify artifacts' : agenticMode ? '🔍 Can search & explore' : '📄 Pre-loaded context'}
            </span>
          </div>

          {/* Write Mode Confirmation Dialog */}
          {showWriteConfirm && (
            <div className="mb-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-xs font-medium text-yellow-600 dark:text-yellow-400 mb-1">
                    Enable Write Mode?
                  </p>
                  <p className="text-[10px] text-yellow-600/80 dark:text-yellow-400/80 mb-2">
                    The AI will be able to update artifacts, create new artifacts, and save files to the outputs folder.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setWriteMode(true)
                        setShowWriteConfirm(false)
                      }}
                      className="px-2 py-1 text-[10px] font-medium bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
                    >
                      Enable Write Mode
                    </button>
                    <button
                      onClick={() => setShowWriteConfirm(false)}
                      className="px-2 py-1 text-[10px] font-medium bg-muted text-muted-foreground rounded hover:bg-muted/80 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={agenticMode ? "Ask anything - I'll search the codebase if needed..." : "Ask me anything..."}
              className="flex-1 p-4 text-sm border border-border/50 rounded-xl bg-card/50 text-foreground resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all duration-300 shadow-sm focus:shadow-md placeholder:text-muted-foreground/70"
              rows={1}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="px-5 py-3 bg-gradient-to-r from-primary to-primary/90 text-primary-foreground rounded-xl hover:from-primary/90 hover:to-primary disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center gap-2 shadow-lg hover:shadow-xl hover:shadow-primary/50 hover:scale-105 active:scale-100 font-bold"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )

  return createPortal(
    isOpen ? chatWindow : launcher,
    portalEl
  )
}

export default memo(FloatingChat)
