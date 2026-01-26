/**
 * Backend Settings Component
 * Allows users to configure a custom backend URL for split deployment scenarios
 * (e.g., frontend on Vercel, backend running locally with ngrok)
 */

import { useState, useEffect } from 'react'
import {
  Server,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  ExternalLink
} from 'lucide-react'
import {
  getBackendUrl,
  setBackendUrl,
  isUsingCustomBackend,
  testBackendConnection
} from '../services/api'

interface ConnectionStatus {
  connected: boolean
  version?: string
  latency?: number
  error?: string
  lastChecked?: Date
}

export default function BackendSettings() {
  const [isOpen, setIsOpen] = useState(false)
  const [url, setUrl] = useState(getBackendUrl())
  const [testUrl, setTestUrl] = useState('')
  const [status, setStatus] = useState<ConnectionStatus | null>(null)
  const [isTesting, setIsTesting] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Check connection on mount
  useEffect(() => {
    checkConnection()
  }, [])

  // Re-check when dialog opens
  useEffect(() => {
    if (isOpen) {
      checkConnection()
    }
  }, [isOpen])

  // Listen for custom event to open settings
  useEffect(() => {
    const handleOpenSettings = () => setIsOpen(true)
    window.addEventListener('architect:open-backend-settings', handleOpenSettings)
    return () => window.removeEventListener('architect:open-backend-settings', handleOpenSettings)
  }, [])

  // Auto-check connection every 30 seconds (always, not just when dialog is open)
  useEffect(() => {
    const interval = setInterval(checkConnection, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkConnection = async () => {
    setIsTesting(true)
    const result = await testBackendConnection()
    setStatus({ ...result, lastChecked: new Date() })
    setIsTesting(false)
  }

  const handleTestUrl = async () => {
    if (!testUrl.trim()) return
    setIsTesting(true)
    const result = await testBackendConnection(testUrl.trim())
    setStatus({ ...result, lastChecked: new Date() })
    setIsTesting(false)
  }

  const handleSave = async () => {
    setIsSaving(true)
    const urlToSave = testUrl.trim() || url
    setBackendUrl(urlToSave)
    setUrl(urlToSave)
    setTestUrl('')

    // Test the new connection
    const result = await testBackendConnection()
    setStatus({ ...result, lastChecked: new Date() })
    setIsSaving(false)

    // Reload the page to apply new backend URL to all components
    if (result.connected) {
      window.location.reload()
    }
  }

  const handleReset = () => {
    setBackendUrl('')
    setUrl('')
    setTestUrl('')
    checkConnection()
  }

  const isCustomBackend = isUsingCustomBackend()
  const currentUrl = getBackendUrl() || window.location.origin

  return (
    <>
      {/* Minimal connection indicator - small dot that shows status */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-3 left-3 z-[2000] w-6 h-6 rounded-full flex items-center justify-center transition-all duration-200 opacity-50 hover:opacity-100 hover:scale-110 ${status?.connected
          ? 'bg-green-500/20 border border-green-500/40 hover:bg-green-500/30'
          : 'bg-red-500/20 border border-red-500/40 hover:bg-red-500/30 animate-pulse'
          }`}
        title={status?.connected ? `Connected${isCustomBackend ? ' (Custom)' : ''}` : 'Disconnected - Click to configure'}
      >
        {status?.connected ? (
          <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]" />
        )}
      </button>

      {/* Modal - z-[2100] to be above both loading overlay and floating button */}
      {isOpen && (
        <div className="fixed inset-0 z-[2100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card border border-border rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border bg-secondary/20">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Server className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h2 className="font-bold text-lg">Backend Connection</h2>
                    <p className="text-xs text-muted-foreground">Configure your API server</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-muted rounded-lg transition-colors"
                >
                  <XCircle className="w-5 h-5 text-muted-foreground" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Connection Status */}
              <div className={`p-4 rounded-xl border ${status?.connected
                ? 'bg-green-500/5 border-green-500/20'
                : 'bg-red-500/5 border-red-500/20'
                }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isTesting ? (
                      <Loader2 className="w-5 h-5 animate-spin text-primary" />
                    ) : status?.connected ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-500" />
                    )}
                    <div>
                      <p className="font-medium">
                        {status?.connected ? 'Connected' : 'Not Connected'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {status?.connected
                          ? `v${status.version} • ${status.latency}ms latency`
                          : status?.error || 'Unable to reach backend'
                        }
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={checkConnection}
                    disabled={isTesting}
                    className="p-2 hover:bg-muted rounded-lg transition-colors"
                    title="Refresh connection"
                  >
                    <RefreshCw className={`w-4 h-4 ${isTesting ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </div>

              {/* Current Backend URL */}
              <div>
                <label className="block text-sm font-medium mb-2">Current Backend URL</label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-muted rounded-lg text-sm font-mono truncate">
                    {currentUrl || 'localhost (relative)'}
                  </code>
                  {isCustomBackend && (
                    <button
                      onClick={handleReset}
                      className="px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {/* Set Custom Backend */}
              <div>
                <label className="block text-sm font-medium mb-2">Set Custom Backend URL</label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={testUrl}
                    onChange={(e) => setTestUrl(e.target.value)}
                    placeholder="https://your-backend.ngrok.io"
                    className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                  <button
                    onClick={handleTestUrl}
                    disabled={!testUrl.trim() || isTesting}
                    className="px-4 py-2 bg-secondary hover:bg-secondary/80 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    Test
                  </button>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Use ngrok or localtunnel to expose your local backend with HTTPS
                </p>
              </div>

              {/* Instructions */}
              <div className="p-4 bg-info/5 border border-info/20 rounded-xl">
                <h4 className="font-medium text-sm mb-2 flex items-center gap-2">
                  <ExternalLink className="w-4 h-4" />
                  How to expose your local backend
                </h4>
                <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                  <li>Install ngrok: <code className="bg-muted px-1 rounded">npm i -g ngrok</code></li>
                  <li>Start your backend: <code className="bg-muted px-1 rounded">python launch.py</code></li>
                  <li>Expose it: <code className="bg-muted px-1 rounded">ngrok http 8000</code></li>
                  <li>Copy the HTTPS URL and paste above</li>
                </ol>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-border bg-secondary/10 flex justify-end gap-3">
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 text-sm hover:bg-muted rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving || (!testUrl.trim() && !isCustomBackend)}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                Save & Reconnect
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
