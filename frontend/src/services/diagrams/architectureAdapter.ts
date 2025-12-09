/**
 * Architecture Diagram Adapter
 * Handles Mermaid architecture/component diagrams
 */

import { BaseDiagramAdapter, DiagramParseResult, MermaidGenerateOptions } from './baseDiagramAdapter'
import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class ArchitectureAdapter extends BaseDiagramAdapter {
  parseFromMermaid(mermaidCode: string): DiagramParseResult {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []

    // Extract components/nodes
    const extractedNodes = this.extractNodesGeneric(mermaidCode)
    const extractedEdges = this.extractEdgesGeneric(mermaidCode)

    // Calculate layout (layered architecture)
    const layers = this.detectLayers(extractedNodes)
    const positions = this.calculateLayeredLayout(layers)

    // Create nodes
    for (let i = 0; i < extractedNodes.length; i++) {
      const node = extractedNodes[i]
      const layer = this.detectNodeLayer(node.label)
      const color = this.getColorForLayer(layer)

      nodes.push({
        id: node.id,
        type: 'component',
        data: {
          label: node.label,
          color,
          layer,
        },
        position: positions[i] || { x: 0, y: 0 },
      })
    }

    // Create edges
    let edgeIndex = 0
    for (const edge of extractedEdges) {
      edges.push({
        id: `conn_${edgeIndex++}`,
        source: edge.from,
        target: edge.to,
        label: edge.label,
        type: 'dependency',
      })
    }

    return { nodes, edges }
  }

  generateMermaid(
    nodes: ReactFlowNode[],
    edges: ReactFlowEdge[],
    options?: MermaidGenerateOptions
  ): string {
    if (nodes.length === 0) {
      return 'graph TD\n  Frontend[Frontend Layer]\n  Backend[Backend Layer]\n  Database[Database Layer]\n  Frontend --> Backend\n  Backend --> Database'
    }

    const direction = options?.direction || 'TD'
    let mermaid = `graph ${direction}\n`

    // Group nodes by layer if available
    const layers = new Map<string, ReactFlowNode[]>()
    for (const node of nodes) {
      const layer = node.data.layer || 'default'
      if (!layers.has(layer)) {
        layers.set(layer, [])
      }
      layers.get(layer)!.push(node)
    }

    // Create a map from node.id to a clean Mermaid ID
    const idMap = new Map<string, string>()
    
    // Add nodes with subgraphs for layers
    for (const [layer, layerNodes] of layers.entries()) {
      if (layer !== 'default' && layerNodes.length > 1) {
        mermaid += `  subgraph ${layer}\n`
        for (const node of layerNodes) {
          const label = node.data.label || 'Component'
          const baseId = label.match(/^[a-zA-Z][a-zA-Z0-9\s]*$/) 
            ? label.replace(/\s+/g, '_')
            : node.id
          const cleanId = this.sanitizeId(baseId)
          const cleanLabel = this.sanitizeLabel(label)
          
          idMap.set(node.id, cleanId)
          mermaid += `    ${cleanId}["${cleanLabel}"]\n`
          
          if (options?.includeStyles && node.data.color) {
            mermaid += `    style ${cleanId} fill:${node.data.color},stroke:#333,stroke-width:2px\n`
          }
        }
        mermaid += '  end\n'
      } else {
        // No subgraph for single nodes
        for (const node of layerNodes) {
          const label = node.data.label || 'Component'
          const baseId = label.match(/^[a-zA-Z][a-zA-Z0-9\s]*$/) 
            ? label.replace(/\s+/g, '_')
            : node.id
          const cleanId = this.sanitizeId(baseId)
          const cleanLabel = this.sanitizeLabel(label)
          
          idMap.set(node.id, cleanId)
          mermaid += `  ${cleanId}["${cleanLabel}"]\n`
          
          if (options?.includeStyles && node.data.color) {
            mermaid += `  style ${cleanId} fill:${node.data.color},stroke:#333,stroke-width:2px\n`
          }
        }
      }
    }

    mermaid += '\n'

    // Add connections using the ID map
    for (const edge of edges) {
      const source = idMap.get(edge.source) || this.sanitizeId(edge.source)
      const target = idMap.get(edge.target) || this.sanitizeId(edge.target)
      const label = edge.label ? `|"${this.sanitizeLabel(edge.label)}"|` : ''

      mermaid += `  ${source} -->${label} ${target}\n`
    }

    return mermaid
  }

  validate(mermaidCode: string): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!mermaidCode.includes('graph')) {
      errors.push('Missing "graph" declaration')
    }

    return {
      valid: errors.length === 0,
      errors,
    }
  }

  getDefaultNodeType(): string {
    return 'component'
  }

  getDefaultEdgeType(): string {
    return 'dependency'
  }

  /**
   * Detect which layer a node belongs to based on its label
   */
  private detectNodeLayer(label: string): string {
    const lowerLabel = label.toLowerCase()

    if (lowerLabel.includes('frontend') || lowerLabel.includes('ui') || lowerLabel.includes('client') || lowerLabel.includes('web') || lowerLabel.includes('mobile')) {
      return 'Frontend'
    }
    if (lowerLabel.includes('backend') || lowerLabel.includes('api') || lowerLabel.includes('service') || lowerLabel.includes('server')) {
      return 'Backend'
    }
    if (lowerLabel.includes('database') || lowerLabel.includes('storage') || lowerLabel.includes('db') || lowerLabel.includes('cache')) {
      return 'Data'
    }
    if (lowerLabel.includes('gateway') || lowerLabel.includes('proxy') || lowerLabel.includes('load balancer')) {
      return 'Gateway'
    }
    if (lowerLabel.includes('auth') || lowerLabel.includes('security')) {
      return 'Security'
    }

    return 'default'
  }

  /**
   * Detect all unique layers
   */
  private detectLayers(nodes: Array<{ id: string; label: string }>): string[] {
    const layers = new Set<string>()
    for (const node of nodes) {
      layers.add(this.detectNodeLayer(node.label))
    }
    return Array.from(layers)
  }

  /**
   * Calculate layered layout (vertical stacking)
   */
  private calculateLayeredLayout(layers: string[]): Array<{ x: number; y: number }> {
    const positions: Array<{ x: number; y: number }> = []
    const layerOrder = ['Frontend', 'Gateway', 'Backend', 'Security', 'Data', 'default']
    
    const sortedLayers = layers.sort((a, b) => {
      const indexA = layerOrder.indexOf(a)
      const indexB = layerOrder.indexOf(b)
      return (indexA === -1 ? 999 : indexA) - (indexB === -1 ? 999 : indexB)
    })

    let y = 100
    const verticalSpacing = 250
    const horizontalSpacing = 300

    for (const layer of sortedLayers) {
      // For simplicity, place nodes horizontally in each layer
      for (let i = 0; i < 3; i++) { // Assume max 3 nodes per layer
        positions.push({
          x: i * horizontalSpacing + 200,
          y: y,
        })
      }
      y += verticalSpacing
    }

    return positions
  }

  /**
   * Assign colors based on layer
   */
  private getColorForLayer(layer: string): string {
    switch (layer) {
      case 'Frontend':
        return '#3b82f6' // blue
      case 'Backend':
        return '#22c55e' // green
      case 'Data':
        return '#f97316' // orange
      case 'Gateway':
        return '#a855f7' // purple
      case 'Security':
        return '#ef4444' // red
      default:
        return '#6366f1' // indigo
    }
  }
}

