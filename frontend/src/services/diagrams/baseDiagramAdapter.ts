/**
 * Base Diagram Adapter
 * Abstract base class for all diagram type adapters
 */

import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export interface DiagramParseResult {
  nodes: ReactFlowNode[]
  edges: ReactFlowEdge[]
  metadata?: Record<string, any>
}

export interface MermaidGenerateOptions {
  direction?: 'TD' | 'LR' | 'RL' | 'BT'
  includeStyles?: boolean
  compactMode?: boolean
}

export abstract class BaseDiagramAdapter {
  /**
   * Parse Mermaid code to React Flow format
   * This is the fallback if AI parsing is not available
   */
  abstract parseFromMermaid(mermaidCode: string): DiagramParseResult

  /**
   * Generate Mermaid code from React Flow nodes/edges
   * Used for bi-directional sync (canvas → code)
   */
  abstract generateMermaid(
    nodes: ReactFlowNode[],
    edges: ReactFlowEdge[],
    options?: MermaidGenerateOptions
  ): string

  /**
   * Validate if Mermaid code is valid for this diagram type
   */
  abstract validate(mermaidCode: string): { valid: boolean; errors: string[] }

  /**
   * Get default node type for this diagram
   */
  abstract getDefaultNodeType(): string

  /**
   * Get default edge type for this diagram
   */
  abstract getDefaultEdgeType(): string

  /**
   * Get diagram-specific color palette
   */
  getColorPalette(): string[] {
    return [
      '#ef4444', // red
      '#f97316', // orange
      '#eab308', // yellow
      '#22c55e', // green
      '#06b6d4', // cyan
      '#3b82f6', // blue
      '#6366f1', // indigo
      '#a855f7', // purple
      '#ec4899', // pink
      '#64748b', // slate
    ]
  }

  /**
   * Sanitize label for Mermaid (remove special characters)
   */
  protected sanitizeLabel(label: string): string {
    return label.replace(/["[\]]/g, '').replace(/\n/g, ' ')
  }

  /**
   * Sanitize ID for Mermaid (alphanumeric + underscore only)
   */
  protected sanitizeId(id: string): string {
    return id.replace(/[^a-zA-Z0-9_]/g, '_')
  }

  /**
   * Calculate automatic layout (grid-based)
   * Override for custom layout logic
   */
  protected calculateLayout(
    nodeCount: number,
    spacing: number = 300
  ): Array<{ x: number; y: number }> {
    const positions: Array<{ x: number; y: number }> = []
    const columns = Math.ceil(Math.sqrt(nodeCount))

    for (let i = 0; i < nodeCount; i++) {
      const col = i % columns
      const row = Math.floor(i / columns)
      positions.push({
        x: col * spacing + 100,
        y: row * spacing + 100,
      })
    }

    return positions
  }

  /**
   * Extract nodes from Mermaid code (generic regex-based)
   * Override for diagram-specific parsing
   */
  protected extractNodesGeneric(mermaidCode: string): Array<{ id: string; label: string }> {
    const nodes: Array<{ id: string; label: string }> = []
    
    // Match various node formats: A[Label], A(Label), A{Label}, etc.
    const nodeRegex = /(\w+)[\[\(\{]([^\]\)\}]+)[\]\)\}]/g
    let match

    while ((match = nodeRegex.exec(mermaidCode)) !== null) {
      nodes.push({
        id: match[1],
        label: match[2],
      })
    }

    return nodes
  }

  /**
   * Extract edges from Mermaid code (generic regex-based)
   */
  protected extractEdgesGeneric(mermaidCode: string): Array<{ from: string; to: string; label?: string }> {
    const edges: Array<{ from: string; to: string; label?: string }> = []
    
    // Match various arrow formats: A --> B, A --|Label| B, etc.
    const edgeRegex = /(\w+)\s*(?:--|\.-|-\.-|==)(?:>|\|([^\|]*)\|)(?:>|\-)?\s*(\w+)/g
    let match

    while ((match = edgeRegex.exec(mermaidCode)) !== null) {
      edges.push({
        from: match[1],
        to: match[3],
        label: match[2]?.trim() || undefined,
      })
    }

    return edges
  }
}

