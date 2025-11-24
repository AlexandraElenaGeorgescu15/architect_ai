/**
 * ERD (Entity-Relationship Diagram) Adapter
 * Handles Mermaid ERD diagrams
 */

import { BaseDiagramAdapter, DiagramParseResult, MermaidGenerateOptions } from './baseDiagramAdapter'
import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class ERDAdapter extends BaseDiagramAdapter {
  parseFromMermaid(mermaidCode: string): DiagramParseResult {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []

    // Extract entities with properties
    const entityRegex = /(\w+)\s*\{([^}]*)\}/gs
    const entityMatches = mermaidCode.matchAll(entityRegex)

    const entityMap = new Map<string, { properties: string[] }>()

    for (const match of entityMatches) {
      const entityName = match[1]
      const propertiesBlock = match[2]

      // Extract properties (type propertyName)
      const properties: string[] = []
      const propMatches = propertiesBlock.matchAll(/(\w+)\s+(\w+)/g)
      for (const propMatch of propMatches) {
        properties.push(`${propMatch[1]} ${propMatch[2]}`)
      }

      entityMap.set(entityName, { properties })
    }

    // Calculate layout (grid)
    const positions = this.calculateLayout(entityMap.size, 350)

    // Create nodes
    let index = 0
    for (const [entityName, { properties }] of entityMap.entries()) {
      const color = this.getColorForEntity(entityName)
      nodes.push({
        id: entityName,
        type: 'entity',
        data: {
          label: entityName,
          properties,
          color,
        },
        position: positions[index] || { x: 0, y: 0 },
      })
      index++
    }

    // Extract relationships
    // Format: EntityA ||--o{ EntityB : "relationship"
    const relationshipRegex = /(\w+)\s*\|([o-])\|(--)?\|([o-])\|\s*(\w+)\s*:\s*"?([^"\n]*)"?/g
    const relationshipMatches = mermaidCode.matchAll(relationshipRegex)

    let edgeIndex = 0
    for (const match of relationshipMatches) {
      const from = match[1]
      const fromCardinality = match[2]
      const to = match[5]
      const toCardinality = match[4]
      const label = match[6]?.trim()

      // Determine relationship type based on cardinality
      let relationType = 'one-to-one'
      if (fromCardinality === 'o' && toCardinality === '{') {
        relationType = 'one-to-many'
      } else if (fromCardinality === '{' && toCardinality === '{') {
        relationType = 'many-to-many'
      } else if (fromCardinality === '{' && toCardinality === 'o') {
        relationType = 'many-to-one'
      }

      edges.push({
        id: `rel_${edgeIndex++}`,
        source: from,
        target: to,
        label,
        type: 'relationship',
        data: {
          relationType,
          fromCardinality,
          toCardinality,
        },
      } as any)
    }

    return { nodes, edges }
  }

  generateMermaid(
    nodes: ReactFlowNode[],
    edges: ReactFlowEdge[],
    options?: MermaidGenerateOptions
  ): string {
    if (nodes.length === 0) {
      return 'erDiagram\n  User {\n    int id\n    string name\n  }'
    }

    let mermaid = 'erDiagram\n'

    // Add entities with properties
    for (const node of nodes) {
      const entityName = this.sanitizeId(node.id)
      mermaid += `  ${entityName} {\n`

      const properties = node.data.properties as string[] || []
      for (const prop of properties) {
        mermaid += `    ${prop}\n`
      }

      mermaid += '  }\n'
    }

    mermaid += '\n'

    // Add relationships
    for (const edge of edges) {
      const from = this.sanitizeId(edge.source)
      const to = this.sanitizeId(edge.target)
      const label = edge.label ? `"${this.sanitizeLabel(edge.label)}"` : '""'

      // Determine cardinality notation
      const edgeData = (edge as any).data || {}
      const relationType = edgeData.relationType || 'one-to-one'

      let notation: string
      switch (relationType) {
        case 'one-to-many':
          notation = '||--o{'
          break
        case 'many-to-one':
          notation = '}o--||'
          break
        case 'many-to-many':
          notation = '}o--o{'
          break
        default:
          notation = '||--||'
      }

      mermaid += `  ${from} ${notation} ${to} : ${label}\n`
    }

    return mermaid
  }

  validate(mermaidCode: string): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!mermaidCode.includes('erDiagram')) {
      errors.push('Missing "erDiagram" declaration')
    }

    // Check for entity syntax
    if (!mermaidCode.match(/\w+\s*\{[^}]*\}/)) {
      errors.push('No entities found. Entities should be in format: EntityName { ... }')
    }

    return {
      valid: errors.length === 0,
      errors,
    }
  }

  getDefaultNodeType(): string {
    return 'entity'
  }

  getDefaultEdgeType(): string {
    return 'relationship'
  }

  /**
   * Assign colors based on entity name/domain
   */
  private getColorForEntity(entityName: string): string {
    const lowerName = entityName.toLowerCase()

    // User-related entities
    if (lowerName.includes('user') || lowerName.includes('account') || lowerName.includes('profile')) {
      return '#3b82f6' // blue
    }

    // Order/Transaction entities
    if (lowerName.includes('order') || lowerName.includes('transaction') || lowerName.includes('payment')) {
      return '#22c55e' // green
    }

    // Product/Item entities
    if (lowerName.includes('product') || lowerName.includes('item') || lowerName.includes('inventory')) {
      return '#f97316' // orange
    }

    // Auth/Security entities
    if (lowerName.includes('auth') || lowerName.includes('token') || lowerName.includes('session')) {
      return '#a855f7' // purple
    }

    // Audit/Log entities
    if (lowerName.includes('log') || lowerName.includes('audit') || lowerName.includes('history')) {
      return '#64748b' // slate
    }

    return '#6366f1' // default indigo
  }
}

