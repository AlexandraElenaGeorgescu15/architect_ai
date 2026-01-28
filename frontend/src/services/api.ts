import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { ApiResponse } from '../types'

// ============== CONFIGURABLE BACKEND URL ==============
// Allows the frontend to connect to any backend (local or remote)
// Stored in localStorage so users can configure their own backend

const BACKEND_URL_KEY = 'architect_ai_backend_url'
const DEFAULT_BACKEND_URL = '' // Empty = relative to current origin (for local dev with Vite proxy)

/**
 * Get the configured backend URL
 * Falls back to environment variable or empty string (relative URLs)
 */
export function getBackendUrl(): string {
  // Check localStorage first (user-configured)
  const stored = localStorage.getItem(BACKEND_URL_KEY)

  if (stored !== null) {
    return stored
  }
  // Fall back to env variable or default
  return import.meta.env.VITE_API_URL || DEFAULT_BACKEND_URL
}

/**
 * Set a custom backend URL
 * Pass empty string to reset to default
 */
export function setBackendUrl(url: string): void {
  if (url === '' || url === DEFAULT_BACKEND_URL) {
    localStorage.removeItem(BACKEND_URL_KEY)
  } else {
    // Normalize: remove trailing slash
    const normalized = url.replace(/\/+$/, '')
    localStorage.setItem(BACKEND_URL_KEY, normalized)
  }
  // Update the axios instance baseURL
  api.defaults.baseURL = getBackendUrl()
}

/**
 * Check if using a custom (non-default) backend URL
 */
export function isUsingCustomBackend(): boolean {
  return localStorage.getItem(BACKEND_URL_KEY) !== null
}

/**
 * Test connection to the backend
 * Returns { connected: boolean, version?: string, error?: string }
 */
export async function testBackendConnection(url?: string): Promise<{
  connected: boolean
  version?: string
  latency?: number
  error?: string
}> {
  const testUrl = url ?? getBackendUrl()
  const start = Date.now()

  try {
    // Use longer timeout for ngrok (free tier can be slow)
    const isNgrok = testUrl.includes('ngrok')
    const timeout = isNgrok ? 15000 : 5000 // 15s for ngrok, 5s for local
    
    const response = await axios.get(`${testUrl}/api/health`, {
      timeout,
      headers: {
        // Required for ngrok free tier - bypasses the browser warning page
        'ngrok-skip-browser-warning': 'true',
      },
    })
    const latency = Date.now() - start

    return {
      connected: true,
      version: response.data?.version || 'unknown',
      latency,
    }
  } catch (error: any) {
    return {
      connected: false,
      error: error.message || 'Connection failed',
    }
  }
}

// Get initial backend URL
const API_BASE_URL = getBackendUrl()

// Create axios instance
// Many AI operations (diagram repair, HTML modifier, bulk generation) can legitimately
// take longer than 30s, especially when models are cold or context building is involved.
// Bump the global timeout to 60s so users don't see "timeout of 30000ms exceeded" for
// otherwise-successful long-running requests.
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // Required for ngrok free tier - bypasses the browser warning page
    'ngrok-skip-browser-warning': 'true',
  },
  timeout: 60000, // 60 seconds
})

// Request interceptor - Add auth token and dynamically update baseURL
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Dynamically update baseURL on each request to handle backend URL changes
    const currentBackendUrl = getBackendUrl()
    
    // Check if we're in production (not localhost) and backend URL is not set
    const isProduction = typeof window !== 'undefined' && 
      window.location.hostname !== 'localhost' && 
      window.location.hostname !== '127.0.0.1' &&
      !window.location.hostname.startsWith('192.168.') &&
      !window.location.hostname.startsWith('10.')
    
    if (isProduction && !currentBackendUrl && config.url?.startsWith('/api')) {
      // In production without backend URL, reject early with helpful message
      const error = new AxiosError(
        'Backend URL not configured. Please click the WiFi icon (bottom-left) and enter your ngrok backend URL.',
        'ERR_BACKEND_NOT_CONFIGURED',
        config,
        undefined,
        undefined
      )
      return Promise.reject(error)
    }
    
    if (currentBackendUrl !== config.baseURL) {
      config.baseURL = currentBackendUrl
    }
    
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Ensure ngrok header is always present
    if (config.headers) {
      config.headers['ngrok-skip-browser-warning'] = 'true'
    }
    
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response) => {
    // Check for HTML response from API endpoints (indicates misconfigured backend URL)
    const contentType = response.headers['content-type']
    if (
      contentType &&
      (contentType.includes('text/html') || contentType.includes('application/xhtml+xml')) &&
      response.config.url?.startsWith('/api') &&
      !response.config.url?.includes('/download')
    ) {
      // Check if backend URL is configured
      const backendUrl = getBackendUrl()
      const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
      
      let errorMessage = 'Invalid API response: Received HTML instead of JSON.'
      if (isProduction && !backendUrl) {
        errorMessage = 'Backend URL not configured. Please click the WiFi icon (bottom-left) and enter your ngrok backend URL.'
      } else if (!backendUrl) {
        errorMessage = 'Backend URL not configured. Please set VITE_API_URL or configure backend URL in settings.'
      } else {
        errorMessage = `Backend URL may be incorrect. Current: ${backendUrl || '(not set)'}. Please check your backend URL configuration.`
      }
      
      const error = new AxiosError(
        errorMessage,
        'ERR_INVALID_RESPONSE_TYPE',
        response.config,
        response.request,
        response
      )
      return Promise.reject(error)
    }
    return response
  },
  async (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status

      // Handle 401 Unauthorized - redirect to login
      if (status === 401) {
        localStorage.removeItem('access_token')
        // Redirect to login page if not already there
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
      }

      // Handle 403 Forbidden
      if (status === 403) {
        // Access forbidden - handle in UI
      }

      // Handle 429 Too Many Requests
      if (status === 429) {
        // Rate limit exceeded - handle in UI
      }

      // Handle 500+ Server Errors
      if (status >= 500) {
        // Server error - handle in UI
      }
    } else if (error.request) {
      // Network error - handle connection resets gracefully
      if (error.code === 'ERR_CONNECTION_CLOSED' || error.code === 'ERR_CONNECTION_RESET') {
        // Check if this is an ngrok URL
        const backendUrl = getBackendUrl()
        const isNgrok = backendUrl.includes('ngrok')
        
        if (isNgrok) {
          // ngrok free tier requires visiting the URL in browser first
          const retryError = new AxiosError(
            'Ngrok connection failed. Please visit the ngrok URL in your browser first to accept the warning page, then try again.',
          error.code,
          error.config,
          error.request,
          error.response
          )
          retryError.message = 'Ngrok Browser Warning: Please visit your ngrok URL in a browser first to accept the warning, then refresh this page.'
          return Promise.reject(retryError)
        } else {
          // Regular connection error
          const retryError = new AxiosError(
            'Connection closed by server. Please check your backend is running and try again.',
            error.code,
            error.config,
            error.request,
            error.response
          )
          return Promise.reject(retryError)
        }
      }
    } else {
      // Request setup error - handle in UI
    }

    return Promise.reject(error)
  }
)

export default api

// Helper function to extract data from API response
export function extractData<T>(response: { data: ApiResponse<T> | T }): T {
  // Check if response has nested data structure
  const data = response.data
  if (data && typeof data === 'object' && 'data' in data) {
    return (data as ApiResponse<T>).data
  }
  return data as T
}

