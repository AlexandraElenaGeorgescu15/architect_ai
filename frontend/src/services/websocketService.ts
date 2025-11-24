import { WebSocketEvent } from '../types'

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

      const wsUrl = new URL(`ws://localhost:8000/ws/${roomId}`)
      if (token) {
        wsUrl.searchParams.set('token', token)
      }

      try {
        this.ws = new WebSocket(wsUrl.toString())

        this.ws.onopen = () => {
          // WebSocket connected successfully
          this.isConnecting = false
          this.reconnectAttempts = 0
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

          // Attempt to reconnect
          if (this.reconnectAttempts < this.maxReconnectAttempts && this.roomId) {
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

