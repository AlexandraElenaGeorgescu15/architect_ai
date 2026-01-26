import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchSystemHealth, SystemHealthResponse } from '../services/healthService'

interface UseSystemStatusResult {
  status: SystemHealthResponse | null
  isReady: boolean
  isChecking: boolean
  error: string | null
  retry: () => Promise<void>
}

export function useSystemStatus(pollInterval = 4000): UseSystemStatusResult {
  const [status, setStatus] = useState<SystemHealthResponse | null>(null)
  const [isChecking, setIsChecking] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSuccess, setHasSuccess] = useState<boolean>(false)
  const [consecutiveFailures, setConsecutiveFailures] = useState<number>(0)

  const checkStatus = useCallback(async () => {
    setIsChecking(true)
    try {
      const result = await fetchSystemHealth()

      // Normalize ready status
      const normalizedResult = {
        ...result,
        ready: result.ready === true || result.overall_status === 'ready'
      }

      setStatus(normalizedResult)
      setError(null)
      setConsecutiveFailures(0) // Reset failures on success

      if (!hasSuccess) {
        setHasSuccess(true)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to reach backend'
      console.warn('⚠️ [SYSTEM_STATUS] Health check failed:', message)

      const newFailures = consecutiveFailures + 1
      setConsecutiveFailures(newFailures)

      // Grace period: Only show error and lose readiness after 3 consecutive failures
      if (hasSuccess && newFailures >= 3) {
        setError(message)
        // Optionally update status to not-ready if we want to force UI change
        setStatus(prev => prev ? { ...prev, ready: false } : null)
      }
    } finally {
      setIsChecking(false)
    }
  }, [consecutiveFailures, hasSuccess])

  useEffect(() => {
    void checkStatus()
    const interval = setInterval(() => {
      void checkStatus()
    }, pollInterval)

    return () => clearInterval(interval)
  }, [checkStatus, pollInterval])

  // Ready if status says ready OR if we're in a grace period (less than 3 failures)
  const isReady = useMemo(() => {
    if (status?.ready) return true
    if (hasSuccess && consecutiveFailures > 0 && consecutiveFailures < 3) return true
    return false
  }, [status?.ready, hasSuccess, consecutiveFailures])

  return {
    status,
    isReady,
    isChecking,
    error,
    retry: checkStatus,
  }
}

