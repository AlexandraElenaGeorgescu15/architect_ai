/**
 * HtmlRenderer - Dedicated component for rendering HTML artifacts
 * 
 * Features:
 * - Secure iframe sandboxing
 * - Zoom controls
 * - Fullscreen mode
 * - Download functionality
 * - Error handling
 */

import { useState, useMemo, useRef } from 'react'
import { Maximize2, Minimize2, Download, ZoomIn, ZoomOut, RotateCcw, ExternalLink, X } from 'lucide-react'

interface HtmlRendererProps {
  content: string
  title?: string
  className?: string
  onError?: (error: string) => void
  showControls?: boolean
  initialHeight?: number | string
}

export default function HtmlRenderer({ 
  content, 
  title = 'HTML Artifact',
  className = '',
  onError,
  showControls = true,
  initialHeight = 400
}: HtmlRendererProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [scale, setScale] = useState(1)
  const [hasError, setHasError] = useState(false)

  // Prepare HTML content - ensure complete document structure
  const preparedContent = useMemo(() => {
    if (!content || content.trim().length === 0) {
      return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { 
      font-family: system-ui, sans-serif; 
      margin: 0; 
      padding: 2rem; 
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: #f8f9fa;
      color: #6c757d;
    }
    .empty-state {
      text-align: center;
    }
    .empty-state svg {
      width: 48px;
      height: 48px;
      margin-bottom: 1rem;
      opacity: 0.5;
    }
  </style>
</head>
<body>
  <div class="empty-state">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
    <p>No HTML content</p>
  </div>
</body>
</html>`
    }

    // Check if content is already a complete HTML document
    const trimmed = content.trim().toLowerCase()
    if (trimmed.startsWith('<!doctype') || trimmed.startsWith('<html')) {
      return content
    }

    // Wrap partial HTML in a complete document structure
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { box-sizing: border-box; }
    body { 
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      margin: 0;
      padding: 1rem;
      line-height: 1.6;
      color: #333;
    }
    img { max-width: 100%; height: auto; }
    pre { overflow-x: auto; background: #f4f4f4; padding: 1rem; border-radius: 4px; }
    code { font-family: 'Fira Code', Consolas, Monaco, monospace; }
  </style>
</head>
<body>
${content}
</body>
</html>`
  }, [content])

  // Download HTML file
  const handleDownload = () => {
    const blob = new Blob([preparedContent], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.replace(/\s+/g, '_').toLowerCase()}.html`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Open in new tab
  const handleOpenExternal = () => {
    const blob = new Blob([preparedContent], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    // Clean up URL after a delay
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  // Zoom controls
  const handleZoomIn = () => setScale(s => Math.min(2, s + 0.1))
  const handleZoomOut = () => setScale(s => Math.max(0.5, s - 0.1))
  const handleResetZoom = () => setScale(1)

  // Handle iframe load errors
  const handleIframeError = () => {
    setHasError(true)
    onError?.('Failed to render HTML content')
  }

  // Calculate container dimensions based on scale
  const scaledHeight = typeof initialHeight === 'number' 
    ? initialHeight * scale 
    : initialHeight

  return (
    <div className={`html-renderer relative ${className}`}>
      {/* Controls */}
      {showControls && (
        <div className="absolute top-2 right-2 z-10 flex items-center gap-1 bg-card/90 backdrop-blur-sm border border-border rounded-lg px-2 py-1 shadow-sm">
          {/* Zoom Controls */}
          <button
            onClick={handleZoomOut}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono min-w-[3rem] text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Reset zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          
          <div className="w-px h-4 bg-border mx-1" />
          
          {/* Action Controls */}
          <button
            onClick={() => setIsFullscreen(true)}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleOpenExternal}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Download HTML"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Iframe Container */}
      <div 
        className="overflow-auto border border-border rounded-lg bg-white"
        style={{ 
          height: scaledHeight,
          transition: 'height 0.2s ease'
        }}
      >
        {hasError ? (
          <div className="flex items-center justify-center h-full bg-destructive/5 text-destructive p-4">
            <p className="text-sm">Failed to render HTML content</p>
          </div>
        ) : (
          <iframe
            ref={iframeRef}
            srcDoc={preparedContent}
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
            className="w-full h-full border-0"
            style={{
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
              width: `${100 / scale}%`,
              height: `${100 / scale}%`
            }}
            title={title}
            onError={handleIframeError}
          />
        )}
      </div>

      {/* Fullscreen Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-[200] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <div className="relative w-full h-full max-w-[95vw] max-h-[95vh] bg-white rounded-xl overflow-hidden shadow-2xl">
            {/* Fullscreen Header */}
            <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-3 bg-gradient-to-b from-black/50 to-transparent">
              <h3 className="text-white font-medium text-sm">{title}</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownload}
                  className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors text-white"
                  title="Download HTML"
                >
                  <Download className="w-4 h-4" />
                </button>
                <button
                  onClick={handleOpenExternal}
                  className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors text-white"
                  title="Open in new tab"
                >
                  <ExternalLink className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="p-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors text-white"
                  title="Close fullscreen"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Fullscreen Iframe */}
            <iframe
              srcDoc={preparedContent}
              sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
              className="w-full h-full border-0"
              title={`${title} (Fullscreen)`}
            />
          </div>
        </div>
      )}
    </div>
  )
}

