/**
 * Enhanced Diagram Editor with React Flow
 * Full MiroMaid-style experience with bi-directional sync
 * Supports all 25+ diagram types
 */

import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  BackgroundVariant,
  Panel,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { Wand2, Download, Eye, Code as CodeIcon, Loader2, Plus, Square, Circle, Table, Box, Save } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { nodeTypes } from './nodes'
import CodeEditor from './CodeEditor'
import { parseDiagram, improveDiagram } from '../services/diagramService'
import { getAdapterForDiagramType } from '../services/diagrams'
import type { ReactFlowNode, ReactFlowEdge } from '../services/diagramService'

interface EnhancedDiagramEditorProps {
  selectedArtifactId?: string | null
}

export default function EnhancedDiagramEditor({ selectedArtifactId: propSelectedArtifactId }: EnhancedDiagramEditorProps = {}) {
  const { artifacts, updateArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()

  // State
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(propSelectedArtifactId || null)
  const [viewMode, setViewMode] = useState<'canvas' | 'code'>('canvas')
  const [mermaidCode, setMermaidCode] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [isImproving, setIsImproving] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isCodePanelCollapsed, setIsCodePanelCollapsed] = useState(() => {
    // Default to collapsed on small screens, expanded on larger screens
    const stored = localStorage.getItem('canvas_code_panel_collapsed')
    return stored !== null ? stored === 'true' : window.innerWidth < 1200
  })
  
  // Toggle code panel and persist
  const toggleCodePanel = () => {
    const newValue = !isCodePanelCollapsed
    setIsCodePanelCollapsed(newValue)
    localStorage.setItem('canvas_code_panel_collapsed', String(newValue))
  }

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  
  // Refs to track latest state (avoids stale closures in callbacks)
  const nodesRef = useRef<Node[]>([])
  const edgesRef = useRef<Edge[]>([])
  
  // Keep refs in sync with state
  useEffect(() => {
    nodesRef.current = nodes
  }, [nodes])
  
  useEffect(() => {
    edgesRef.current = edges
  }, [edges])

  // Get selected artifact
  const selectedArtifact = selectedArtifactId
    ? artifacts.find((a) => a.id === selectedArtifactId)
    : null

  // Get diagram artifacts (only Mermaid, no HTML)
  const diagramArtifacts = artifacts.filter(
    (a) => a.type.startsWith('mermaid_')
  )

  // Update selected artifact when prop changes
  useEffect(() => {
    if (propSelectedArtifactId) {
      setSelectedArtifactId(propSelectedArtifactId)
    }
  }, [propSelectedArtifactId])

  // Initialize with first artifact if no prop provided
  useEffect(() => {
    if (diagramArtifacts.length > 0 && !selectedArtifactId && !propSelectedArtifactId) {
      setSelectedArtifactId(diagramArtifacts[0].id)
    }
  }, [diagramArtifacts.length, selectedArtifactId, propSelectedArtifactId])
  
  // Reload artifacts when component mounts or artifacts change
  useEffect(() => {
    const loadArtifacts = async () => {
      try {
        const { listArtifacts } = await import('../services/generationService')
        const loadedArtifacts = await listArtifacts()
        useArtifactStore.getState().setArtifacts(loadedArtifacts)
      } catch (error) {
        console.error('Failed to reload artifacts:', error)
      }
    }
    loadArtifacts()
  }, [])

  /**
   * Generate Mermaid code from canvas (bi-directional sync)
   * Uses refs to always get latest state, avoiding stale closures
   * MUST be defined first as other callbacks depend on it
   */
  const generateMermaidFromCanvas = useCallback((currentNodes?: Node[], currentEdges?: Edge[]) => {
    if (!selectedArtifact) return

    // Use provided values or fall back to refs (which have latest state)
    const nodesToUse = currentNodes || nodesRef.current
    const edgesToUse = currentEdges || edgesRef.current

    const adapter = getAdapterForDiagramType(selectedArtifact.type)
    const generated = adapter.generateMermaid(
      nodesToUse as ReactFlowNode[],
      edgesToUse as ReactFlowEdge[],
      { includeStyles: true }
    )

    setMermaidCode(generated)

    // Update artifact
    updateArtifact(selectedArtifact.id, {
      content: generated,
      lastModified: new Date().toISOString(),
    })

    addNotification('success', 'Code updated from canvas')
  }, [selectedArtifact, updateArtifact, addNotification])

  /**
   * Handle node deletion
   */
  const handleNodeDelete = useCallback((id: string) => {
    // We need to update both nodes and edges, then sync
    let updatedNodes: Node[] = []
    let updatedEdges: Edge[] = []
    
    setNodes((nds) => {
      updatedNodes = nds.filter((node) => node.id !== id)
      return updatedNodes
    })
    
    setEdges((eds) => {
      updatedEdges = eds.filter((edge) => edge.source !== id && edge.target !== id)
      // Sync to code after both state updates with the new values
      setTimeout(() => {
        generateMermaidFromCanvas(updatedNodes, updatedEdges)
      }, 100)
      return updatedEdges
    })
  }, [generateMermaidFromCanvas])

  /**
   * Handle node data changes (e.g., label, color)
   * Prevents unnecessary re-renders that cause properties to disappear
   */
  const handleNodeDataChange = useCallback(
    (id: string, newData: Partial<any>) => {
      setNodes((nds) => {
        const updatedNodes = nds.map((node) =>
          node.id === id
            ? { 
                ...node, 
                data: { 
                  ...node.data, 
                  ...newData,
                  // Preserve callbacks
                  onChange: handleNodeDataChange,
                  onDelete: handleNodeDelete,
                } 
              }
            : node
        )

        // Update refs immediately to prevent stale state
        nodesRef.current = updatedNodes

        // Auto-sync to code after a short delay with the updated nodes
        setTimeout(() => {
          generateMermaidFromCanvas(updatedNodes, edgesRef.current)
        }, 500)
        
        return updatedNodes
      })
    },
    [generateMermaidFromCanvas, handleNodeDelete]
  )

  /**
   * Parse Mermaid code and load into canvas (rule-based first, AI only if needed)
   * MUST be defined before useEffect that uses it
   */
  const parseAndLoadDiagram = useCallback(async (code: string, diagramType: string, useAI: boolean = false) => {
    if (!code || !code.trim()) {
      console.warn('parseAndLoadDiagram: Empty code provided')
      addNotification('warning', 'No diagram code to parse')
      return
    }

    try {
      setIsSyncing(true)

      // ALWAYS try rule-based parsing first (fast, no AI needed)
      try {
        const adapter = getAdapterForDiagramType(diagramType)
        
        // Clean the code first if adapter has cleanMermaidCode method
        let cleanedCode = code
        if ('cleanMermaidCode' in adapter && typeof (adapter as any).cleanMermaidCode === 'function') {
          cleanedCode = (adapter as any).cleanMermaidCode(code)
        }
        
        if (!cleanedCode || !cleanedCode.trim()) {
          console.warn('parseAndLoadDiagram: Code became empty after cleaning')
          addNotification('warning', 'Diagram code is empty after cleaning')
          return
        }
        
        const parsed = adapter.parseFromMermaid(cleanedCode)

        if (parsed.nodes.length > 0) {
          // Convert to React Flow format with callbacks
          const flowNodes = parsed.nodes.map((node) => ({
            ...node,
            data: {
              ...node.data,
              onChange: handleNodeDataChange,
              onDelete: handleNodeDelete,
            },
          }))

          setNodes(flowNodes)
          setEdges(parsed.edges || [])

          addNotification('success', `Loaded ${parsed.nodes.length} nodes (rule-based parsing)`)
          return // Success with rule-based parsing
        } else {
          console.warn('Rule-based parsing returned 0 nodes for:', cleanedCode.substring(0, 100))
          addNotification('warning', 'Could not parse diagram - no nodes found')
        }
      } catch (ruleError) {
        console.error('Rule-based parsing failed:', ruleError)
        addNotification('error', `Parsing failed: ${ruleError instanceof Error ? ruleError.message : 'Unknown error'}`)
      }

      // Only use AI parsing if rule-based failed AND useAI is true (e.g., for repair/improve)
      if (useAI) {
        try {
          const result = await parseDiagram(code, diagramType as any)

          if (result.success && result.nodes.length > 0) {
            // Convert to React Flow format with callbacks
            const flowNodes = result.nodes.map((node) => ({
              ...node,
              data: {
                ...node.data,
                onChange: handleNodeDataChange,
                onDelete: handleNodeDelete,
              },
            }))

            setNodes(flowNodes)
            setEdges(result.edges)

            addNotification('success', `Loaded ${result.nodes.length} nodes using AI parsing`)
            return
          }
        } catch (aiError) {
          console.error('AI parsing also failed:', aiError)
        }
      }

      // If both failed, show error
      addNotification('error', 'Failed to parse diagram. Please check the Mermaid syntax.')
    } catch (error) {
      console.error('Failed to parse diagram:', error)
      addNotification('error', `Failed to parse diagram: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSyncing(false)
    }
  }, [handleNodeDataChange, handleNodeDelete, addNotification])

  // Load artifact content when selected (clean the content first)
  // MUST be after parseAndLoadDiagram is defined
  useEffect(() => {
    if (selectedArtifact && selectedArtifact.content) {
      // Clean the content to remove explanatory text
      const adapter = getAdapterForDiagramType(selectedArtifact.type)
      const cleanedContent = 'cleanMermaidCode' in adapter 
        ? (adapter as any).cleanMermaidCode(selectedArtifact.content)
        : selectedArtifact.content
      
      if (cleanedContent && cleanedContent.trim()) {
        setMermaidCode(cleanedContent)
        // Use rule-based parsing first (fast, no AI)
        parseAndLoadDiagram(cleanedContent, selectedArtifact.type, false)
      } else {
        console.warn('Selected artifact has no content:', selectedArtifact.id)
        addNotification('warning', 'Selected artifact has no content to display')
      }
    }
  }, [selectedArtifact?.id, selectedArtifact?.content, parseAndLoadDiagram, addNotification])

  /**
   * Sync code to canvas (rule-based parsing, no AI)
   */
  const handleSync = useCallback(() => {
    if (!selectedArtifact) return
    parseAndLoadDiagram(mermaidCode, selectedArtifact.type, false)
  }, [mermaidCode, selectedArtifact, parseAndLoadDiagram])

  /**
   * AI-powered diagram improvement
   */
  const handleMagicImprovement = useCallback(async () => {
    if (!selectedArtifact) {
      addNotification('warning', 'Please select a diagram first')
      return
    }

    if (!mermaidCode.trim()) {
      addNotification('warning', 'No diagram code to improve')
      return
    }

    try {
      setIsImproving(true)
      addNotification('info', 'Analyzing diagram with AI...')

      const result = await improveDiagram(mermaidCode, selectedArtifact.type as any)

      if (result.success && result.improved_code && result.improved_code.trim().length > 10) {
        // Only update if we got meaningful improvements
        if (result.improved_code.trim() !== mermaidCode.trim()) {
          setMermaidCode(result.improved_code)
          
          // Parse improved code to canvas (use rule-based first, AI only if needed)
          await parseAndLoadDiagram(result.improved_code, selectedArtifact.type, false)

          const improvements = result.improvements_made.length > 0 
            ? result.improvements_made.join(', ')
            : 'Diagram optimized'
          addNotification('success', `AI Improved: ${improvements}`)
        } else {
          addNotification('info', 'Diagram already looks good! No changes needed.')
        }
      } else {
        // Show user-friendly error
        const errorMsg = result.error || 'AI could not improve the diagram'
        addNotification('warning', errorMsg)
      }
    } catch (error: any) {
      console.error('Failed to improve diagram:', error)
      const errorMsg = error?.response?.data?.detail || error?.message || 'AI service unavailable'
      addNotification('error', `Failed to improve: ${errorMsg}`)
    } finally {
      setIsImproving(false)
    }
  }, [mermaidCode, selectedArtifact, addNotification, parseAndLoadDiagram])


  /**
   * Handle edge creation
   */
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => {
        const updatedEdges = addEdge(connection, eds)
        // Sync to code with the updated edges
        setTimeout(() => {
          generateMermaidFromCanvas(nodesRef.current, updatedEdges)
        }, 100)
        return updatedEdges
      })
    },
    [generateMermaidFromCanvas]
  )

  /**
   * Handle adding new nodes to canvas
   */
  const handleAddNode = useCallback((nodeType: 'custom' | 'entity' | 'component' | 'decision' = 'custom') => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: nodeType,
      position: {
        x: Math.random() * 400 + 100,
        y: Math.random() * 300 + 100,
      },
      data: {
        label: nodeType === 'entity' ? 'New Entity' : nodeType === 'component' ? 'New Component' : nodeType === 'decision' ? 'Decision?' : 'New Node',
        onChange: handleNodeDataChange,
        onDelete: handleNodeDelete,
        ...(nodeType === 'entity' ? { properties: [] } : {}),
      },
    }
    
    // Update state and sync code with the new nodes
    setNodes((nds) => {
      const updatedNodes = [...nds, newNode]
      // Sync to code immediately with the new state
      setTimeout(() => {
        generateMermaidFromCanvas(updatedNodes, edgesRef.current)
      }, 100)
      return updatedNodes
    })
  }, [handleNodeDataChange, handleNodeDelete, generateMermaidFromCanvas])

  /**
   * Handle adding table node (for ERD diagrams)
   */
  const handleAddTable = useCallback(() => {
    const newNode: Node = {
      id: `table-${Date.now()}`,
      type: 'entity',
      position: {
        x: Math.random() * 400 + 100,
        y: Math.random() * 300 + 100,
      },
      data: {
        label: 'New Table',
        properties: ['id (PK)', 'name', 'created_at'],
        onChange: handleNodeDataChange,
        onDelete: handleNodeDelete,
      },
    }
    
    // Update state and sync code with the new nodes
    setNodes((nds) => {
      const updatedNodes = [...nds, newNode]
      // Sync to code immediately with the new state
      setTimeout(() => {
        generateMermaidFromCanvas(updatedNodes, edgesRef.current)
      }, 100)
      return updatedNodes
    })
  }, [handleNodeDataChange, handleNodeDelete, generateMermaidFromCanvas])

  /**
   * Handle code editor changes
   */
  const handleCodeChange = useCallback((code: string) => {
    setMermaidCode(code)
  }, [])

  /**
   * Save diagram to backend and create a new version
   * Uses refs to always get the latest state
   */
  const handleSave = useCallback(async () => {
    if (!selectedArtifact) {
      addNotification('error', 'No artifact selected')
      return
    }

    try {
      setIsSaving(true)
      
      // Generate current Mermaid code from canvas using refs for latest state
      const adapter = getAdapterForDiagramType(selectedArtifact.type)
      const generated = adapter.generateMermaid(
        nodesRef.current as ReactFlowNode[],
        edgesRef.current as ReactFlowEdge[],
        { includeStyles: true }
      )

      // Update local state with the generated code
      setMermaidCode(generated)

      // Update local store
      updateArtifact(selectedArtifact.id, {
        content: generated,
        updated_at: new Date().toISOString(),
      })

      // Save to backend artifact
      const { updateArtifact: updateArtifactAPI } = await import('../services/generationService')
      await updateArtifactAPI(selectedArtifact.id, generated)

      // Also create a new version in the version service
      // Use artifact type as the artifact_id (stable versioning)
      try {
        const { default: api } = await import('../services/api')
        await api.post('/api/versions/create', {
          artifact_id: selectedArtifact.type,  // Use type as stable ID
          artifact_type: selectedArtifact.type,
          content: generated,
          metadata: {
            source: 'canvas_editor',
            model_used: 'manual_edit',
            validation_score: 100,
            is_valid: true
          }
        })
        addNotification('success', 'Diagram saved as new version!')
      } catch (versionError) {
        console.warn('Failed to create version (version API may not exist):', versionError)
        addNotification('success', 'Diagram saved successfully!')
      }
    } catch (error) {
      console.error('Failed to save diagram:', error)
      addNotification('error', 'Failed to save diagram. Check console for details.')
    } finally {
      setIsSaving(false)
    }
  }, [selectedArtifact, updateArtifact, addNotification])

  /**
   * Download diagram as file (Mermaid code or SVG)
   */
  const handleDownload = useCallback(() => {
    if (!selectedArtifact || !mermaidCode) {
      addNotification('warning', 'No diagram to download')
      return
    }
    
    // Create download options
    const downloadMermaid = () => {
      const blob = new Blob([mermaidCode], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedArtifact.type.replace('mermaid_', '')}_diagram.mmd`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      addNotification('success', 'Mermaid file downloaded!')
    }
    
    // For now, download as Mermaid code (PNG export requires canvas rendering)
    downloadMermaid()
  }, [selectedArtifact, mermaidCode, addNotification])

  // Empty state
  if (diagramArtifacts.length === 0) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <CodeIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p className="text-lg font-medium text-gray-600 mb-2">
            No diagrams available
          </p>
          <p className="text-sm text-gray-500">
            Generate a Mermaid or HTML diagram first to use the Canvas editor
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex relative">
      {/* Canvas View */}
      {viewMode === 'canvas' ? (
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            className="bg-gray-50"
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
            <Controls />

            {/* Top Toolbar */}
            <Panel position="top-center" className="bg-white rounded-lg shadow-lg p-2 flex gap-2 items-center border border-gray-200 z-10">
              {/* Add Node Controls */}
              <div className="flex items-center gap-1 border-r border-gray-300 pr-2">
                <button
                  onClick={() => handleAddNode('custom')}
                  className="px-2 py-1.5 bg-blue-500 text-white rounded-md text-xs font-medium flex items-center gap-1 hover:bg-blue-600"
                  title="Add Node"
                >
                  <Plus size={14} />
                  Node
                </button>
                <button
                  onClick={() => handleAddNode('entity')}
                  className="px-2 py-1.5 bg-green-500 text-white rounded-md text-xs font-medium flex items-center gap-1 hover:bg-green-600"
                  title="Add Entity/Table"
                >
                  <Table size={14} />
                  Table
                </button>
                <button
                  onClick={() => handleAddNode('component')}
                  className="px-2 py-1.5 bg-purple-500 text-white rounded-md text-xs font-medium flex items-center gap-1 hover:bg-purple-600"
                  title="Add Component"
                >
                  <Box size={14} />
                  Component
                </button>
                <button
                  onClick={() => handleAddNode('decision')}
                  className="px-2 py-1.5 bg-orange-500 text-white rounded-md text-xs font-medium flex items-center gap-1 hover:bg-orange-600"
                  title="Add Decision"
                >
                  <Circle size={14} />
                  Decision
                </button>
              </div>

              <div className="w-px h-6 bg-gray-300"></div>

              <button
                onClick={handleSave}
                disabled={isSaving || !selectedArtifact}
                className="px-3 py-1.5 bg-green-600 text-white rounded-md text-sm font-medium flex items-center gap-1.5 hover:bg-green-700 disabled:opacity-50"
                title="Save as new version"
              >
                {isSaving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Save size={16} />
                )}
                Save Version
              </button>

              <div className="w-px h-6 bg-gray-300"></div>

              <button
                onClick={handleMagicImprovement}
                disabled={isImproving}
                className="px-3 py-1.5 bg-purple-600 text-white rounded-md text-sm font-medium flex items-center gap-1.5 hover:bg-purple-700 disabled:opacity-50"
                title="AI Improvement"
              >
                {isImproving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Wand2 size={16} />
                )}
                AI Improve
              </button>

              <div className="w-px h-6 bg-gray-300"></div>

              <button
                onClick={() => setViewMode('code')}
                className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md text-sm font-medium flex items-center gap-1.5 hover:bg-gray-200"
              >
                <CodeIcon size={16} />
                Code
              </button>

              <button
                onClick={handleDownload}
                className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md text-sm font-medium flex items-center gap-1.5 hover:bg-gray-200"
              >
                <Download size={16} />
                Export
              </button>
            </Panel>
            
            {/* Stats Badge - Bottom left, always visible */}
            <Panel position="bottom-left" className="bg-white/90 backdrop-blur-sm rounded-lg shadow-md px-3 py-2 border border-gray-200">
              <div className="text-sm font-medium text-gray-700 flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  {nodes.length} nodes
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  {edges.length} edges
                </span>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      ) : (
        /* Code View */
        <div className="flex-1 flex">
          <div className="flex-1 flex items-center justify-center bg-gray-100 p-4">
            <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl">
              <CodeIcon className="w-12 h-12 mx-auto mb-4 text-indigo-600" />
              <h3 className="text-lg font-semibold text-center mb-2">
                Code Editor Mode
              </h3>
              <p className="text-sm text-gray-600 text-center mb-4">
                Edit code in the panel on the right and click <b>Render</b> to
                update the canvas.
              </p>
              <button
                onClick={() => setViewMode('canvas')}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 flex items-center justify-center gap-2"
              >
                <Eye size={16} />
                View Canvas
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Code Editor Sidebar - Collapsible */}
      <CodeEditor
        code={mermaidCode}
        onCodeChange={handleCodeChange}
        onSync={handleSync}
        onMagic={handleMagicImprovement}
        isSyncing={isSyncing}
        diagramType={selectedArtifact?.type || 'Mermaid'}
        isCollapsed={isCodePanelCollapsed}
        onToggleCollapse={toggleCodePanel}
      />
    </div>
  )
}

