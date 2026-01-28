import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchSystemHealth, SystemHealthResponse } from '../services/healthService'

const BACKEND_URL_KEY = 'architect_ai_backend_url'

interface UseSystemStatusResult {
  status: SystemHealthResponse | null
  isReady: boolean
  isChecking: boolean
  error: string | null
  retry: () => Promise<void>
}

// Detect if using ngrok and use longer polling interval to avoid connection limits
function getPollInterval(): number {
  try {
    const backendUrl = localStorage.getItem(BACKEND_URL_KEY) || ''
    // ngrok free tier has connection limits - poll less frequently
    if (backendUrl.includes('ngrok')) {
      return 10000 // 10 seconds for ngrok
    }
  } catch (e) {
    // localStorage might not be available (SSR)
  }
  return 4000 // 4 seconds for local/regular connections
}

export function useSystemStatus(pollInterval?: number): UseSystemStatusResult {
  const effectivePollInterval = pollInterval ?? getPollInterval()
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
      
      // Don't log connection resets as errors - they're expected with ngrok free tier
      const isConnectionReset = err instanceof Error && (
        err.message.includes('ERR_CONNECTION_CLOSED') ||
        err.message.includes('ERR_CONNECTION_RESET') ||
        err.message.includes('Network Error')
      )
      
      if (!isConnectionReset) {
        console.warn('⚠️ [SYSTEM_STATUS] Health check failed:', message)
      }

      const newFailures = consecutiveFailures + 1
      setConsecutiveFailures(newFailures)

      // Grace period: Only show error and lose readiness after 5 consecutive failures (increased for ngrok)
      if (hasSuccess && newFailures >= 5) {
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
    }, effectivePollInterval)

    return () => clearInterval(interval)
  }, [checkStatus, effectivePollInterval])

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

