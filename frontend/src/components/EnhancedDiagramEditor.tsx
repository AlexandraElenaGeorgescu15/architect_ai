/**
 * Enhanced Diagram Editor with React Flow
 * Full MiroMaid-style experience with bi-directional sync
 * Supports all 25+ diagram types
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react'
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

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

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

  // Load artifact content when selected
  useEffect(() => {
    if (selectedArtifact) {
      setMermaidCode(selectedArtifact.content)
      parseAndLoadDiagram(selectedArtifact.content, selectedArtifact.type)
    }
  }, [selectedArtifact?.id])

  /**
   * Parse Mermaid code and load into canvas (AI-powered or fallback)
   */
  const parseAndLoadDiagram = async (code: string, diagramType: string) => {
    try {
      setIsSyncing(true)

      // Try AI parsing first
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

        addNotification({
          type: 'success',
          message: `Loaded ${result.nodes.length} nodes using ${result.metadata.model_used}`,
        })
      } else {
        // Fallback to client-side parsing
        const adapter = getAdapterForDiagramType(diagramType)
        const parsed = adapter.parseFromMermaid(code)

        const flowNodes = parsed.nodes.map((node) => ({
          ...node,
          data: {
            ...node.data,
            onChange: handleNodeDataChange,
            onDelete: handleNodeDelete,
          },
        }))

        setNodes(flowNodes)
        setEdges(parsed.edges)

        addNotification({
          type: 'info',
          message: `Loaded ${parsed.nodes.length} nodes (client-side parsing)`,
        })
      }
    } catch (error) {
      console.error('Failed to parse diagram:', error)
      addNotification({
        type: 'error',
        message: 'Failed to parse diagram. Check console for details.',
      })
    } finally {
      setIsSyncing(false)
    }
  }

  /**
   * Generate Mermaid code from canvas (bi-directional sync)
   */
  const generateMermaidFromCanvas = useCallback(() => {
    if (!selectedArtifact) return

    const adapter = getAdapterForDiagramType(selectedArtifact.type)
    const generated = adapter.generateMermaid(
      nodes as ReactFlowNode[],
      edges as ReactFlowEdge[],
      { includeStyles: true }
    )

    setMermaidCode(generated)

    // Update artifact
    updateArtifact(selectedArtifact.id, {
      content: generated,
      lastModified: new Date().toISOString(),
    })

    addNotification({
      type: 'success',
      message: 'Code updated from canvas',
    })
  }, [nodes, edges, selectedArtifact, updateArtifact, addNotification])

  /**
   * Sync code to canvas
   */
  const handleSync = useCallback(() => {
    if (!selectedArtifact) return
    parseAndLoadDiagram(mermaidCode, selectedArtifact.type)
  }, [mermaidCode, selectedArtifact])

  /**
   * AI-powered diagram improvement
   */
  const handleMagicImprovement = useCallback(async () => {
    if (!selectedArtifact) return

    try {
      setIsImproving(true)

      const result = await improveDiagram(mermaidCode, selectedArtifact.type as any)

      if (result.success) {
        setMermaidCode(result.improved_code)
        
        // Parse improved code to canvas
        await parseAndLoadDiagram(result.improved_code, selectedArtifact.type)

        addNotification({
          type: 'success',
          message: `Improved: ${result.improvements_made.join(', ')}`,
        })
      } else {
        addNotification({
          type: 'error',
          message: result.error || 'Failed to improve diagram',
        })
      }
    } catch (error) {
      console.error('Failed to improve diagram:', error)
      addNotification({
        type: 'error',
        message: 'Failed to improve diagram. Check console for details.',
      })
    } finally {
      setIsImproving(false)
    }
  }, [mermaidCode, selectedArtifact, addNotification])

  /**
   * Handle node data changes (e.g., label, color)
   */
  const handleNodeDataChange = useCallback(
    (id: string, newData: Partial<any>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === id
            ? { ...node, data: { ...node.data, ...newData } }
            : node
        )
      )

      // Auto-sync to code after 1 second delay
      setTimeout(() => {
        generateMermaidFromCanvas()
      }, 1000)
    },
    [generateMermaidFromCanvas]
  )

  /**
   * Handle node deletion
   */
  const handleNodeDelete = useCallback((id: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== id))
    setEdges((eds) => eds.filter((edge) => edge.source !== id && edge.target !== id))

    // Auto-sync to code
    setTimeout(() => {
      generateMermaidFromCanvas()
    }, 500)
  }, [generateMermaidFromCanvas])

  /**
   * Handle edge creation
   */
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge(connection, eds))

      // Auto-sync to code
      setTimeout(() => {
        generateMermaidFromCanvas()
      }, 500)
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
    
    setNodes((nds) => [...nds, newNode])
    
    // Auto-sync to code
    setTimeout(() => {
      generateMermaidFromCanvas()
    }, 500)
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
    
    setNodes((nds) => [...nds, newNode])
    
    // Auto-sync to code
    setTimeout(() => {
      generateMermaidFromCanvas()
    }, 500)
  }, [handleNodeDataChange, handleNodeDelete, generateMermaidFromCanvas])

  /**
   * Handle code editor changes
   */
  const handleCodeChange = useCallback((code: string) => {
    setMermaidCode(code)
  }, [])

  /**
   * Save diagram to backend
   */
  const handleSave = useCallback(async () => {
    if (!selectedArtifact) {
      addNotification({
        type: 'error',
        message: 'No artifact selected',
      })
      return
    }

    try {
      setIsSaving(true)
      
      // Generate current Mermaid code from canvas
      const adapter = getAdapterForDiagramType(selectedArtifact.type)
      const generated = adapter.generateMermaid(
        nodes as ReactFlowNode[],
        edges as ReactFlowEdge[],
        { includeStyles: true }
      )

      // Update local store
      updateArtifact(selectedArtifact.id, {
        content: generated,
        updated_at: new Date().toISOString(),
      })

      // Save to backend
      const { updateArtifact: updateArtifactAPI } = await import('../services/generationService')
      await updateArtifactAPI(selectedArtifact.id, generated)

      addNotification({
        type: 'success',
        message: 'Diagram saved successfully!',
      })
    } catch (error) {
      console.error('Failed to save diagram:', error)
      addNotification({
        type: 'error',
        message: 'Failed to save diagram. Check console for details.',
      })
    } finally {
      setIsSaving(false)
    }
  }, [selectedArtifact, nodes, edges, updateArtifact, addNotification])

  /**
   * Download diagram as PNG
   */
  const handleDownload = useCallback(() => {
    addNotification({
      type: 'info',
      message: 'Download feature coming soon!',
    })
  }, [addNotification])

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
                title="Save Diagram"
              >
                {isSaving ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Save size={16} />
                )}
                Save
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

              <div className="text-xs text-gray-500 ml-2">
                {nodes.length} nodes, {edges.length} edges
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

      {/* Code Editor Sidebar */}
      <CodeEditor
        code={mermaidCode}
        onCodeChange={handleCodeChange}
        onSync={handleSync}
        onMagic={handleMagicImprovement}
        isSyncing={isSyncing}
        diagramType={selectedArtifact?.type || 'Mermaid'}
      />
    </div>
  )
}

