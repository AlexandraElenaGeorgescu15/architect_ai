import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'
import { AlertCircle, ZoomIn, ZoomOut, Maximize2, Download } from 'lucide-react'

interface MermaidRendererProps {
  content: string
  className?: string
}

export default function MermaidRenderer({ content, className = '' }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    // Initialize Mermaid once
    if (!isInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif',
        themeVariables: {
          primaryColor: '#3b82f6',
          primaryTextColor: '#fff',
          primaryBorderColor: '#2563eb',
          lineColor: '#64748b',
          secondaryColor: '#8b5cf6',
          tertiaryColor: '#ec4899',
        }
      })
      setIsInitialized(true)
    }
  }, [isInitialized])

  useEffect(() => {
    if (!containerRef.current || !content || !isInitialized) return

    const renderDiagram = async () => {
      try {
        setError(null)
        const container = containerRef.current
        if (!container) return

        // Clear previous content
        container.innerHTML = ''

        // Generate unique ID for this diagram
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`

        // Create a temporary div for rendering
        const tempDiv = document.createElement('div')
        tempDiv.id = id
        tempDiv.className = 'mermaid'
        tempDiv.textContent = content

        // Render the diagram
        const { svg } = await mermaid.render(id, content)
        
        // Insert the SVG
        container.innerHTML = svg

        // Apply zoom
        const svgElement = container.querySelector('svg')
        if (svgElement) {
          svgElement.style.transform = `scale(${zoom})`
          svgElement.style.transformOrigin = 'top center'
          svgElement.style.transition = 'transform 0.3s ease'
        }
      } catch (err: any) {
        console.error('Mermaid rendering error:', err)
        setError(err.message || 'Failed to render diagram')
      }
    }

    renderDiagram()
  }, [content, zoom, isInitialized])

  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.1, 2))
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.1, 0.5))
  const handleResetZoom = () => setZoom(1)

  const handleDownload = () => {
    if (!containerRef.current) return
    
    const svg = containerRef.current.querySelector('svg')
    if (!svg) return

    const svgData = new XMLSerializer().serializeToString(svg)
    const blob = new Blob([svgData], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'diagram.svg'
    link.click()
    URL.revokeObjectURL(url)
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center max-w-md p-6 bg-destructive/10 border border-destructive/30 rounded-lg">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-destructive" />
          <h3 className="text-lg font-bold text-foreground mb-2">Rendering Error</h3>
          <p className="text-sm text-muted-foreground mb-4">{error}</p>
          <details className="text-xs text-left bg-background/50 p-3 rounded border border-border">
            <summary className="cursor-pointer font-semibold mb-2">Show Diagram Code</summary>
            <pre className="whitespace-pre-wrap break-all overflow-auto max-h-40">
              {content}
            </pre>
          </details>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative h-full flex flex-col ${className}`}>
      {/* Zoom Controls */}
      <div className="absolute top-4 right-4 z-10 flex items-center gap-2 bg-card/90 backdrop-blur-sm border border-border rounded-lg shadow-lg p-2">
        <button
          onClick={handleZoomOut}
          className="p-2 hover:bg-secondary rounded transition-colors"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-sm font-mono text-muted-foreground min-w-[3rem] text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={handleZoomIn}
          className="p-2 hover:bg-secondary rounded transition-colors"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <div className="w-px h-6 bg-border mx-1"></div>
        <button
          onClick={handleResetZoom}
          className="p-2 hover:bg-secondary rounded transition-colors"
          title="Reset Zoom"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
        <button
          onClick={handleDownload}
          className="p-2 hover:bg-secondary rounded transition-colors"
          title="Download SVG"
        >
          <Download className="w-4 h-4" />
        </button>
      </div>

      {/* Diagram Container */}
      <div className="flex-1 overflow-auto custom-scrollbar p-8 flex items-center justify-center">
        <div 
          ref={containerRef}
          className="mermaid-container"
          style={{ 
            minWidth: '100%',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        />
      </div>
    </div>
  )
}

