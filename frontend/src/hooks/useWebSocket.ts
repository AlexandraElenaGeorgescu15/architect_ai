import { useEffect, useRef, useCallback } from 'react'
import { useWebSocketContext } from '../contexts/WebSocketContext'
import { WebSocketEventType, EventHandler } from '../services/websocketService'

/**
 * Hook for WebSocket event subscriptions.
 * Automatically cleans up subscriptions on unmount.
 */
export function useWebSocket(event: WebSocketEventType, handler: EventHandler) {
  const { on, off } = useWebSocketContext()
  const handlerRef = useRef(handler)

  // Update handler ref when it changes
  useEffect(() => {
    handlerRef.current = handler
  }, [handler])

  useEffect(() => {
    // Create wrapper that uses latest handler
    const wrappedHandler: EventHandler = (data) => {
      handlerRef.current(data)
    }

    const unsubscribe = on(event, wrappedHandler)

    return () => {
      off(event, wrappedHandler)
      unsubscribe()
    }
  }, [event, on, off])
}

/**
 * Hook for WebSocket connection status.
 */
export function useWebSocketStatus() {
  const { isConnected, roomId, connect, disconnect } = useWebSocketContext()

  return {
    isConnected,
    roomId,
    connect,
    disconnect,
  }
}

