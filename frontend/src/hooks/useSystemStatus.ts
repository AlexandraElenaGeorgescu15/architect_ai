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

  const checkStatus = useCallback(async () => {
    setIsChecking(true)
    try {
      const result = await fetchSystemHealth()
      
      // Normalize ready status - ensure it's always a boolean
      const normalizedResult = {
        ...result,
        ready: result.ready === true || result.overall_status === 'ready'
      }
      
      // Log detailed health check response
      const wasReady = status?.ready
      const shouldLog = normalizedResult.ready !== wasReady || wasReady === undefined || normalizedResult.ready === true
      if (shouldLog) {
        const phaseStatuses = normalizedResult.phases ? 
          Object.fromEntries(Object.entries(normalizedResult.phases).map(([k, v]) => [k, (v as any).status])) :
          {}
        console.log('🏥 [SYSTEM_STATUS] Health check:', {
          ready: normalizedResult.ready,
          overall_status: normalizedResult.overall_status,
          message: normalizedResult.message,
          phases_count: Object.keys(normalizedResult.phases || {}).length,
          phase_statuses: phaseStatuses,
          raw_ready: result.ready,
          raw_overall_status: result.overall_status
        })
      }
      setStatus(normalizedResult)
      setError(null)
      if (!hasSuccess) {
        setHasSuccess(true)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unable to reach backend'
      console.error('❌ [SYSTEM_STATUS] Health check failed:', message)

      // Before the first successful health check, treat errors as "backend still starting"
      // and avoid showing a scary error message in the UI. After at least one success,
      // surface errors so the user knows something regressed.
      if (hasSuccess) {
        setError(message)
      } else {
        setError(null)
      }
    } finally {
      setIsChecking(false)
    }
  }, [status?.ready, hasSuccess])

  useEffect(() => {
    void checkStatus()
    const interval = setInterval(() => {
      void checkStatus()
    }, pollInterval)

    return () => clearInterval(interval)
  }, [checkStatus, pollInterval])

  const isReady = useMemo(() => status?.ready ?? false, [status])

  return {
    status,
    isReady,
    isChecking,
    error,
    retry: checkStatus,
  }
}

