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
  pending: 'text-slate-500 dark:text-slate-400',
  running: 'text-amber-600 dark:text-amber-400',
  complete: 'text-emerald-600 dark:text-emerald-400',
  skipped: 'text-slate-400 dark:text-slate-500',
  error: 'text-red-600 dark:text-red-400',
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
  // 1. Backend is initializing (status is null)
  // 2. There are errors (UNLESS skip flag is set)
  // 3. Backend is not ready AND (not skipped OR actively checking)
  // 4. Loading progress is less than 100%
  // 
  // Show overlay if:
  // 1. Backend is initializing (status is null)
  // 2. There are errors (Show unless user explicitly actively bypassed - but we want them to fix it)
  // 3. Backend is not ready AND (not skipped OR actively checking)
  // 4. Loading progress is less than 100%
  const showOverlay = hasError || // Always show on errors so they see the error message
    isInitializing ||
    (!isReady && (!skipFlag || isChecking === true)) ||
    (loadingProgress !== undefined && loadingProgress < 100)

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
    <div className="fixed inset-0 z-[1000] flex flex-col items-center justify-center bg-background/95 backdrop-blur-sm overflow-y-auto">
      <div className="w-full max-w-4xl rounded-3xl border border-border bg-card/95 p-8 shadow-2xl shadow-black/10 my-8">
        {/* Header Section with Game */}
        <div className="mb-6">
          <div className="flex items-start gap-6 mb-4">
            <div className="flex-1 min-w-0">
              <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground font-semibold">
                {status?.overall_status?.toUpperCase() ?? 'INITIALIZING'}
              </p>
              <p className="text-2xl font-bold text-foreground mt-1">
                {loadingMessage || status?.message || 'Preparing backend services...'}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {status?.service ?? 'Architect.AI Backend'}
              </p>
              {loadingProgress !== undefined && (
                <div className="mt-4">
                  <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-primary h-full transition-all duration-300 ease-out"
                      style={{ width: `${loadingProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-2 text-center">
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
              <p className="text-xs text-muted-foreground mt-2 text-center">
                Press SPACE to play while waiting
              </p>
            </div>
          </div>
        </div>

        {/* Phases Grid - Scrollable with inactive items first */}
        <div className="mt-8">
          <div className="max-h-[300px] overflow-y-auto custom-scrollbar pr-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {phases
                .sort(([_, a], [__, b]) => {
                  // Sort: pending/running first, then complete/skipped, then errors
                  const statusOrder: Record<string, number> = {
                    pending: 0,
                    running: 1,
                    error: 2,
                    complete: 3,
                    skipped: 4,
                  }
                  return (statusOrder[a.status] ?? 99) - (statusOrder[b.status] ?? 99)
                })
                .map(([key, phase]) => (
                  <div
                    key={key}
                    className="flex items-start justify-between rounded-xl border border-border bg-muted/30 px-4 py-3 transition-all hover:bg-muted/50"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-foreground truncate">{phase.title ?? formatPhaseTitle(key)}</p>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{phase.message ?? 'Pending...'}</p>
                    </div>
                    <span className={`text-xs font-semibold uppercase px-2 py-1 rounded-full flex-shrink-0 ml-2 ${getStatusBadgeClass(phase.status)}`}>
                      {statusLabel[phase.status] ?? phase.status}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>

        {/* Connection hint when there's an error */}
        {error && (
          <div className="mt-6 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-amber-500/20 rounded-lg flex-shrink-0">
                <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm text-amber-700 dark:text-amber-400">Need to connect to a custom backend?</p>
                <p className="text-xs text-amber-600/80 dark:text-amber-400/70 mt-1">
                  Click the <strong>WiFi icon</strong> in the <strong>bottom-left corner</strong> to configure your ngrok URL or local backend address.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 flex items-center justify-between pt-6 border-t border-border">
          <div className="text-xs text-muted-foreground">
            {error ? (
              <span className="text-destructive font-medium">
                Unable to reach backend. Click the <span className="font-bold border border-destructive/20 rounded px-1">WiFi Icon</span> at bottom-left to configure.
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
              className="rounded-full border border-border bg-card px-4 py-2 text-xs font-semibold uppercase tracking-wider text-foreground hover:bg-muted transition-colors shadow-sm"
            >
              Retry Now
            </button>
            <button
              onClick={() => {
                // Force hide overlay by setting a flag in localStorage
                localStorage.setItem('skip_loading_overlay', 'true')
                window.location.reload()
              }}
              className="rounded-full border border-border bg-muted px-4 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:bg-muted/80 transition-colors shadow-sm"
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
  switch (status) {
    case 'complete':
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400'
    case 'running':
      return 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400'
    case 'error':
      return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400'
    case 'skipped':
      return 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
    default:
      return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
  }
}

