/**
 * Diagram Service - API client for AI diagram parsing and improvement
 * Integrates with backend AI endpoints
 */

import api from './api'
import { ArtifactType } from './generationService'

export interface ReactFlowNode {
  id: string
  type: string
  data: {
    label: string
    color?: string
    [key: string]: any
  }
  position: {
    x: number
    y: number
  }
}

export interface ReactFlowEdge {
  id: string
  source: string
  target: string
  label?: string
  type?: string
  animated?: boolean
}

export interface ParseDiagramResponse {
  success: boolean
  nodes: ReactFlowNode[]
  edges: ReactFlowEdge[]
  metadata: {
    model_used: string
    diagram_type: string
    node_count: number
    edge_count: number
  }
  error?: string
}

export interface ImproveDiagramResponse {
  success: boolean
  improved_code: string
  improvements_made: string[]
  error?: string
}

export interface DiagramType {
  value: string
  label: string
  icon: string
}

/**
 * Parse Mermaid diagram code to React Flow JSON format
 */
export const parseDiagram = async (
  mermaidCode: string,
  diagramType: ArtifactType | string,
  layoutPreference?: 'horizontal' | 'vertical' | 'radial' | 'force'
): Promise<ParseDiagramResponse> => {
  try {
    const response = await api.post<ParseDiagramResponse>('/api/ai/parse-diagram', {
      mermaid_code: mermaidCode,
      diagram_type: diagramType,
      layout_preference: layoutPreference
    })
    return response.data
  } catch (error: any) {
    console.error('Failed to parse diagram:', error)
    return {
      success: false,
      nodes: [],
      edges: [],
      metadata: {
        model_used: 'unknown',
        diagram_type: diagramType.toString(),
        node_count: 0,
        edge_count: 0
      },
      error: error.response?.data?.detail || error.message || 'Failed to parse diagram'
    }
  }
}

/**
 * Get AI-powered diagram improvements
 */
export const improveDiagram = async (
  mermaidCode: string,
  diagramType: ArtifactType | string,
  improvementFocus: string[] = ['syntax', 'colors', 'layout', 'relationships']
): Promise<ImproveDiagramResponse> => {
  try {
    const response = await api.post<ImproveDiagramResponse>('/api/ai/improve-diagram', {
      mermaid_code: mermaidCode,
      diagram_type: diagramType,
      improvement_focus: improvementFocus
    })
    return response.data
  } catch (error: any) {
    console.error('Failed to improve diagram:', error)
    return {
      success: false,
      improved_code: mermaidCode, // Return original on error
      improvements_made: [],
      error: error.response?.data?.detail || error.message || 'Failed to improve diagram'
    }
  }
}

/**
 * Get list of supported diagram types for canvas editing
 */
export const getSupportedDiagramTypes = async (): Promise<DiagramType[]> => {
  try {
    const response = await api.get<{ supported_types: DiagramType[] }>('/api/ai/diagram-types')
    return response.data.supported_types
  } catch (error) {
    console.error('Failed to fetch diagram types:', error)
    return []
  }
}

/**
 * Check if a diagram type is supported for canvas editing
 */
export const isDiagramTypeSupported = (diagramType: string): boolean => {
  const supportedPrefixes = ['mermaid_', 'html_']
  return supportedPrefixes.some(prefix => diagramType.startsWith(prefix))
}

/**
 * Get diagram type category (flowchart, erd, sequence, etc.)
 */
export const getDiagramCategory = (diagramType: string): string => {
  const type = diagramType.replace('mermaid_', '').replace('html_', '')
  return type.split('_')[0] // e.g., 'erd', 'sequence', 'flowchart'
}

