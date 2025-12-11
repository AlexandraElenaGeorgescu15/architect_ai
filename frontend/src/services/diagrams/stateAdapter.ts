/**
 * State Diagram Adapter
 * Parses Mermaid state diagram syntax to React Flow format
 */

import { BaseDiagramAdapter } from './baseDiagramAdapter'
import type { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class StateAdapter extends BaseDiagramAdapter {
  /**
   * Parse Mermaid state diagram to React Flow nodes/edges
   */
  parseFromMermaid(mermaidCode: string): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    const seenNodes = new Set<string>()
    
    const lines = mermaidCode.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('%%'))
    
    let yOffset = 0
    let xOffset = 0
    
    for (const line of lines) {
      // Skip diagram declaration
      if (line.startsWith('stateDiagram') || line.startsWith('state-v2')) continue
      if (line.startsWith('direction')) continue
      
      // State definition with description: state "Description" as StateId
      const stateDefMatch = line.match(/^state\s+"([^"]+)"\s+as\s+(\w+)$/i)
      if (stateDefMatch) {
        const [, description, stateId] = stateDefMatch
        if (!seenNodes.has(stateId)) {
          seenNodes.add(stateId)
          nodes.push({
            id: stateId,
            type: 'default',
            data: {
              label: description,
              color: '#8b5cf6',
            },
            position: { x: xOffset, y: yOffset },
          })
          xOffset += 200
          if (xOffset > 600) {
            xOffset = 0
            yOffset += 100
          }
        }
        continue
      }
      
      // Transition: State1 --> State2 : label
      const transitionMatch = line.match(/^(\[?\*?\]?|\w+)\s*-->\s*(\[?\*?\]?|\w+)(?:\s*:\s*(.+))?$/)
      if (transitionMatch) {
        let [, source, target, label] = transitionMatch
        
        // Handle special states
        if (source === '[*]') source = '_start_'
        if (target === '[*]') target = '_end_'
        
        // Add source node if not seen
        if (!seenNodes.has(source)) {
          seenNodes.add(source)
          const isSpecial = source === '_start_' || source === '_end_'
          nodes.push({
            id: source,
            type: 'default',
            data: {
              label: source === '_start_' ? '●' : source === '_end_' ? '◉' : source,
              color: isSpecial ? '#1f2937' : '#8b5cf6',
              isStart: source === '_start_',
              isEnd: source === '_end_',
            },
            position: { x: xOffset, y: yOffset },
          })
          xOffset += 200
          if (xOffset > 600) {
            xOffset = 0
            yOffset += 100
          }
        }
        
        // Add target node if not seen
        if (!seenNodes.has(target)) {
          seenNodes.add(target)
          const isSpecial = target === '_start_' || target === '_end_'
          nodes.push({
            id: target,
            type: 'default',
            data: {
              label: target === '_start_' ? '●' : target === '_end_' ? '◉' : target,
              color: isSpecial ? '#1f2937' : '#8b5cf6',
              isStart: target === '_start_',
              isEnd: target === '_end_',
            },
            position: { x: xOffset, y: yOffset },
          })
          xOffset += 200
          if (xOffset > 600) {
            xOffset = 0
            yOffset += 100
          }
        }
        
        // Add edge
        edges.push({
          id: `${source}-${target}-${edges.length}`,
          source,
          target,
          type: 'smoothstep',
          label: label?.trim() || undefined,
          animated: source === '_start_',
        })
        continue
      }
      
      // Simple state declaration: state StateId
      const simpleStateMatch = line.match(/^state\s+(\w+)$/i)
      if (simpleStateMatch) {
        const stateId = simpleStateMatch[1]
        if (!seenNodes.has(stateId)) {
          seenNodes.add(stateId)
          nodes.push({
            id: stateId,
            type: 'default',
            data: {
              label: stateId,
              color: '#8b5cf6',
            },
            position: { x: xOffset, y: yOffset },
          })
          xOffset += 200
          if (xOffset > 600) {
            xOffset = 0
            yOffset += 100
          }
        }
      }
    }
    
    return { nodes, edges }
  }

  /**
   * Generate Mermaid state diagram from React Flow nodes/edges
   */
  generateMermaid(nodes: ReactFlowNode[], edges: ReactFlowEdge[]): string {
    const lines: string[] = ['stateDiagram-v2', '    direction LR', '']
    
    // Generate state definitions
    for (const node of nodes) {
      if (node.data?.isStart || node.data?.isEnd) continue
      
      const label = node.data?.label || node.id
      if (label !== node.id) {
        lines.push(`    state "${label}" as ${node.id}`)
      }
    }
    
    if (nodes.some(n => !n.data?.isStart && !n.data?.isEnd && n.data?.label !== n.id)) {
      lines.push('')
    }
    
    // Generate transitions
    for (const edge of edges) {
      let source = edge.source
      let target = edge.target
      
      // Convert special states back
      if (source === '_start_') source = '[*]'
      if (target === '_end_') target = '[*]'
      
      const label = edge.label ? ` : ${edge.label}` : ''
      lines.push(`    ${source} --> ${target}${label}`)
    }
    
    return lines.join('\n')
  }

  /**
   * Clean Mermaid code
   */
  cleanMermaidCode(code: string): string {
    const match = code.match(/stateDiagram[\s\S]*?(?=```|$)/i)
    if (match) {
      return match[0].trim()
    }
    
    const cleaned = code
      .replace(/```mermaid\s*/gi, '')
      .replace(/```\s*/g, '')
      .trim()
    
    if (!cleaned.toLowerCase().startsWith('statediagram')) {
      return `stateDiagram-v2\n${cleaned}`
    }
    
    return cleaned
  }
}

