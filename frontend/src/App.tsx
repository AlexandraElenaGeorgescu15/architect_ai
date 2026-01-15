import React, { useEffect, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { WebSocketProvider } from './contexts/WebSocketContext'
import Layout from './components/layout/Layout'
import OnboardingTour from './components/OnboardingTour'
import CelebrationEffect from './components/CelebrationEffect'
import SystemLoadingOverlay from './components/SystemLoadingOverlay'
import BackendSettings from './components/BackendSettings'
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
      
      // Generic error handling
      return (
        <div style={{ padding: '20px', fontFamily: 'sans-serif', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ maxWidth: '500px', padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
            <h1 style={{ color: '#dc2626', marginBottom: '16px' }}>Application Error</h1>
            <p style={{ marginBottom: '16px', color: '#666' }}>{this.state.error.message}</p>
            <p style={{ marginBottom: '16px', color: '#666', fontSize: '14px' }}>Check the browser console (F12) for more details.</p>
            <button
              onClick={() => window.location.reload()}
              style={{ padding: '8px 16px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Reload Page
            </button>
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
