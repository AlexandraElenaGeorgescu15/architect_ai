import { useState, useEffect } from 'react'
import { Key, Eye, EyeOff, Save, CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react'
import api from '../services/api'
import { useUIStore } from '../stores/uiStore'

interface ApiKeyStatus {
  configured: boolean
  env_var: boolean
  settings_key: boolean
  key_length: number
  valid?: boolean
}

interface ApiKeysStatus {
  gemini: ApiKeyStatus
  groq: ApiKeyStatus
  openai: ApiKeyStatus
  anthropic: ApiKeyStatus
}

export default function ApiKeysManager() {
  const [keys, setKeys] = useState<ApiKeysStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
  const [formKeys, setFormKeys] = useState<Record<string, string>>({
    groq: '',
    gemini: '',
    openai: '',
    anthropic: '',
  })
  const { addNotification } = useUIStore()

  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    setIsLoading(true)
    try {
      const response = await api.get('/api/models/api-keys/status')
      setKeys(response.data.api_keys || response.data)
      // Pre-fill form with existing keys (masked)
      if (response.data) {
        setFormKeys({
          groq: response.data.groq.configured ? '••••••••' : '',
          gemini: response.data.gemini.configured ? '••••••••' : '',
          openai: response.data.openai.configured ? '••••••••' : '',
          anthropic: response.data.anthropic.configured ? '••••••••' : '',
        })
      }
    } catch (error) {
      // Failed to load API keys status - show notification
      addNotification('error', 'Failed to load API keys status')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSave = async (provider: string) => {
    const key = formKeys[provider]
    if (!key || key === '••••••••') {
      addNotification('error', 'Please enter a new API key')
      return
    }

    setIsSaving(true)
    try {
      // Save to .env file via backend
      await api.post('/api/config/api-keys', {
        provider,
        api_key: key,
      })
      addNotification('success', `${provider} API key saved successfully`)
      setFormKeys((prev) => ({ ...prev, [provider]: '••••••••' }))
      await loadStatus()
    } catch (error: any) {
      // Failed to save API key - show notification
      addNotification('error', error.response?.data?.detail || 'Failed to save API key')
    } finally {
      setIsSaving(false)
    }
  }

  const toggleShowKey = (provider: string) => {
    setShowKeys((prev) => ({ ...prev, [provider]: !prev[provider] }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    )
  }

  const providers = [
    { id: 'groq', name: 'Groq (X.AI)', placeholder: 'gsk_...' },
    { id: 'gemini', name: 'Gemini (Google)', placeholder: 'AIzaSy...' },
    { id: 'openai', name: 'OpenAI', placeholder: 'sk-...' },
    { id: 'anthropic', name: 'Anthropic (Claude)', placeholder: 'sk-ant-...' },
  ]

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="glass-panel bg-primary/5 border-2 border-primary/20 rounded-xl p-4">
        <h3 className="text-lg font-bold flex items-center gap-2 mb-2 text-foreground">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Key className="w-5 h-5 text-primary" />
          </div>
          API Keys Configuration
        </h3>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Configure API keys for cloud AI providers. Keys are stored securely in your .env file.
        </p>
      </div>

      <div className="space-y-4">
        {providers.map((provider) => {
          const status = keys?.[provider.id as keyof ApiKeysStatus] as ApiKeyStatus | undefined
          const isConfigured = status?.configured || false
          const currentKey = formKeys[provider.id]
          const isMasked = currentKey === '••••••••'

          return (
            <div
              key={provider.id}
              className="glass-panel bg-card border-2 border-border rounded-xl p-5 hover:border-primary/40 hover:bg-primary/5 transition-all duration-300 animate-fade-in-up group"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center border-2 transition-all duration-300 ${
                    isConfigured 
                      ? 'bg-success/10 border-success/30 group-hover:scale-110' 
                      : 'bg-muted border-border group-hover:scale-105'
                  }`}>
                    <Key className={`w-5 h-5 transition-colors ${isConfigured ? 'text-success' : 'text-muted-foreground'}`} />
                  </div>
                  <div>
                    <h4 className="font-bold text-foreground group-hover:text-primary transition-colors">{provider.name}</h4>
                    <div className="flex items-center gap-2 mt-1">
                      {isConfigured ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-success" />
                          <span className="text-xs text-success font-semibold">Configured</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="w-4 h-4 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground font-medium">Not configured</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="relative">
                  <input
                    type={showKeys[provider.id] ? 'text' : 'password'}
                    value={currentKey}
                    onChange={(e) => setFormKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))}
                    placeholder={provider.placeholder}
                    className="w-full px-4 py-3 pr-12 glass-input border-2 border-border rounded-xl bg-background/50 text-foreground font-mono text-sm transition-all duration-300 focus:border-primary/50 focus:bg-background"
                  />
                  <button
                    type="button"
                    onClick={() => toggleShowKey(provider.id)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground hover:bg-muted/50 p-1.5 rounded-lg transition-all"
                  >
                    {showKeys[provider.id] ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleSave(provider.id)}
                    disabled={isSaving || !currentKey || isMasked}
                    className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 transition-all duration-300 shadow-md hover:shadow-glow hover:scale-105 active:scale-95 font-semibold"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" />
                        {isConfigured ? 'Update Key' : 'Save Key'}
                      </>
                    )}
                  </button>
                  {isConfigured && (
                    <div className="text-xs text-muted-foreground flex items-center gap-1.5 px-3 py-2 bg-muted/30 rounded-lg border border-border">
                      <AlertCircle className="w-3 h-3" />
                      <span className="font-medium">Key length: <span className="text-foreground font-bold">{status?.key_length || 0}</span> chars</span>
                    </div>
                  )}
                </div>

                {provider.id === 'groq' && (
                  <div className="text-xs text-muted-foreground bg-info/5 border border-info/20 p-3 rounded-xl flex items-start gap-2">
                    <span className="text-base">💡</span>
                    <div>
                      <span className="font-medium">Your Grok key:</span>
                      <code className="block mt-1 bg-background px-2 py-1 rounded font-mono text-[10px] break-all">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</code>
                    </div>
                  </div>
                )}
                {provider.id === 'gemini' && (
                  <div className="text-xs text-muted-foreground bg-info/5 border border-info/20 p-3 rounded-xl flex items-start gap-2">
                    <span className="text-base">💡</span>
                    <div>
                      <span className="font-medium">Your Gemini key:</span>
                      <code className="block mt-1 bg-background px-2 py-1 rounded font-mono text-[10px] break-all">AIzaSyAg6R0U0Noix5QRc4-mRio5ovaQz2CSSWs</code>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="glass-panel bg-warning/5 border-2 border-warning/20 rounded-xl p-4">
        <p className="text-sm text-muted-foreground leading-relaxed">
          <strong className="text-foreground font-bold">Note:</strong> API keys are stored in your <code className="bg-background px-2 py-0.5 rounded-md font-mono text-primary">.env</code> file in the backend directory.
          After saving, restart the backend server for changes to take effect.
        </p>
      </div>
    </div>
  )
}

