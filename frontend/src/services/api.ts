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
    const response = await axios.get(`${testUrl}/api/health`, {
      timeout: 5000, // 5 second timeout for health check
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
  },
  timeout: 60000, // 60 seconds
})

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
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
      // Network error - handle in UI
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
  if ('data' in response.data && typeof response.data === 'object' && 'data' in response.data) {
    return (response.data as ApiResponse<T>).data
  }
  return response.data as T
}

