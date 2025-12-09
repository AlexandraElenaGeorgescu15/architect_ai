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

  useEffect(() => {
    // Connect on mount if defaultRoomId is provided
    if (defaultRoomId) {
      connect(defaultRoomId, token).catch(() => {
        // WebSocket connection failed - notify user
        if (!connectionNotifiedRef.current) {
          addNotification('warning', 'Real-time updates unavailable - running in offline mode')
          connectionNotifiedRef.current = true
        }
      })
    }

    // Cleanup on unmount
    return () => {
      websocketService.disconnect()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run on mount

  const connect = async (newRoomId: string, newToken?: string) => {
    try {
      await websocketService.connect(newRoomId, newToken)
      setRoomId(newRoomId)
      setIsConnected(true)
      
      // Notify on reconnection (not initial connection)
      if (wasConnected.current && !connectionNotifiedRef.current) {
        addNotification('success', 'Reconnected to real-time updates')
      }
      wasConnected.current = true
      connectionNotifiedRef.current = false
    } catch (error) {
      // Failed to connect WebSocket - notify user
      setIsConnected(false)
      if (wasConnected.current && !connectionNotifiedRef.current) {
        addNotification('warning', 'Lost connection to real-time updates')
        connectionNotifiedRef.current = true
      }
    }
  }

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

  // Update connection status
  useEffect(() => {
    const interval = setInterval(() => {
      setIsConnected(websocketService.isConnected())
    }, 1000)

    return () => clearInterval(interval)
  }, [])

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

