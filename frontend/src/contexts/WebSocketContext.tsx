import React, { createContext, useContext, useEffect, useState, useRef, ReactNode } from 'react'
import websocketService, { WebSocketEventType, EventHandler } from '../services/websocketService'
import { useUIStore } from '../stores/uiStore'

interface WebSocketContextType {
  isConnected: boolean
  roomId: string | null
  connect: (roomId: string, token?: string) => Promise<void>
  disconnect: () => void
  on: (event: WebSocketEventType, handler: EventHandler) => () => void
  off: (event: WebSocketEventType, handler: EventHandler) => void
  emit: (event: string, data: unknown) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
  defaultRoomId?: string
  token?: string
}

export function WebSocketProvider({
  children,
  defaultRoomId,
  token,
}: WebSocketProviderProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [roomId, setRoomId] = useState<string | null>(defaultRoomId || null)
  const { addNotification } = useUIStore()
  const wasConnected = useRef(false)
  const connectionNotifiedRef = useRef(false)
  const initialConnectionFailedRef = useRef(false)
  const warnedLostConnectionRef = useRef(false) // only warn once per session after a successful connect
  const mountedRef = useRef(true)

  const connect = async (newRoomId: string, newToken?: string) => {
    try {
      await websocketService.connect(newRoomId, newToken)
      if (!mountedRef.current) return
      
      setRoomId(newRoomId)
      setIsConnected(true)
      
      // Notify on reconnection (not initial connection)
      if (wasConnected.current && !connectionNotifiedRef.current) {
        addNotification('success', 'Reconnected to real-time updates')
      }
      wasConnected.current = true
      // Reset warning throttle only after a successful reconnect
      connectionNotifiedRef.current = false
    } catch (error) {
      if (!mountedRef.current) return
      
      // Failed to connect WebSocket
      setIsConnected(false)
      // Only notify if user was previously connected (not on initial connection failure)
      if (
        wasConnected.current &&
        !connectionNotifiedRef.current &&
        !initialConnectionFailedRef.current &&
        !warnedLostConnectionRef.current
      ) {
        addNotification('warning', 'Lost connection to real-time updates')
        connectionNotifiedRef.current = true // throttle within reconnect attempts
        warnedLostConnectionRef.current = true // throttle across the whole session
      }
    }
  }

  useEffect(() => {
    mountedRef.current = true
    
    // Connect on mount if defaultRoomId is provided
    if (defaultRoomId) {
      connect(defaultRoomId, token).catch(() => {
        // WebSocket connection failed on initial connection - silently continue in offline mode
        // Don't notify user unless they were previously connected
        initialConnectionFailedRef.current = true
      })
    }

    // Cleanup on unmount
    return () => {
      mountedRef.current = false
      websocketService.disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run on mount

  const disconnect = () => {
    websocketService.disconnect()
    setRoomId(null)
    setIsConnected(false)
  }

  const on = (event: WebSocketEventType, handler: EventHandler) => {
    return websocketService.on(event, handler)
  }

  const off = (event: WebSocketEventType, handler: EventHandler) => {
    websocketService.off(event, handler)
  }

  const emit = (event: string, data: unknown) => {
    websocketService.emit(event, data)
  }

  // Disabled connection status polling to prevent performance issues
  // Connection status is updated only on connect/disconnect events

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        roomId,
        connect,
        disconnect,
        on,
        off,
        emit,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider')
  }
  return context
}

