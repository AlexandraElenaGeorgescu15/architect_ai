import { useEffect, useRef } from 'react'
import { useModelStore } from '../stores/modelStore'

/**
 * Hook for auto-refreshing models with proper cleanup.
 * 
 * This replaces the module-level interval in modelStore.ts that
 * could leak during HMR or if component trees unmount unexpectedly.
 * 
 * @param intervalMs - Refresh interval in milliseconds (default: 30000)
 * @param enabled - Whether auto-refresh is enabled (default: true)
 */
export function useAutoRefreshModels(intervalMs: number = 30000, enabled: boolean = true): void {
  const fetchModels = useModelStore(state => state.fetchModels)
  const isLoading = useModelStore(state => state.isLoading)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  useEffect(() => {
    if (!enabled) {
      // Clear any existing interval if disabled
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }
    
    // Start the refresh interval
    intervalRef.current = setInterval(() => {
      // Only fetch if not already loading to prevent overlapping requests
      if (!useModelStore.getState().isLoading) {
        fetchModels()
      }
    }, intervalMs)
    
    // Cleanup on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [fetchModels, intervalMs, enabled])
}

export default useAutoRefreshModels

