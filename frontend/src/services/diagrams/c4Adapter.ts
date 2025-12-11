/**
 * C4 Model Diagram Adapter
 * Parses Mermaid C4 diagram syntax to React Flow format
 * Supports: C4Context, C4Container, C4Component, C4Deployment
 */

import { BaseDiagramAdapter } from './baseDiagramAdapter'
import type { ReactFlowNode, ReactFlowEdge } from '../diagramService'

type C4ElementType = 'Person' | 'System' | 'Container' | 'Component' | 'SystemDb' | 'ContainerDb' | 'Node' | 'Boundary'

interface C4Element {
  id: string
  type: C4ElementType
  label: string
  description?: string
  technology?: string
  parentBoundary?: string
}

export class C4Adapter extends BaseDiagramAdapter {
  /**
   * Parse Mermaid C4 diagram to React Flow nodes/edges
   */
  parseFromMermaid(mermaidCode: string): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    const elements: C4Element[] = []
    
    const lines = mermaidCode.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('%%'))
    
    let currentBoundary: string | undefined
    let yOffset = 0
    let xOffset = 0
    
    for (const line of lines) {
      // Skip diagram declaration
      if (line.match(/^C4(Context|Container|Component|Deployment|Dynamic)$/i)) continue
      if (line.startsWith('title')) continue
      if (line.startsWith('LAYOUT_')) continue
      if (line === '}') {
        currentBoundary = undefined
        continue
      }
      
      // Boundary: System_Boundary(id, "label") { or Enterprise_Boundary, Container_Boundary
      const boundaryMatch = line.match(/^(System_Boundary|Enterprise_Boundary|Container_Boundary|Boundary)\s*\(\s*(\w+)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?\s*\)\s*\{?$/i)
      if (boundaryMatch) {
        const [, boundaryType, id, label, description] = boundaryMatch
        currentBoundary = id
        elements.push({
          id,
          type: 'Boundary',
          label,
          description,
        })
        
        nodes.push({
          id,
          type: 'default',
          data: {
            label: `📦 ${label}`,
            color: '#6366f1',
            isBoundary: true,
            description,
          },
          position: { x: xOffset, y: yOffset },
        })
        yOffset += 80
        continue
      }
      
      // Person: Person(id, "label", "description")
      const personMatch = line.match(/^Person(?:_Ext)?\s*\(\s*(\w+)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?\s*\)$/i)
      if (personMatch) {
        const [, id, label, description] = personMatch
        elements.push({ id, type: 'Person', label, description, parentBoundary: currentBoundary })
        
        nodes.push({
          id,
          type: 'default',
          data: {
            label: `👤 ${label}`,
            color: '#0ea5e9',
            c4Type: 'Person',
            description,
          },
          position: { x: xOffset, y: yOffset },
        })
        xOffset += 200
        if (xOffset > 600) { xOffset = 0; yOffset += 100 }
        continue
      }
      
      // System: System(id, "label", "description") or System_Ext
      const systemMatch = line.match(/^System(?:_Ext|Db|_Db)?\s*\(\s*(\w+)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?\s*\)$/i)
      if (systemMatch) {
        const [fullMatch, id, label, description] = systemMatch
        const isDb = fullMatch.includes('Db')
        const type: C4ElementType = isDb ? 'SystemDb' : 'System'
        elements.push({ id, type, label, description, parentBoundary: currentBoundary })
        
        nodes.push({
          id,
          type: 'default',
          data: {
            label: `${isDb ? '🗄️' : '📱'} ${label}`,
            color: isDb ? '#f59e0b' : '#10b981',
            c4Type: type,
            description,
          },
          position: { x: xOffset, y: yOffset },
        })
        xOffset += 200
        if (xOffset > 600) { xOffset = 0; yOffset += 100 }
        continue
      }
      
      // Container: Container(id, "label", "technology", "description")
      const containerMatch = line.match(/^Container(?:_Ext|Db|_Db)?\s*\(\s*(\w+)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?(?:\s*,\s*"([^"]*)")?\s*\)$/i)
      if (containerMatch) {
        const [fullMatch, id, label, technology, description] = containerMatch
        const isDb = fullMatch.includes('Db')
        const type: C4ElementType = isDb ? 'ContainerDb' : 'Container'
        elements.push({ id, type, label, description, technology, parentBoundary: currentBoundary })
        
        nodes.push({
          id,
          type: 'default',
          data: {
            label: `${isDb ? '🗄️' : '📦'} ${label}${technology ? `\n[${technology}]` : ''}`,
            color: isDb ? '#f59e0b' : '#3b82f6',
            c4Type: type,
            technology,
            description,
          },
          position: { x: xOffset, y: yOffset },
        })
        xOffset += 200
        if (xOffset > 600) { xOffset = 0; yOffset += 100 }
        continue
      }
      
      // Component: Component(id, "label", "technology", "description")
      const componentMatch = line.match(/^Component(?:Db|_Db)?\s*\(\s*(\w+)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?(?:\s*,\s*"([^"]*)")?\s*\)$/i)
      if (componentMatch) {
        const [fullMatch, id, label, technology, description] = componentMatch
        const isDb = fullMatch.includes('Db')
        const type: C4ElementType = isDb ? 'ContainerDb' : 'Component'
        elements.push({ id, type, label, description, technology, parentBoundary: currentBoundary })
        
        nodes.push({
          id,
          type: 'default',
          data: {
            label: `⚙️ ${label}${technology ? `\n[${technology}]` : ''}`,
            color: '#8b5cf6',
            c4Type: type,
            technology,
            description,
          },
          position: { x: xOffset, y: yOffset },
        })
        xOffset += 200
        if (xOffset > 600) { xOffset = 0; yOffset += 100 }
        continue
      }
      
      // Relationship: Rel(from, to, "label", "technology")
      const relMatch = line.match(/^(?:Rel|BiRel|Rel_U|Rel_D|Rel_L|Rel_R|Rel_Back)\s*\(\s*(\w+)\s*,\s*(\w+)\s*,\s*"([^"]+)"(?:\s*,\s*"([^"]*)")?\s*\)$/i)
      if (relMatch) {
        const [, from, to, label, technology] = relMatch
        edges.push({
          id: `${from}-${to}-${edges.length}`,
          source: from,
          target: to,
          type: 'smoothstep',
          label: technology ? `${label}\n[${technology}]` : label,
          animated: true,
        })
        continue
      }
    }
    
    return { nodes, edges }
  }

  /**
   * Generate Mermaid C4 diagram from React Flow nodes/edges
   */
  generateMermaid(nodes: ReactFlowNode[], edges: ReactFlowEdge[]): string {
    const lines: string[] = ['C4Context', '    title C4 Context Diagram', '']
    
    // Group by boundaries
    const boundaries: Record<string, ReactFlowNode[]> = { _none_: [] }
    
    for (const node of nodes) {
      if (node.data?.isBoundary) {
        boundaries[node.id] = []
      }
    }
    
    for (const node of nodes) {
      if (node.data?.isBoundary) continue
      const boundary = node.data?.parentBoundary || '_none_'
      if (!boundaries[boundary]) boundaries[boundary] = []
      boundaries[boundary].push(node)
    }
    
    // Generate elements
    for (const node of boundaries._none_ || []) {
      const type = node.data?.c4Type || 'System'
      const label = (node.data?.label || node.id).replace(/^[📱🗄️👤📦⚙️]\s*/, '')
      const desc = node.data?.description || ''
      
      if (type === 'Person') {
        lines.push(`    Person(${node.id}, "${label}", "${desc}")`)
      } else if (type === 'SystemDb') {
        lines.push(`    SystemDb(${node.id}, "${label}", "${desc}")`)
      } else {
        lines.push(`    System(${node.id}, "${label}", "${desc}")`)
      }
    }
    
    // Generate boundaries with their contents
    for (const [boundaryId, boundaryNodes] of Object.entries(boundaries)) {
      if (boundaryId === '_none_') continue
      
      const boundaryNode = nodes.find(n => n.id === boundaryId)
      const boundaryLabel = (boundaryNode?.data?.label || boundaryId).replace(/^📦\s*/, '')
      
      lines.push('')
      lines.push(`    System_Boundary(${boundaryId}, "${boundaryLabel}") {`)
      
      for (const node of boundaryNodes) {
        const type = node.data?.c4Type || 'Container'
        const label = (node.data?.label || node.id).replace(/^[📱🗄️👤📦⚙️]\s*/, '').split('\n')[0]
        const tech = node.data?.technology || ''
        const desc = node.data?.description || ''
        
        if (type === 'ContainerDb') {
          lines.push(`        ContainerDb(${node.id}, "${label}", "${tech}", "${desc}")`)
        } else {
          lines.push(`        Container(${node.id}, "${label}", "${tech}", "${desc}")`)
        }
      }
      
      lines.push('    }')
    }
    
    // Generate relationships
    if (edges.length > 0) {
      lines.push('')
      for (const edge of edges) {
        const label = (edge.label || 'uses').toString().split('\n')[0]
        lines.push(`    Rel(${edge.source}, ${edge.target}, "${label}")`)
      }
    }
    
    return lines.join('\n')
  }

  /**
   * Clean Mermaid code
   */
  cleanMermaidCode(code: string): string {
    const match = code.match(/C4(Context|Container|Component|Deployment|Dynamic)[\s\S]*?(?=```|$)/i)
    if (match) {
      return match[0].trim()
    }
    
    const cleaned = code
      .replace(/```mermaid\s*/gi, '')
      .replace(/```\s*/g, '')
      .trim()
    
    return cleaned
  }
}

