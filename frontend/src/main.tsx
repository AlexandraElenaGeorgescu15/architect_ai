import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Initialize light mode as default (dark mode only if explicitly set)
const isDarkMode = localStorage.getItem('darkMode') === 'true'
if (isDarkMode) {
  document.documentElement.classList.add('dark')
} else {
  document.documentElement.classList.remove('dark')
  // Ensure light mode is default
  if (!localStorage.getItem('darkMode')) {
    localStorage.setItem('darkMode', 'false')
  }
  // Ensure light mode is default
  if (!localStorage.getItem('darkMode')) {
    localStorage.setItem('darkMode', 'false')
  }
}

// Error boundary for development
const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element not found')
}

try {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
} catch (error) {
  // Failed to render React app - show fallback UI
  rootElement.innerHTML = `
    <div style="padding: 20px; font-family: sans-serif;">
      <h1>Error Loading Application</h1>
      <p>${error instanceof Error ? error.message : 'Unknown error'}</p>
      <p>Check the browser console for details.</p>
    </div>
  `
}


