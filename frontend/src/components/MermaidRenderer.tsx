import { useEffect, useRef, useState, useCallback } from 'react'
import mermaid from 'mermaid'
import { ZoomIn, ZoomOut, Maximize2, Download, Wand2, AlertTriangle, Loader2, Code, Eye, Move } from 'lucide-react'
import api from '../services/api'
import { useDiagramStore } from '../stores/diagramStore'

interface MermaidRendererProps {
  content: string
  className?: string
  onContentUpdate?: (newContent: string) => void
  artifactType?: string
}

// Pan/drag state for diagram viewer
interface PanState {
  x: number
  y: number
  isDragging: boolean
  startX: number
  startY: number
}

export default function MermaidRenderer({ content, className = '', onContentUpdate, artifactType = 'mermaid_erd' }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const diagramWrapperRef = useRef<HTMLDivElement>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  const [showCode, setShowCode] = useState(false)
  const containerRefSnapshot = useRef<HTMLDivElement | null>(null)
  
  // Pan/drag state for moving the diagram with mouse
  const [pan, setPan] = useState<PanState>({ x: 0, y: 0, isDragging: false, startX: 0, startY: 0 })
  
  // Use Zustand store for error state - this fixes the stale error bug
  const {
    error,
    setError,
    validation,
    setValidation,
    lastErrorContent,
    setLastErrorContent,
    isRepairing,
    setIsRepairing,
    zoom,
    zoomIn,
    zoomOut,
    resetZoom,
    resetState,
  } = useDiagramStore()

  // Store the actual Mermaid error for AI repair context
  const [mermaidErrorDetail, setMermaidErrorDetail] = useState<string | null>(null)
  
  // Pan/drag handlers for moving the diagram with mouse
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return // Only left click
    e.preventDefault()
    setPan(prev => ({
      ...prev,
      isDragging: true,
      startX: e.clientX - prev.x,
      startY: e.clientY - prev.y
    }))
  }, [])
  
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!pan.isDragging) return
    e.preventDefault()
    setPan(prev => ({
      ...prev,
      x: e.clientX - prev.startX,
      y: e.clientY - prev.startY
    }))
  }, [pan.isDragging])
  
  const handleMouseUp = useCallback(() => {
    setPan(prev => ({ ...prev, isDragging: false }))
  }, [])
  
  const handleMouseLeave = useCallback(() => {
    setPan(prev => ({ ...prev, isDragging: false }))
  }, [])
  
  const resetPan = useCallback(() => {
    setPan({ x: 0, y: 0, isDragging: false, startX: 0, startY: 0 })
  }, [])
  
  // Handle scroll wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    // Prevent page scroll
    e.preventDefault()
    
    if (e.deltaY < 0) {
      // Scroll up = zoom in
      zoomIn()
    } else {
      // Scroll down = zoom out
      zoomOut()
    }
  }, [zoomIn, zoomOut])

  const formatMermaidError = (rawError?: string): string => {
    // Store raw error for AI repair, but show friendly message to user
    if (rawError) {
      setMermaidErrorDetail(rawError)
    }
    return 'Mermaid syntax error. Please fix the diagram or click AI Repair.'
  }

  const clearMermaidErrorArtifacts = () => {
    try {
      // Remove error elements
      document.querySelectorAll('.error, .error-text, .error-icon, .messageText').forEach((el) => {
        el.remove()
      })
      // Remove error SVGs (Mermaid creates SVGs with error-icon and error-text classes)
      document.querySelectorAll('svg[role="graphics-document document"][aria-roledescription="error"]').forEach((el) => {
        el.remove()
      })
      // Remove any SVG with error classes inside
      document.querySelectorAll('svg .error-icon, svg .error-text').forEach((el) => {
        const svg = el.closest('svg')
        if (svg) svg.remove()
      })
      // Remove any div containing error SVGs
      document.querySelectorAll('div[id^="dmermaid-"]').forEach((div) => {
        const svg = div.querySelector('svg[aria-roledescription="error"]')
        if (svg) {
          div.remove()
        }
      })
    } catch {
      // ignore
    }
  }

  // Validate Mermaid content before rendering
  const validateMermaidContent = useCallback((diagramContent: string): { isValid: boolean; errors: string[]; warnings: string[] } => {
    const errors: string[] = []
    const warnings: string[] = []
    
    if (!diagramContent || diagramContent.trim().length < 5) {
      errors.push('Diagram content is too short or empty')
      return { isValid: false, errors, warnings }
    }
    
    // Check for diagram type declaration
    const diagramTypes = [
      'erDiagram', 'flowchart', 'graph', 'sequenceDiagram',
      'classDiagram', 'stateDiagram', 'gantt', 'pie', 'journey',
      'gitgraph', 'mindmap', 'timeline'
    ]
    const hasDiagramType = diagramTypes.some(dt => diagramContent.includes(dt))
    if (!hasDiagramType) {
      errors.push('Missing Mermaid diagram type declaration (erDiagram, flowchart, etc.)')
    }
    
    // Check for balanced brackets
    if (diagramContent.split('{').length !== diagramContent.split('}').length) {
      errors.push('Unbalanced curly braces {}')
    }
    if (diagramContent.split('[').length !== diagramContent.split(']').length) {
      errors.push('Unbalanced square brackets []')
    }
    if (diagramContent.split('(').length !== diagramContent.split(')').length) {
      warnings.push('Possibly unbalanced parentheses ()')
    }
    
    // Check for common syntax issues
    if (diagramContent.includes('class ') && diagramContent.includes('erDiagram')) {
      warnings.push('ERD diagram contains class diagram syntax - may need conversion')
    }
    
    // Check for empty entity definitions
    const emptyEntityPattern = /\w+\s*\{\s*\}/g
    if (emptyEntityPattern.test(diagramContent)) {
      warnings.push('Some entities have no attributes defined')
    }
    
    return {
      isValid: errors.length === 0,
      errors,
      warnings
    }
  }, [])

  // CRITICAL FIX: Reset error state when content changes
  // This must happen BEFORE the containerRef check to fix the stale error bug
  useEffect(() => {
    // When content changes, clear previous error state immediately
    // This ensures a fresh render attempt for the new diagram
    setError(null)
    setValidation(null)
    setLastErrorContent(null)
    setMermaidErrorDetail(null)
  }, [content, setError, setValidation, setLastErrorContent])
  
  // Repair function - AGGRESSIVE: keeps trying until diagram renders (max 3 attempts)
  const handleAIRepair = useCallback(async () => {
    if (isRepairing) return
    
    // If content is empty, we can't repair - show error
    if (!content || content.trim().length === 0) {
      setError('Cannot repair empty diagram. Please generate a diagram first.')
      return
    }
    
    setIsRepairing(true)
    const originalContent = content // Save original content in case all repairs fail
    const MAX_ATTEMPTS = 3
    let lastError = ''
    let currentContent = content
    
    console.log('🔧 [MermaidRenderer] AGGRESSIVE REPAIR: will try up to', MAX_ATTEMPTS, 'times until diagram renders')
    
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      try {
        console.log(`🔧 [MermaidRenderer] Repair attempt ${attempt}/${MAX_ATTEMPTS}`)
        console.log('🔧 [MermaidRenderer] Error context:', mermaidErrorDetail || error || lastError || 'No specific error captured')
        
        // Call the aggressive repair endpoint with error context
        const response = await api.post('/api/ai/repair-diagram', {
          mermaid_code: currentContent,
          diagram_type: artifactType,
          error_message: mermaidErrorDetail || error || lastError || null,
          improvement_focus: ['syntax', 'layout', 'relationships']
        })
        
        const improvedCode = response.data.improved_code?.trim()
        
        // Validate that we got actual content back
        if (response.data.success && improvedCode && improvedCode.length > 10) {
          console.log(`✅ [MermaidRenderer] Repair attempt ${attempt} returned code, testing render...`)
          console.log('✅ [MermaidRenderer] New content length:', improvedCode.length)
          
          // Try to render the repaired diagram to verify it works
          try {
            clearMermaidErrorArtifacts()
            await mermaid.parse(improvedCode)
            
            // Parse succeeded! Update content
            console.log(`✅ [MermaidRenderer] Repair successful on attempt ${attempt}!`, response.data.improvements_made)
            
            if (onContentUpdate) {
              onContentUpdate(improvedCode)
            }
            
            // Reset error state to trigger re-render
            setError(null)
            setLastErrorContent(null)
            setMermaidErrorDetail(null)
            setIsRepairing(false)
            return // SUCCESS - exit the function
          } catch (parseError: any) {
            // Repair returned something but it still doesn't render
            console.warn(`⚠️ [MermaidRenderer] Attempt ${attempt} returned invalid diagram:`, parseError.message)
            lastError = parseError.message || 'Parse error'
            currentContent = improvedCode // Use the repaired content for next attempt
            // Continue to next attempt
          }
        } else {
          // API returned failure
          console.warn(`⚠️ [MermaidRenderer] Attempt ${attempt} failed:`, response.data.error)
          lastError = response.data.error || 'Repair returned empty content'
          // Continue to next attempt with same content
        }
      } catch (err: any) {
        console.error(`❌ [MermaidRenderer] Attempt ${attempt} request failed:`, err)
        lastError = err.message || 'Network error'
        // Continue to next attempt
      }
      
      // Small delay between attempts to avoid overwhelming the server
      if (attempt < MAX_ATTEMPTS) {
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }
    
    // All attempts failed - restore original content
    console.error(`❌ [MermaidRenderer] All ${MAX_ATTEMPTS} repair attempts failed`)
    if (onContentUpdate) {
      onContentUpdate(originalContent)
    }
    setError(`Repair could not fix this diagram after ${MAX_ATTEMPTS} attempts. ${lastError || 'The diagram syntax may be too broken. Please try regenerating.'}`)
    setIsRepairing(false)
  }, [content, artifactType, onContentUpdate, isRepairing, setError, setIsRepairing, setLastErrorContent, mermaidErrorDetail, error])

  useEffect(() => {
    // Initialize Mermaid once
    if (!isInitialized) {
      // Suppress Mermaid’s internal parse error output
      try {
        ;(mermaid as any).parseError = () => {}
      } catch (e) {
        // ignore
      }

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
    if (!containerRef.current || !isInitialized) return
    
    // Handle empty content
    if (!content || content.trim().length === 0) {
      setError('Diagram content is empty. Please generate a diagram first or use AI Repair if you have existing content.')
      return
    }

    const renderDiagram = async () => {
      try {
        containerRefSnapshot.current = containerRef.current
        setError(null)
        setValidation(null)
        const container = containerRef.current
        if (!container) return

        // Clear previous content
        container.innerHTML = ''
        clearMermaidErrorArtifacts()

        // Extract Mermaid diagram from content (remove any surrounding text)
        let diagramContent = content.trim()
        
        // Try to extract from markdown code blocks first
        const mermaidPattern = /```(?:mermaid)?\s*\n(.*?)```/s
        const codeBlockMatch = diagramContent.match(mermaidPattern)
        if (codeBlockMatch) {
          diagramContent = codeBlockMatch[1].trim()
        } else {
          // If no code block, check if content already is mermaid code
          // Look for mermaid diagram type declarations
          const diagramTypes = [
            'erDiagram', 'flowchart', 'graph', 'sequenceDiagram',
            'classDiagram', 'stateDiagram', 'gantt', 'pie', 'journey',
            'gitgraph', 'mindmap', 'timeline', 'C4Context', 'C4Container',
            'C4Component', 'C4Deployment'
          ]
          
          // If content contains a diagram type, extract from there
          for (const dt of diagramTypes) {
            const idx = diagramContent.indexOf(dt)
            if (idx !== -1) {
              let extracted = diagramContent.substring(idx).trim()
              
              // Try to remove trailing explanatory text
              const lines = extracted.split('\n')
              const diagramLines: string[] = []
              
              for (const line of lines) {
                const lineTrimmed = line.trim()
                // Stop if we hit explanatory text
                if (lineTrimmed.startsWith('**Explanation') || 
                    lineTrimmed.startsWith('**Note') ||
                    lineTrimmed.startsWith('Explanation') ||
                    (lineTrimmed.startsWith('1.') && diagramLines.length > 5)) {
                  break
                }
                // Skip markdown formatting lines
                if (lineTrimmed && !lineTrimmed.startsWith('**') && !lineTrimmed.startsWith('#')) {
                  diagramLines.push(line)
                }
              }
              
              if (diagramLines.length > 0) {
                diagramContent = diagramLines.join('\n').trim()
                // Remove any remaining markdown formatting
                diagramContent = diagramContent.replace(/\*\*.*?\*\*/g, '')
                diagramContent = diagramContent.replace(/^#+\s+.*$/gm, '')
                diagramContent = diagramContent.trim()
              } else {
                diagramContent = extracted
              }
              break
            }
          }
        }
        
        // Fix ERD syntax if it's using class diagram syntax (client-side safety net)
        if (diagramContent.includes('erDiagram') && (diagramContent.includes('class ') || diagramContent.includes('CLASS '))) {
          // Convert class diagram syntax to ERD syntax
          diagramContent = diagramContent.replace(/class\s+(\w+)\s*\{([^}]+)\}/gi, (match, entityName, fieldsText) => {
            const erdFields: string[] = []
            for (const line of fieldsText.split('\n')) {
              const trimmed = line.trim()
              if (!trimmed || !trimmed.startsWith('-')) continue
              
              const fieldText = trimmed.substring(1).trim()
              const fieldMatch = fieldText.match(/(\w+)(?:\s*\(([^)]+)\))?/)
              if (fieldMatch) {
                const fieldName = fieldMatch[1]
                const description = fieldMatch[2] || ''
                
                let fieldType = 'string'
                if (fieldName.endsWith('_id') || fieldName === 'id') {
                  fieldType = 'int'
                } else if (fieldName.toLowerCase().includes('date') || fieldName.toLowerCase().includes('time')) {
                  fieldType = 'datetime'
                } else if (description.toLowerCase().includes('boolean') || fieldName.startsWith('is_') || fieldName.startsWith('has_')) {
                  fieldType = 'boolean'
                }
                
                let keySuffix = ''
                if (description.toLowerCase().includes('primary key') || fieldName === 'id') {
                  keySuffix = ' PK'
                } else if (description.toLowerCase().includes('foreign key') || (fieldName.endsWith('_id') && fieldName !== 'id')) {
                  keySuffix = ' FK'
                }
                
                erdFields.push(`        ${fieldType} ${fieldName}${keySuffix}`)
              }
            }
            
            if (erdFields.length > 0) {
              return `${entityName} {\n${erdFields.join('\n')}\n    }`
            }
            return `${entityName} {\n        int id PK\n    }`
          })
        }

        // Pre-validate the diagram content
        const validationResult = validateMermaidContent(diagramContent)
        setValidation(validationResult)
        
        // If there are critical errors, don't even try to render
        if (validationResult.errors.length > 0 && !validationResult.isValid) {
          console.warn('🔍 [MermaidRenderer] Validation failed, attempting render anyway:', validationResult.errors)
        }

        // Generate unique ID for this diagram
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`

        // Create a temporary div for rendering
        const tempDiv = document.createElement('div')
        tempDiv.id = id
        tempDiv.className = 'mermaid'
        tempDiv.textContent = diagramContent

        // Pre-validate via mermaid.parse to avoid internal error DOM output
        try {
          clearMermaidErrorArtifacts()
          mermaid.parse(diagramContent)
        } catch (parseErr: any) {
          clearMermaidErrorArtifacts()
          const rawErrorMsg = parseErr?.message || parseErr?.toString() || 'Unknown parse error'
          console.error('🔍 [MermaidRenderer] Parse error:', rawErrorMsg)
          setError(formatMermaidError(rawErrorMsg))
          setLastErrorContent(content)
          return
        }

        // Render the diagram
        const { svg } = await mermaid.render(id, diagramContent)
        
        // Check if the rendered SVG contains error elements
        const tempCheckDiv = document.createElement('div')
        tempCheckDiv.innerHTML = svg
        const hasError = tempCheckDiv.querySelector('.error-icon, .error-text, svg[aria-roledescription="error"]')
        
        if (hasError) {
          // If error SVG was created, don't insert it and show error message instead
          clearMermaidErrorArtifacts()
          setError(formatMermaidError())
          setLastErrorContent(content)
          return
        }
        
        // Insert the SVG
        container.innerHTML = svg

        // Double-check after insertion that no error SVG was created
        const insertedErrorSvg = container.querySelector('svg[aria-roledescription="error"]')
        if (insertedErrorSvg) {
          clearMermaidErrorArtifacts()
          container.innerHTML = ''
          setError(formatMermaidError())
          setLastErrorContent(content)
          return
        }

        // Note: Zoom is now applied via CSS transform on the container wrapper
        // This allows both zoom and pan to work together smoothly
        
        // Clear any previous error on successful render
        setError(null)
      } catch (err: any) {
        const rawErrorMsg = err?.message || err?.toString() || 'Unknown rendering error'
        console.error('Mermaid rendering error:', rawErrorMsg)
        clearMermaidErrorArtifacts()
        if (containerRefSnapshot.current) {
          containerRefSnapshot.current.innerHTML = ''
        }
        // Additional cleanup: remove any error SVGs that might have been created
        setTimeout(() => {
          clearMermaidErrorArtifacts()
          if (containerRefSnapshot.current) {
            containerRefSnapshot.current.innerHTML = ''
          }
        }, 100)
        setError(formatMermaidError(rawErrorMsg))
        setLastErrorContent(content)
      }
    }

    renderDiagram()
  }, [content, isInitialized, validateMermaidContent, setError, setValidation, setLastErrorContent])

  const handleZoomIn = () => zoomIn()
  const handleZoomOut = () => zoomOut()
  const handleResetZoom = () => {
    resetZoom()
    resetPan()
  }

  const handleDownload = () => {
    if (!containerRef.current) return
    
    const svg = containerRef.current.querySelector('svg')
    if (!svg) {
      setError('No diagram to download. Please generate or repair the diagram first.')
      return
    }

    const svgData = new XMLSerializer().serializeToString(svg)
    const blob = new Blob([svgData], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'diagram.svg'
    link.click()
    URL.revokeObjectURL(url)
  }

  // If there's an error, show the raw content with AI repair option
  if (error) {
    return (
      <div className={`h-full flex flex-col ${className}`}>
        {/* Error Banner with AI Repair Button */}
        <div className="bg-destructive/10 border-b border-destructive/30 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-destructive text-sm">Mermaid Syntax Error</h4>
            <p className="text-xs text-destructive/80 mt-1 break-words">{error}</p>
              {validation && validation.errors.length > 0 && (
                <ul className="mt-2 text-xs text-destructive/70 list-disc list-inside">
                  {validation.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              )}
              {validation && validation.warnings.length > 0 && (
                <ul className="mt-2 text-xs text-yellow-600 dark:text-yellow-400 list-disc list-inside">
                  {validation.warnings.map((warn, i) => (
                    <li key={i}>{warn}</li>
                  ))}
                </ul>
              )}
            </div>
            <button
              onClick={handleAIRepair}
              disabled={isRepairing}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg transition-all duration-200 shadow-lg shadow-primary/20 hover:shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
              title="Use AI to fix diagram syntax"
            >
              {isRepairing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm font-medium">Repairing...</span>
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  <span className="text-sm font-medium">AI Repair</span>
                </>
              )}
            </button>
          </div>
        </div>
        
        {/* Code Display */}
        <div className="flex-1 overflow-auto p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground font-medium">Mermaid Code</span>
            <button
              onClick={() => setShowCode(!showCode)}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {showCode ? <Eye className="w-3 h-3" /> : <Code className="w-3 h-3" />}
              {showCode ? 'Preview' : 'Code'}
            </button>
          </div>
          <pre className="whitespace-pre-wrap break-words text-sm font-mono text-foreground bg-muted/30 p-4 rounded-lg border border-border">
            {content}
          </pre>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative h-full flex flex-col ${className}`}>
      {/* Validation Warnings Banner (shown when diagram renders but has warnings) */}
      {validation && validation.warnings.length > 0 && !error && (
        <div className="bg-yellow-500/10 border-b border-yellow-500/30 px-4 py-2 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
          <span className="text-xs text-yellow-700 dark:text-yellow-300 flex-1">
            {validation.warnings.length} warning{validation.warnings.length > 1 ? 's' : ''}: {validation.warnings[0]}
            {validation.warnings.length > 1 && ` (+${validation.warnings.length - 1} more)`}
          </span>
          <button
            onClick={handleAIRepair}
            disabled={isRepairing}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-700 dark:text-yellow-300 rounded-md transition-colors text-xs font-medium"
            title="Use AI to improve diagram"
          >
            {isRepairing ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Wand2 className="w-3 h-3" />
            )}
            Improve
          </button>
        </div>
      )}
      
      {/* Zoom & Pan Controls - Enhanced visibility */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
        {/* Main Controls Bar */}
        <div className="flex items-center gap-1 bg-card/95 backdrop-blur-md border border-border/60 rounded-xl shadow-xl p-1.5">
          {/* Pan/Drag hint */}
          <div className="flex items-center gap-1 px-2 py-1 text-muted-foreground rounded-lg hover:bg-secondary/50" title="Drag to pan the diagram">
            <Move className="w-4 h-4" />
            <span className="text-xs hidden lg:inline font-medium">Drag</span>
          </div>
          <div className="w-px h-6 bg-border/50"></div>
          
          {/* Zoom Controls */}
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-secondary rounded-lg transition-all hover:scale-110"
            title="Zoom Out (or scroll down)"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="px-2 py-1 bg-secondary/50 rounded-lg min-w-[3.5rem] text-center">
            <span className="text-sm font-bold text-foreground">
              {Math.round(zoom * 100)}%
            </span>
          </div>
          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-secondary rounded-lg transition-all hover:scale-110"
            title="Zoom In (or scroll up)"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <div className="w-px h-6 bg-border/50"></div>
          
          {/* Reset & Download */}
          <button
            onClick={handleResetZoom}
            className="p-2 hover:bg-secondary rounded-lg transition-all hover:scale-110"
            title="Reset View (zoom + position)"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleDownload}
            className="p-2 hover:bg-secondary rounded-lg transition-all hover:scale-110"
            title="Download SVG"
          >
            <Download className="w-4 h-4" />
          </button>
          <div className="w-px h-6 bg-border/50"></div>
          
          {/* AI Repair */}
          <button
            onClick={handleAIRepair}
            disabled={isRepairing}
            className="p-2 hover:bg-primary/20 rounded-lg transition-all text-primary hover:scale-110 disabled:opacity-50 disabled:hover:scale-100"
            title="AI Improve Diagram"
          >
            {isRepairing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
          </button>
        </div>
        
        {/* Scroll hint */}
        <div className="text-[10px] text-muted-foreground/60 text-center hidden md:block">
          Scroll to zoom • Drag to pan
        </div>
      </div>

      {/* Diagram Container with Pan/Drag + Scroll Zoom Support */}
      <div 
        ref={diagramWrapperRef}
        className="flex-1 overflow-hidden p-4 flex items-center justify-center"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onWheel={handleWheel}
        style={{ 
          cursor: pan.isDragging ? 'grabbing' : 'grab',
          userSelect: 'none'
        }}
      >
        <div 
          ref={containerRef}
          className="mermaid-container"
          style={{ 
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: 'center center',
            transition: pan.isDragging ? 'none' : 'transform 0.2s ease',
            minWidth: 'fit-content',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center'
          }}
        />
      </div>
    </div>
  )
}

