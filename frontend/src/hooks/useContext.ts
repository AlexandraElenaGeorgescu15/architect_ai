import { useState, useCallback } from 'react'
import { useContextStore } from '../stores/contextStore'
import { useUIStore } from '../stores/uiStore'
import {
  buildContext,
  getContext,
  ContextBuildRequest,
  ContextResponse,
} from '../services/contextService'
import { Context } from '../types'

export function useContext() {
  const [isBuilding, setIsBuilding] = useState(false)
  const { addContext, setCurrentContext } = useContextStore()
  const { addNotification } = useUIStore()

  const build = useCallback(
    async (request: ContextBuildRequest): Promise<ContextResponse> => {
      setIsBuilding(true)

      try {
        const response = await buildContext(request)

        // Fetch full context details
        const context = await getContext(response.context_id)
        addContext(context)
        setCurrentContext(context)

        setIsBuilding(false)
        addNotification('success', 'Context built successfully!')
        return response
      } catch (error: unknown) {
        setIsBuilding(false)
        let message = 'Context building failed'
        let suggestion = 'Please try again'
        
        if (error && typeof error === 'object' && 'response' in error) {
          const axiosError = error as { response?: { status?: number; data?: { detail?: string } } }
          const status = axiosError.response?.status
          
          if (status === 429) {
            message = 'Rate limit exceeded'
            suggestion = 'Please wait a moment and try again'
          } else if (status === 500) {
            message = 'Server error'
            suggestion = 'The server encountered an issue. Please try again in a moment.'
          } else if (status === 503) {
            message = 'Service unavailable'
            suggestion = 'The service is temporarily unavailable. Please try again later.'
          } else if (status === 400) {
            message = 'Invalid request'
            suggestion = axiosError.response?.data?.detail || 'Please check your meeting notes and try again'
          } else if (status === 401) {
            message = 'Authentication required'
            suggestion = 'Please log in and try again'
          }
        } else if (error instanceof Error) {
          if (error.message.includes('network') || error.message.includes('Network')) {
            message = 'Connection error'
            suggestion = 'Please check your internet connection and try again'
          } else if (error.message.includes('timeout')) {
            message = 'Request timeout'
            suggestion = 'The request took too long. Please try again'
          } else {
            message = error.message || 'Context building failed'
          }
        }
        
        addNotification('error', `${message}. ${suggestion}`)
        throw error
      }
    },
    [addContext, setCurrentContext, addNotification]
  )

  const loadContext = useCallback(
    async (contextId: string): Promise<Context> => {
      try {
        const context = await getContext(contextId)
        setCurrentContext(context)
        return context
      } catch (error: unknown) {
        let message = 'Failed to load context'
        let suggestion = 'Please try again'
        
        if (error && typeof error === 'object' && 'response' in error) {
          const axiosError = error as { response?: { status?: number } }
          const status = axiosError.response?.status
          
          if (status === 404) {
            message = 'Context not found'
            suggestion = 'The requested context does not exist'
          } else if (status === 500) {
            message = 'Server error'
            suggestion = 'The server encountered an issue. Please try again in a moment.'
          }
        } else if (error instanceof Error) {
          if (error.message.includes('network') || error.message.includes('Network')) {
            message = 'Connection error'
            suggestion = 'Please check your internet connection and try again'
          } else {
            message = error.message || 'Failed to load context'
          }
        }
        
        addNotification('error', `${message}. ${suggestion}`)
        throw error
      }
    },
    [setCurrentContext, addNotification]
  )

  return {
    isBuilding,
    build,
    loadContext,
  }
}

