import { SystemHealthResponse, SystemPhaseStatus } from '../services/healthService'
import RobotGame from './RobotGame'

interface SystemLoadingOverlayProps {
  status: SystemHealthResponse | null
  error: string | null
  isChecking: boolean
  onRetry: () => Promise<void>
  loadingProgress?: number
  loadingMessage?: string
}

const statusLabel: Record<string, string> = {
  pending: 'Queued',
  running: 'In progress',
  complete: 'Ready',
  skipped: 'Skipped',
  error: 'Failed',
}

const statusColor: Record<string, string> = {
  pending: 'text-slate-500',
  running: 'text-amber-600',
  complete: 'text-emerald-600',
  skipped: 'text-slate-400',
  error: 'text-red-600',
}

const defaultPhases: Array<[string, SystemPhaseStatus]> = [
  [
    'database',
    {
      name: 'database',
      title: 'Database',
      status: 'pending',
      message: 'Initializing database...',
    },
  ],
  [
    'model_registry',
    {
      name: 'model_registry',
      title: 'Model Registry',
      status: 'pending',
      message: 'Loading models...',
    },
  ],
]

export default function SystemLoadingOverlay({ status, error, isChecking, onRetry, loadingProgress, loadingMessage }: SystemLoadingOverlayProps) {
  const phases = Object.entries(status?.phases ?? Object.fromEntries(defaultPhases))

  // Check if user manually skipped the overlay
  const skipFlag = localStorage.getItem('skip_loading_overlay') === 'true'
  
  // Check if backend is ready - multiple fallback checks
  const allPhasesComplete = phases.length > 0 && phases.every(([_, phase]) => 
    phase.status === 'complete' || phase.status === 'skipped'
  )
  
  // If status is null, we're still initializing - show overlay
  const isInitializing = status === null
  
  // Check for errors (health check failures)
  const hasError = error !== null && error !== undefined
  
  // Backend is ready if: status indicates ready AND no errors AND all phases complete
  // Don't use skipFlag to determine if backend is ready - that's just a UI preference
  const isReady = (status !== null && status.ready === true && !hasError) || 
    (status !== null && status.overall_status === 'ready' && !hasError) ||
    (status !== null && status.status === 'ready' && !hasError) ||
    (status !== null && allPhasesComplete && !hasError)
  
  // Show overlay if:
  // 1. There are errors (always show on errors, even if skip flag is set)
  // 2. Backend is initializing (status is null)
  // 3. Backend is not ready AND (not skipped OR actively checking)
  // 4. Health checks are in progress and backend is not ready
  // 5. Loading progress is less than 100%
  // 
  // Exception: If skip flag is set AND backend is actually ready AND no errors, hide overlay
  const showOverlay = hasError || // Always show on errors (even if skip flag is set)
    isInitializing || // Always show when initializing
    (!isReady && (!skipFlag || isChecking === true)) || // Show when not ready (respect skip flag only if actually ready)
    (loadingProgress !== undefined && loadingProgress < 100) // Show when loading
  
  // Debug logging
  console.log('🎨 [LOADING_OVERLAY] Show decision:', {
    skipFlag,
    isInitializing,
    isReady,
    isChecking,
    loadingProgress,
    showOverlay,
    hasError,
    error,
    status_ready: status?.ready,
    overall_status: status?.overall_status,
    loadingMessage
  })
  
  // Log detailed status for debugging
  if (status) {
    const phaseStatuses = Object.fromEntries(
      phases.map(([key, phase]) => [key, phase.status])
    )
    console.log('🎨 [LOADING_OVERLAY] Detailed Status:', {
      ready: status.ready,
      isReady,
      overall_status: status.overall_status,
      message: status.message,
      phases_count: phases.length,
      phase_statuses: phaseStatuses,
      all_phases_complete: phases.every(([_, phase]) => phase.status === 'complete' || phase.status === 'skipped'),
      has_phases_from_backend: !!status.phases,
      phases_keys: status.phases ? Object.keys(status.phases) : []
    })
  }
  
  if (!showOverlay) {
    console.log('✅ [LOADING_OVERLAY] Backend ready, hiding overlay', {
      skipFlag,
      isInitializing,
      isReady,
      isChecking,
      loadingProgress,
      loadingMessage
    })
    return null
  }
  
  console.log('🎨 [LOADING_OVERLAY] Showing overlay', {
    skipFlag,
    isInitializing,
    isReady,
    isChecking,
    loadingProgress,
    loadingMessage
  })

  return (
    <div className="fixed inset-0 z-[1000] flex flex-col items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 px-4 backdrop-blur-sm overflow-y-auto">
      <div className="w-full max-w-4xl rounded-3xl border border-slate-200 bg-white/80 p-8 shadow-2xl shadow-slate-900/10 my-8">
        {/* Header Section with Game */}
        <div className="mb-6">
          <div className="flex items-start gap-6 mb-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm uppercase tracking-[0.3em] text-slate-500 font-semibold">
                {status?.overall_status?.toUpperCase() ?? 'INITIALIZING'}
              </p>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {loadingMessage || status?.message || 'Preparing backend services...'}
              </p>
              <p className="text-sm text-slate-600 mt-1">
                {status?.service ?? 'Architect.AI Backend'}
              </p>
              {loadingProgress !== undefined && (
                <div className="mt-4">
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-primary h-full transition-all duration-300 ease-out"
                      style={{ width: `${loadingProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-2 text-center">
                    {Math.round(loadingProgress)}% complete
                  </p>
                </div>
              )}
            </div>
          </div>
          
          {/* Interactive Robot Game - Full Width */}
          <div className="w-full flex justify-center">
            <div className="w-full max-w-md">
              <RobotGame className="w-full" />
              <p className="text-xs text-slate-500 mt-2 text-center">
                Press SPACE to play while waiting
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 space-y-3">
          {phases.map(([key, phase]) => (
            <div
              key={key}
              className="flex items-start justify-between rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-3 transition-all hover:bg-slate-100/50"
            >
              <div className="flex-1">
                <p className="text-sm font-semibold text-slate-900">{phase.title ?? formatPhaseTitle(key)}</p>
                <p className="text-xs text-slate-600 mt-0.5">{phase.message ?? 'Pending...'}</p>
              </div>
              <span className={`text-xs font-semibold uppercase px-2 py-1 rounded-full ${getStatusBadgeClass(phase.status)}`}>
                {statusLabel[phase.status] ?? phase.status}
              </span>
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-center justify-between pt-6 border-t border-slate-200">
          <div className="text-xs text-slate-600">
            {error ? (
              <span className="text-red-600 font-medium">
                Unable to reach backend: {error}. Retrying {isChecking ? 'now…' : 'shortly'}.
              </span>
            ) : (
              <span>Backend is warming up. This can take around a minute.</span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                void onRetry()
              }}
              className="rounded-full border border-slate-300 bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wider text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-colors shadow-sm"
            >
              Retry Now
            </button>
            <button
              onClick={() => {
                // Force hide overlay by setting a flag in localStorage
                localStorage.setItem('skip_loading_overlay', 'true')
                window.location.reload()
              }}
              className="rounded-full border border-slate-400 bg-slate-100 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-slate-600 hover:bg-slate-200 transition-colors shadow-sm"
            >
              Skip
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatPhaseTitle(phaseKey: string): string {
  return phaseKey
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function getStatusBadgeClass(status: string): string {
  const baseClasses = 'text-xs font-semibold uppercase px-2 py-1 rounded-full'
  switch (status) {
    case 'complete':
      return `${baseClasses} bg-emerald-100 text-emerald-700`
    case 'running':
      return `${baseClasses} bg-amber-100 text-amber-700`
    case 'error':
      return `${baseClasses} bg-red-100 text-red-700`
    case 'skipped':
      return `${baseClasses} bg-slate-100 text-slate-500`
    default:
      return `${baseClasses} bg-slate-100 text-slate-600`
  }
}

