import { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

/**
 * React Error Boundary for catching and handling component errors.
 * 
 * Usage:
 *   <ErrorBoundary>
 *     <YourComponent />
 *   </ErrorBoundary>
 * 
 *   // With custom fallback:
 *   <ErrorBoundary fallback={<CustomErrorUI />}>
 *     <YourComponent />
 *   </ErrorBoundary>
 * 
 *   // With error callback:
 *   <ErrorBoundary onError={(error, info) => logToServer(error)}>
 *     <YourComponent />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to console for development
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    
    this.setState({ errorInfo })
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
    
    // Log to backend (if available)
    this.logErrorToBackend(error, errorInfo)
  }

  private async logErrorToBackend(error: Error, errorInfo: ErrorInfo) {
    try {
      await fetch('/api/feedback/error-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error_type: 'react_error_boundary',
          error_message: error.message,
          error_stack: error.stack,
          component_stack: errorInfo.componentStack,
          url: window.location.href,
          timestamp: new Date().toISOString(),
          user_agent: navigator.userAgent
        })
      })
    } catch (logError) {
      // Silently fail - we don't want to cause more errors
      console.warn('Failed to log error to backend:', logError)
    }
  }

  private handleReload = () => {
    window.location.reload()
  }

  private handleGoHome = () => {
    window.location.href = '/'
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback provided
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-4">
          <div className="max-w-md w-full bg-card border border-border rounded-2xl shadow-xl p-8 text-center">
            {/* Error Icon */}
            <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-destructive" />
            </div>
            
            {/* Title */}
            <h1 className="text-2xl font-bold text-foreground mb-2">
              Something went wrong
            </h1>
            
            {/* Description */}
            <p className="text-muted-foreground mb-6">
              We apologize for the inconvenience. An unexpected error has occurred.
            </p>
            
            {/* Error Details (collapsible) */}
            {this.state.error && (
              <details className="text-left mb-6 p-4 bg-muted/50 rounded-lg">
                <summary className="cursor-pointer text-sm font-medium text-foreground flex items-center gap-2">
                  <Bug className="w-4 h-4" />
                  Technical Details
                </summary>
                <div className="mt-3 space-y-2">
                  <p className="text-sm text-destructive font-mono break-all">
                    {this.state.error.message}
                  </p>
                  {this.state.error.stack && (
                    <pre className="text-xs text-muted-foreground overflow-auto max-h-32 p-2 bg-background rounded">
                      {this.state.error.stack.slice(0, 500)}
                    </pre>
                  )}
                </div>
              </details>
            )}
            
            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleRetry}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              
              <button
                onClick={this.handleGoHome}
                className="flex items-center justify-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-muted transition-colors font-medium"
              >
                <Home className="w-4 h-4" />
                Go Home
              </button>
            </div>
            
            {/* Reload hint */}
            <p className="mt-6 text-xs text-muted-foreground">
              If the problem persists,{' '}
              <button 
                onClick={this.handleReload}
                className="text-primary hover:underline"
              >
                reload the page
              </button>
              {' '}or contact support.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

/**
 * HOC to wrap a component with ErrorBoundary
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  fallback?: ReactNode
) {
  return function WithErrorBoundary(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    )
  }
}

export default ErrorBoundary

