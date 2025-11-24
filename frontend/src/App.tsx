import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { WebSocketProvider } from './contexts/WebSocketContext'
import Layout from './components/layout/Layout'
import Studio from './pages/Studio'
import Intelligence from './pages/Intelligence'
import Canvas from './pages/Canvas'
import OnboardingTour from './components/OnboardingTour'
import CelebrationEffect from './components/CelebrationEffect'

// Simple error boundary
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // React Error caught - display error boundary
  }

  render() {
    if (this.state.hasError && this.state.error) {
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

  return (
    <ErrorBoundary>
      <WebSocketProvider defaultRoomId={defaultRoomId} token={token}>
        <Router 
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true
          }}
        >
          <Routes>
            <Route
              path="*"
              element={
                <Layout>
                  <Routes>
                    <Route path="/" element={<Navigate to="/studio" replace />} />
                    <Route path="/studio" element={<Studio />} />
                    <Route path="/intelligence" element={<Intelligence />} />
                    <Route path="/canvas" element={<Canvas />} />
                    <Route path="*" element={<Navigate to="/studio" replace />} />
                  </Routes>
                </Layout>
              }
            />
          </Routes>
          {/* Global onboarding tour - works on all pages */}
          <OnboardingTour />
          {/* Celebration effect for successful generations */}
          <CelebrationEffect />
        </Router>
      </WebSocketProvider>
    </ErrorBoundary>
  )
}

export default App
