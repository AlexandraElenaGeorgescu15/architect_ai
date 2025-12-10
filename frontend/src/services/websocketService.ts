import { WebSocketEvent } from '../types'

// Get WebSocket URL from environment or derive from current location
const getWebSocketBaseUrl = (): string => {
  // Check for explicit WS URL in environment
  const envWsUrl = import.meta.env.VITE_WS_URL
  if (envWsUrl) {
    return envWsUrl
  }
  
  // Check for API URL and convert to WebSocket
  const apiUrl = import.meta.env.VITE_API_URL
  if (apiUrl) {
    const url = new URL(apiUrl, window.location.origin)
    return `${url.protocol === 'https:' ? 'wss:' : 'ws:'}//${url.host}`
  }
  
  // In development, default to localhost:8000
  // In production, use current host
  if (import.meta.env.DEV) {
    return 'ws://localhost:8000'
  }
  
  // Production: use current origin with appropriate protocol
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

export type WebSocketEventType =
  | 'generation.progress'
  | 'generation.chunk'
  | 'generation.complete'
  | 'generation.error'
  | 'training.progress'
  | 'training.complete'
  | 'training.error'

export type EventHandler = (data: unknown) => void

class WebSocketService {
  private ws: WebSocket | null = null
  private roomId: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private eventHandlers: Map<WebSocketEventType, Set<EventHandler>> = new Map()
  private isConnecting = false
  private hasEverConnected = false
  private shouldReconnect = true

  /**
   * Connect to WebSocket server.
   */
  connect(roomId: string, token?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
        resolve()
        return
      }

      this.isConnecting = true
      this.roomId = roomId

      const wsBaseUrl = getWebSocketBaseUrl()
      const wsUrl = new URL(`${wsBaseUrl}/ws/${roomId}`)
      if (token) {
        wsUrl.searchParams.set('token', token)
      }

      try {
        this.ws = new WebSocket(wsUrl.toString())

        this.ws.onopen = () => {
          // WebSocket connected successfully
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.hasEverConnected = true
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data: WebSocketEvent = JSON.parse(event.data)
            this.handleEvent(data.type as WebSocketEventType, data.data)
          } catch (error) {
            // Error parsing WebSocket message - handle in UI
          }
        }

        this.ws.onerror = (error) => {
          // WebSocket error - handle in UI
          this.isConnecting = false
          reject(error)
        }

        this.ws.onclose = () => {
          // WebSocket disconnected
          this.isConnecting = false
          this.ws = null

          // Only attempt to reconnect if:
          // 1. We've successfully connected before (not just initial connection failure)
          // 2. We haven't exceeded max reconnection attempts
          // 3. We still have a roomId
          // 4. Reconnection is enabled
          if (this.hasEverConnected && this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts && this.roomId) {
            this.reconnectAttempts++
            setTimeout(() => {
              this.connect(this.roomId!, token).catch(() => {
                // Reconnect failed - handle in UI
              })
            }, this.reconnectDelay * this.reconnectAttempts)
          }
        }
      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  /**
   * Disconnect from WebSocket server.
   */
  disconnect(): void {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.roomId = null
    this.reconnectAttempts = 0
    this.eventHandlers.clear()
  }

  /**
   * Subscribe to a WebSocket event.
   */
  on(event: WebSocketEventType, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set())
    }
    this.eventHandlers.get(event)!.add(handler)

    // Return unsubscribe function
    return () => {
      this.eventHandlers.get(event)?.delete(handler)
    }
  }

  /**
   * Unsubscribe from a WebSocket event.
   */
  off(event: WebSocketEventType, handler: EventHandler): void {
    this.eventHandlers.get(event)?.delete(handler)
  }

  /**
   * Emit an event to the server (if supported).
   */
  emit(event: string, data: unknown): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: event, data }))
    }
  }

  /**
   * Check if WebSocket is connected.
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * Handle incoming WebSocket event.
   */
  private handleEvent(event: WebSocketEventType, data: unknown): void {
    const handlers = this.eventHandlers.get(event)
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data)
        } catch (error) {
          // Error in event handler - handle in UI
        }
      })
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService()
export default websocketService

