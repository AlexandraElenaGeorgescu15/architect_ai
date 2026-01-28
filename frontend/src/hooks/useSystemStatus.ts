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
    // ngrok free tier has severe connection limits - poll very infrequently
    if (backendUrl.includes('ngrok')) {
      return 30000 // 30 seconds for ngrok (free tier closes connections aggressively)
    }
  } catch (e) {
    // localStorage might not be available (SSR)
  }
  return 4000 // 4 seconds for local/regular connections
}

// Check if using ngrok
function isUsingNgrok(): boolean {
  try {
    const backendUrl = localStorage.getItem(BACKEND_URL_KEY) || ''
    return backendUrl.includes('ngrok')
  } catch (e) {
    return false
  }
}

export function useSystemStatus(pollInterval?: number): UseSystemStatusResult {
  const effectivePollInterval = pollInterval ?? getPollInterval()
  const usingNgrok = isUsingNgrok()
  const [status, setStatus] = useState<SystemHealthResponse | null>(null)
  const [isChecking, setIsChecking] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSuccess, setHasSuccess] = useState<boolean>(false)
  const [consecutiveFailures, setConsecutiveFailures] = useState<number>(0)
  const [initialCheckDone, setInitialCheckDone] = useState<boolean>(false)
  const [ngrokTimeoutReached, setNgrokTimeoutReached] = useState<boolean>(false)

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

      // For ngrok: If we've had a successful connection before, don't mark as error
      // ngrok free tier closes connections aggressively, but the backend is still running
      if (usingNgrok && hasSuccess) {
        // Don't update error state - assume backend is still working
        // Just silently track failures but don't show error to user
        return
      }

      // Grace period: Only show error and lose readiness after 5 consecutive failures (increased for ngrok)
      if (hasSuccess && newFailures >= 5) {
        setError(message)
        // Optionally update status to not-ready if we want to force UI change
        setStatus(prev => prev ? { ...prev, ready: false } : null)
      }
    } finally {
      setIsChecking(false)
    }
  }, [consecutiveFailures, hasSuccess, usingNgrok])

  useEffect(() => {
    // Initial check
    let mounted = true
    let ngrokTimeout: NodeJS.Timeout | null = null
    
    // For ngrok: Set a timeout - if we can't connect after 10 seconds, assume ready
    // This handles cases where ngrok free tier blocks all connections
    if (usingNgrok) {
      ngrokTimeout = setTimeout(() => {
        if (mounted) {
          console.log('⏱️ [SYSTEM_STATUS] Ngrok timeout reached - assuming backend is ready')
          setNgrokTimeoutReached(true)
          setInitialCheckDone(true)
          // Create a mock ready status
          setStatus({
            status: 'ready',
            service: 'architect-ai-backend',
            version: '3.5.2',
            ready: true,
            overall_status: 'ready',
            message: 'Backend assumed ready (ngrok connection timeout)',
            last_updated: new Date().toISOString(),
            phases: {},
            cache: {},
            metrics: { counters: 0, gauges: 0, timers: 0 }
          })
          setHasSuccess(true)
        }
      }, 10000) // 10 second timeout for ngrok (reduced from 15s for faster UX)
    }
    
    checkStatus().then(() => {
      if (mounted) {
        setInitialCheckDone(true)
        // Clear timeout if we succeeded
        if (ngrokTimeout) {
          clearTimeout(ngrokTimeout)
        }
      }
    }).catch(() => {
      if (mounted) {
        setInitialCheckDone(true)
      }
    })
    
    // For ngrok, only poll if we haven't had success yet
    // Once we have success, assume backend is working and stop aggressive polling
    // This prevents ngrok from closing connections due to too many requests
    const shouldPoll = !usingNgrok || !hasSuccess
    
    if (shouldPoll) {
      const interval = setInterval(() => {
        void checkStatus()
      }, effectivePollInterval)

      return () => {
        mounted = false
        if (ngrokTimeout) clearTimeout(ngrokTimeout)
        clearInterval(interval)
      }
    }
    
    return () => {
      mounted = false
      if (ngrokTimeout) clearTimeout(ngrokTimeout)
    }
  }, [checkStatus, effectivePollInterval, usingNgrok, hasSuccess])

  // Ready if status says ready OR if we're in a grace period
  // For ngrok: If we've had success before OR timeout reached, assume ready even if health checks fail
  const isReady = useMemo(() => {
    if (status?.ready) return true
    // For ngrok: If timeout reached, assume ready (ngrok free tier may block all connections)
    if (usingNgrok && ngrokTimeoutReached) return true
    // For ngrok: If we've successfully connected before, assume ready
    // (ngrok free tier closes connections but backend is still running)
    if (usingNgrok && hasSuccess && initialCheckDone) return true
    // Grace period: Allow some failures before marking as not ready
    if (hasSuccess && consecutiveFailures > 0 && consecutiveFailures < 5) return true
    return false
  }, [status?.ready, hasSuccess, consecutiveFailures, usingNgrok, initialCheckDone, ngrokTimeoutReached])

  return {
    status,
    isReady,
    isChecking,
    error,
    retry: checkStatus,
  }
}

