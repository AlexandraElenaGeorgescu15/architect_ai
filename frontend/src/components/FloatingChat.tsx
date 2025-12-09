import { useState, useRef, useEffect, useCallback, memo } from 'react'
import { MessageSquare, X, Send, Bot, Minimize2, Maximize2 } from 'lucide-react'
import { sendChatMessage, streamChatMessage } from '../services/chatService'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

// Memoized message component to prevent re-renders
const ChatMessage = memo(function ChatMessage({ message }: { message: Message }) {
  return (
    <div
      className={`flex gap-3 animate-fade-in-up ${
        message.role === 'user' ? 'justify-end' : 'justify-start'
      }`}
    >
      {message.role === 'assistant' && (
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center flex-shrink-0 border border-primary/30 shadow-md">
          <Bot className="w-5 h-5 text-primary" />
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-2xl p-4 shadow-elegant transition-all duration-300 hover:shadow-elevated backdrop-blur-sm ${
          message.role === 'user'
            ? 'bg-gradient-to-br from-primary to-primary/90 text-primary-foreground shadow-primary/20 rounded-tr-none'
            : 'bg-card/80 text-foreground border border-border/50 rounded-tl-none'
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed line-clamp-[20]">{message.content}</p>
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
  const [isOpen, setIsOpen] = useState(false)
  const [isMinimized, setIsMinimized] = useState(true)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m Architect.AI. Ask me anything about your codebase, architecture, or requirements!',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    if (isOpen && !isMinimized) {
      scrollToBottom()
    }
  }, [messages, isOpen, isMinimized, scrollToBottom])

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
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      try {
        let fullResponse = ''
        for await (const chunk of streamChatMessage({
          message: currentInput,
          conversation_history: conversationHistory,
          include_project_context: true
        })) {
          fullResponse += chunk
          setMessages((prev) => prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: fullResponse }
              : msg
          ))
        }
      } catch (streamError) {
        // Streaming failed, using non-streaming
        const response = await sendChatMessage({
          message: currentInput,
          conversation_history: conversationHistory,
          include_project_context: true
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

  if (!isOpen) {
    return (
      <button
        onClick={() => {
          setIsOpen(true)
          setIsMinimized(false)
        }}
        className="fixed bottom-6 right-6 z-50 w-16 h-16 bg-gradient-to-br from-primary to-primary/80 text-primary-foreground rounded-full shadow-[0_8px_32px_rgba(37,99,235,0.4)] hover:shadow-[0_16px_48px_rgba(37,99,235,0.6)] flex items-center justify-center transition-all duration-500 hover:scale-110 hover:rotate-12 group border border-primary/20 animate-pulse"
        aria-label="Open chat"
      >
        <MessageSquare className="w-7 h-7 group-hover:scale-125 transition-transform duration-300" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-background animate-pulse shadow-[0_0_12px_rgba(34,197,94,0.8)]" />
      </button>
    )
  }

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 transition-all duration-500 ease-out ${
        isMinimized
          ? 'w-80 h-16'
          : 'w-[420px] h-[650px]'
      } animate-in slide-in-from-bottom-8 fade-in duration-700`}
    >
      <div className="h-full glass-panel border border-primary/30 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.3)] hover:shadow-[0_24px_72px_rgba(0,0,0,0.4)] flex flex-col overflow-hidden backdrop-blur-xl bg-card/95 dark:bg-card/95 transition-shadow duration-300">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border/30 bg-muted/20 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center animate-pulse-glow border border-primary/30 shadow-lg">
              <Bot className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="font-black text-foreground text-lg">Architect.AI</h3>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                Always Online
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-2.5 hover:bg-primary/10 rounded-xl transition-all duration-300 text-muted-foreground hover:text-primary shadow-sm hover:shadow-md group"
              aria-label={isMinimized ? 'Maximize' : 'Minimize'}
            >
              {isMinimized ? (
                <Maximize2 className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" />
              ) : (
                <Minimize2 className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" />
              )}
            </button>
            <button
              onClick={() => {
                setIsOpen(false)
                setIsMinimized(false)
              }}
              className="p-2.5 hover:bg-destructive/20 rounded-xl transition-all duration-300 text-muted-foreground hover:text-destructive shadow-sm hover:shadow-md group"
              aria-label="Close chat"
            >
              <X className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
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
                    <div className="flex gap-2">
                      <div className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-sm" style={{ animationDelay: '0ms' }} />
                      <div className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-sm" style={{ animationDelay: '150ms' }} />
                      <div className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-sm" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-5 border-t border-border/30 bg-gradient-to-r from-background/30 to-background/10 backdrop-blur-md">
              <div className="flex gap-3">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me anything..."
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
          </>
        )}
      </div>
    </div>
  )
}

export default memo(FloatingChat)
