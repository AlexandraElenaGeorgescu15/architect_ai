import React, { useEffect, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { WebSocketProvider } from './contexts/WebSocketContext'
import Layout from './components/layout/Layout'
import OnboardingTour from './components/OnboardingTour'
import CelebrationEffect from './components/CelebrationEffect'
import SystemLoadingOverlay from './components/SystemLoadingOverlay'
import BackendSettings from './components/BackendSettings'
import RobotGame from './components/RobotGame'
import { useSystemStatus } from './hooks/useSystemStatus'
import { useAppLoading } from './hooks/useAppLoading'

// Lazy load with retry - handles chunk loading failures after deployments
function lazyWithRetry<T extends React.ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  retries = 3
): React.LazyExoticComponent<T> {
  return React.lazy(() =>
    importFn().catch((error) => {
      // Check if this is a chunk loading error
      const isChunkError = error.message?.includes('dynamically imported module') ||
                          error.message?.includes('Loading chunk') ||
                          error.message?.includes('Failed to fetch')
      
      if (isChunkError && retries > 0) {
        // Clear module cache and retry
        console.warn(`Chunk loading failed, retrying... (${retries} attempts left)`)
        return new Promise<{ default: T }>((resolve) => {
          setTimeout(() => {
            resolve(lazyWithRetry(importFn, retries - 1) as any)
          }, 1000)
        })
      }
      
      // If all retries failed or not a chunk error, reload the page
      if (isChunkError) {
        console.error('Chunk loading failed after retries, reloading page...')
        window.location.reload()
      }
      
      throw error
    })
  )
}

// Lazy load pages with retry logic for deployment resilience
const Studio = lazyWithRetry(() => import('./pages/Studio'))
const Intelligence = lazyWithRetry(() => import('./pages/Intelligence'))
const Canvas = lazyWithRetry(() => import('./pages/Canvas'))

// Enhanced error boundary with chunk loading detection
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null; isChunkError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null, isChunkError: false }
  }

  static getDerivedStateFromError(error: Error) {
    // Detect chunk loading errors (happen after deployments with changed asset hashes)
    const isChunkError = error.message?.includes('dynamically imported module') ||
                        error.message?.includes('Loading chunk') ||
                        error.message?.includes('Failed to fetch')
    return { hasError: true, error, isChunkError }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('React Error:', error, errorInfo)
    
    // Auto-reload for chunk errors (new deployment detected)
    if (this.state.isChunkError) {
      console.log('Chunk loading error detected, reloading page...')
      // Small delay to let user see the message
      setTimeout(() => window.location.reload(), 1500)
    }
  }

  render() {
    if (this.state.hasError && this.state.error) {
      // Special handling for chunk loading errors
      if (this.state.isChunkError) {
        return (
          <div style={{ padding: '20px', fontFamily: 'sans-serif', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
            <div style={{ maxWidth: '500px', padding: '32px', background: 'white', border: '1px solid #e2e8f0', borderRadius: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)', textAlign: 'center' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔄</div>
              <h1 style={{ color: '#0f172a', marginBottom: '12px', fontSize: '20px' }}>New Version Available!</h1>
              <p style={{ marginBottom: '20px', color: '#64748b', fontSize: '14px' }}>
                A new version of the app has been deployed. Refreshing automatically...
              </p>
              <button
                onClick={() => window.location.reload()}
                style={{ padding: '10px 24px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '500' }}
              >
                Refresh Now
              </button>
            </div>
          </div>
        )
      }
      
      // Generic error handling - show RobotGame like the loading overlay
      return (
        <div className="fixed inset-0 z-[1000] flex flex-col items-center justify-center bg-background/95 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-4xl rounded-3xl border border-border bg-card/95 p-8 shadow-2xl shadow-black/10 my-8">
            {/* Header Section with Game */}
            <div className="mb-6">
              <div className="flex items-start gap-6 mb-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground font-semibold">
                    APPLICATION ERROR
                  </p>
                  <h1 className="text-2xl font-bold text-foreground mt-1" style={{ color: '#dc2626' }}>
                    Something went wrong
                  </h1>
                  <p className="text-sm text-muted-foreground mt-1">
                    {this.state.error.message || 'An unexpected error occurred'}
                  </p>
                </div>
              </div>
              
              {/* Interactive Robot Game - Full Width */}
              <div className="w-full flex justify-center">
                <div className="w-full max-w-md">
                  <RobotGame className="w-full" />
                  <p className="text-xs text-muted-foreground mt-2 text-center">
                    Press SPACE to play while we fix this
                  </p>
                </div>
              </div>
            </div>

            {/* Error Details */}
            <div className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-red-500/20 rounded-lg flex-shrink-0">
                  <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm text-red-700 dark:text-red-400">Error Details</p>
                  <p className="text-xs text-red-600/80 dark:text-red-400/70 mt-1">
                    Check the browser console (F12) for more details. This error has been logged.
                  </p>
                  {this.state.error.stack && (
                    <details className="mt-2">
                      <summary className="text-xs text-red-600/60 dark:text-red-400/60 cursor-pointer hover:text-red-600 dark:hover:text-red-400">
                        Show stack trace
                      </summary>
                      <pre className="mt-2 text-xs text-red-600/80 dark:text-red-400/70 overflow-auto max-h-32 p-2 bg-red-500/5 rounded">
                        {this.state.error.stack}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-between pt-6 border-t border-border">
              <div className="text-xs text-muted-foreground">
                <span>An error occurred while rendering the application. Try reloading the page.</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => window.location.reload()}
                  className="rounded-full border border-border bg-card px-4 py-2 text-xs font-semibold uppercase tracking-wider text-foreground hover:bg-muted transition-colors shadow-sm"
                >
                  Reload Page
                </button>
                <button
                  onClick={() => {
                    // Clear localStorage and reload
                    localStorage.clear()
                    window.location.reload()
                  }}
                  className="rounded-full border border-border bg-muted px-4 py-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:bg-muted/80 transition-colors shadow-sm"
                >
                  Clear & Reload
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  // Get auth token from localStorage for WebSocket connection
  const token = localStorage.getItem('access_token') || undefined
  // Use a default room ID (could be user-specific in production)
  const defaultRoomId = 'main'
  // Remember last visited path so refresh on "/" returns user to their page
  const lastVisitedPath = localStorage.getItem('last_path') || '/studio'
  const { status: systemStatus, isReady: backendReady, isChecking, error: systemError, retry } = useSystemStatus()
  const { isFullyLoaded, loadingProgress, loadingMessage } = useAppLoading()

  return (
    <ErrorBoundary>
      <WebSocketProvider defaultRoomId={defaultRoomId} token={token}>
        {/* Only show main UI when everything is fully loaded */}
        {isFullyLoaded ? (
          <Router 
            future={{
              v7_startTransition: true,
              v7_relativeSplatPath: true
            }}
          >
            <PersistLastPath />
            <Routes>
              <Route
                path="*"
                element={
                  <Layout>
                    <Suspense fallback={
                      <div className="flex h-full items-center justify-center">
                        <div className="text-gray-500">Loading page...</div>
                      </div>
                    }>
                      <Routes>
                        <Route path="/" element={<Navigate to="/studio" replace />} />
                        <Route path="/last" element={<Navigate to={lastVisitedPath} replace />} />
                        <Route path="/studio" element={<Studio />} />
                        <Route path="/intelligence" element={<Intelligence />} />
                        <Route path="/canvas" element={<Canvas />} />
                        <Route path="*" element={<Navigate to="/studio" replace />} />
                      </Routes>
                    </Suspense>
                  </Layout>
                }
              />
            </Routes>
            {/* Global onboarding tour - works on all pages */}
            <OnboardingTour />
            {/* Celebration effect for successful generations */}
            <CelebrationEffect />
          </Router>
        ) : null}
        {/* Backend connection settings - ALWAYS visible so user can configure before connecting */}
        <BackendSettings />
        <SystemLoadingOverlay 
          status={{
            ...systemStatus,
            message: loadingMessage || systemStatus?.message || 'Loading...',
            ready: isFullyLoaded,
            overall_status: isFullyLoaded ? 'ready' : 'loading',
          } as any} 
          error={systemError} 
          isChecking={!isFullyLoaded || isChecking} 
          onRetry={retry}
          loadingProgress={loadingProgress}
          loadingMessage={loadingMessage}
        />
      </WebSocketProvider>
    </ErrorBoundary>
  )
}

export default App

function PersistLastPath() {
  const location = useLocation()
  useEffect(() => {
    localStorage.setItem('last_path', location.pathname + location.search + location.hash)
  }, [location])
  return null
}
