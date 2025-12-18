import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { ApiResponse } from '../types'

// Use empty string to make requests relative to the current origin
// This allows Vite's proxy to intercept /api/* requests in development
// In production, set VITE_API_URL to the actual backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

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

