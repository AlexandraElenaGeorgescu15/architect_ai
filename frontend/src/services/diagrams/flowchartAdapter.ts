/**
 * Flowchart Adapter
 * Handles Mermaid flowchart diagrams (like MiroMaid)
 */

import { BaseDiagramAdapter, DiagramParseResult, MermaidGenerateOptions } from './baseDiagramAdapter'
import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class FlowchartAdapter extends BaseDiagramAdapter {
  parseFromMermaid(mermaidCode: string): DiagramParseResult {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []

    // Clean the code first
    const cleanCode = this.cleanMermaidCode(mermaidCode)

    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/dfc1763a-e24e-49d7-baae-a7a908b307cd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'flowchartAdapter.ts:parseFromMermaid',message:'FlowchartAdapter parsing',data:{codeLength:cleanCode.length,hasGraph:cleanCode.includes('graph'),hasFlowchart:cleanCode.includes('flowchart'),codePreview:cleanCode.substring(0,300)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H3'})}).catch(()=>{});
    // #endregion

    // Extract direction (TD, LR, etc.) - handle both "graph" and "flowchart"
    const directionMatch = cleanCode.match(/(?:graph|flowchart)\s+(TD|LR|RL|BT)/i)
    const direction = directionMatch ? directionMatch[1] : 'TD'

    // Extract nodes with various shapes
    const nodeMatches = cleanCode.matchAll(/(\w+)\[([^\]]+)\]/g) // Rectangle [Label]
    const circleMatches = cleanCode.matchAll(/(\w+)\(\(([^)]+)\)\)/g) // Circle ((Label))
    const roundedMatches = cleanCode.matchAll(/(\w+)\(([^)]+)\)/g) // Rounded (Label)
    const diamondMatches = cleanCode.matchAll(/(\w+)\{([^}]+)\}/g) // Diamond {Label}

    const nodeMap = new Map<string, { label: string; shape: string }>()

    // Process all node types
    for (const match of nodeMatches) {
      nodeMap.set(match[1], { label: match[2], shape: 'rectangle' })
    }
    for (const match of circleMatches) {
      nodeMap.set(match[1], { label: match[2], shape: 'circle' })
    }
    for (const match of roundedMatches) {
      if (!nodeMap.has(match[1])) { // Avoid overriding circles
        nodeMap.set(match[1], { label: match[2], shape: 'rounded' })
      }
    }
    for (const match of diamondMatches) {
      nodeMap.set(match[1], { label: match[2], shape: 'diamond' })
    }

    // Calculate layout based on direction
    const positions = this.calculateFlowLayout(nodeMap.size, direction)

    // Create React Flow nodes
    let index = 0
    for (const [id, { label, shape }] of nodeMap.entries()) {
      const color = this.getColorForNodeType(label)
      nodes.push({
        id,
        type: shape === 'diamond' ? 'decision' : 'custom',
        data: {
          label,
          color,
          shape,
        },
        position: positions[index] || { x: 0, y: 0 },
      })
      index++
    }

    // Extract edges - handle various arrow styles
    const edgeMatches = cleanCode.matchAll(/(\w+)\s*--([->|]?)(?:\|([^|]*)\|)?([->|]?)\s*(\w+)/g)
    let edgeIndex = 0

    for (const match of edgeMatches) {
      const from = match[1]
      const to = match[5]
      const label = match[3]?.trim()
      const hasArrow = match[2] === '>' || match[4] === '>'

      edges.push({
        id: `edge_${edgeIndex++}`,
        source: from,
        target: to,
        label,
        type: hasArrow ? 'default' : 'straight',
        animated: false,
      })
    }

    return { nodes, edges, metadata: { direction } }
  }

  generateMermaid(
    nodes: ReactFlowNode[],
    edges: ReactFlowEdge[],
    options?: MermaidGenerateOptions
  ): string {
    if (nodes.length === 0) {
      return 'graph TD\n  Start[Start Here]'
    }

    const direction = options?.direction || 'TD'
    let mermaid = `graph ${direction}\n`

    // Create a map from node.id to a clean Mermaid ID
    const idMap = new Map<string, string>()
    
    // Add nodes with appropriate shapes
    for (const node of nodes) {
      // Create a stable, clean ID from the label or node id
      const label = node.data.label || 'Node'
      const cleanLabel = this.sanitizeLabel(label)
      // Use label as basis for ID if it's simple enough, otherwise use sanitized node.id
      const baseId = label.match(/^[a-zA-Z][a-zA-Z0-9\s]*$/) 
        ? label.replace(/\s+/g, '_')
        : node.id
      const cleanId = this.sanitizeId(baseId)
      
      // Store mapping for edge generation
      idMap.set(node.id, cleanId)
      
      const shape = node.data.shape || (node.type === 'decision' ? 'diamond' : 'rectangle')

      // Choose bracket style based on shape or node type
      let nodeDeclaration: string
      switch (shape) {
        case 'circle':
          nodeDeclaration = `  ${cleanId}(("${cleanLabel}"))`
          break
        case 'rounded':
          nodeDeclaration = `  ${cleanId}("${cleanLabel}")`
          break
        case 'diamond':
          nodeDeclaration = `  ${cleanId}{"${cleanLabel}"}`
          break
        default:
          nodeDeclaration = `  ${cleanId}["${cleanLabel}"]`
      }

      mermaid += nodeDeclaration + '\n'

      // Add color styling if requested
      if (options?.includeStyles && node.data.color) {
        mermaid += `  style ${cleanId} fill:${node.data.color},stroke:#333,stroke-width:2px\n`
      }
    }

    mermaid += '\n'

    // Add edges using the ID map
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

    // Accept both "graph" and "flowchart"
    if (!mermaidCode.includes('graph') && !mermaidCode.includes('flowchart')) {
      errors.push('Missing "graph" or "flowchart" declaration')
    }

    // Check for unclosed brackets
    const openBrackets = (mermaidCode.match(/\[/g) || []).length
    const closeBrackets = (mermaidCode.match(/\]/g) || []).length
    if (openBrackets !== closeBrackets) {
      errors.push('Mismatched square brackets')
    }

    return {
      valid: errors.length === 0,
      errors,
    }
  }

  getDefaultNodeType(): string {
    return 'custom'
  }

  getDefaultEdgeType(): string {
    return 'default'
  }

  /**
   * Calculate flowchart layout based on direction
   */
  private calculateFlowLayout(
    nodeCount: number,
    direction: string
  ): Array<{ x: number; y: number }> {
    const positions: Array<{ x: number; y: number }> = []
    const spacing = 250

    if (direction === 'TD' || direction === 'BT') {
      // Vertical flow
      for (let i = 0; i < nodeCount; i++) {
        positions.push({
          x: 300,
          y: i * spacing + 100,
        })
      }
    } else {
      // Horizontal flow (LR, RL)
      for (let i = 0; i < nodeCount; i++) {
        positions.push({
          x: i * spacing + 100,
          y: 300,
        })
      }
    }

    return positions
  }

  /**
   * Assign colors based on node label/type
   */
  private getColorForNodeType(label: string): string {
    const lowerLabel = label.toLowerCase()

    if (lowerLabel.includes('start') || lowerLabel.includes('begin')) {
      return '#22c55e' // green
    }
    if (lowerLabel.includes('end') || lowerLabel.includes('finish') || lowerLabel.includes('stop')) {
      return '#ef4444' // red
    }
    if (lowerLabel.includes('decision') || lowerLabel.includes('if') || lowerLabel.includes('?')) {
      return '#eab308' // yellow
    }
    if (lowerLabel.includes('process') || lowerLabel.includes('calculate')) {
      return '#3b82f6' // blue
    }
    if (lowerLabel.includes('data') || lowerLabel.includes('input') || lowerLabel.includes('output')) {
      return '#06b6d4' // cyan
    }

    return '#6366f1' // default indigo
  }
}

