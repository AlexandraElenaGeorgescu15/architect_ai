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

import { Wand2, Download, Eye, Code as CodeIcon, Loader2 } from 'lucide-react'
import { useArtifactStore } from '../stores/artifactStore'
import { useUIStore } from '../stores/uiStore'
import { nodeTypes } from './nodes'
import CodeEditor from './CodeEditor'
import { parseDiagram, improveDiagram } from '../services/diagramService'
import { getAdapterForDiagramType } from '../services/diagrams'
import type { ReactFlowNode, ReactFlowEdge } from '../services/diagramService'

export default function EnhancedDiagramEditor() {
  const { artifacts, updateArtifact } = useArtifactStore()
  const { addNotification } = useUIStore()

  // State
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'canvas' | 'code'>('canvas')
  const [mermaidCode, setMermaidCode] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [isImproving, setIsImproving] = useState(false)

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Get selected artifact
  const selectedArtifact = selectedArtifactId
    ? artifacts.find((a) => a.id === selectedArtifactId)
    : null

  // Get diagram artifacts
  const diagramArtifacts = artifacts.filter(
    (a) => a.type.startsWith('mermaid_') || a.type.startsWith('html_')
  )

  // Initialize with first artifact
  useEffect(() => {
    if (diagramArtifacts.length > 0 && !selectedArtifactId) {
      setSelectedArtifactId(diagramArtifacts[0].id)
    }
  }, [diagramArtifacts.length, selectedArtifactId])

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
   * Handle code editor changes
   */
  const handleCodeChange = useCallback((code: string) => {
    setMermaidCode(code)
  }, [])

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
            <Panel position="top-center" className="bg-white rounded-lg shadow-lg p-2 flex gap-2 items-center border border-gray-200">
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

