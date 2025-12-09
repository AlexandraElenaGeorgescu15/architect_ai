/**
 * ERD (Entity-Relationship Diagram) Adapter
 * Handles Mermaid ERD diagrams
 */

import { BaseDiagramAdapter, DiagramParseResult, MermaidGenerateOptions } from './baseDiagramAdapter'
import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class ERDAdapter extends BaseDiagramAdapter {
  /**
   * Clean and extract pure Mermaid ERD code from content that may contain explanations
   */
  cleanMermaidCode(rawContent: string): string {
    let content = rawContent.trim()
    
    // Try to extract from markdown code blocks first
    const codeBlockMatch = content.match(/```(?:mermaid)?\s*\n([\s\S]*?)```/)
    if (codeBlockMatch) {
      content = codeBlockMatch[1].trim()
    }
    
    // Find where erDiagram starts
    const erdIndex = content.indexOf('erDiagram')
    if (erdIndex === -1) return content
    
    content = content.substring(erdIndex)
    
    // Remove CLASS prefix from entity definitions (common LLM mistake)
    // Convert: CLASS USER { ... } to: USER { ... }
    content = content.replace(/\bCLASS\s+(\w+)\s*\{/gi, '$1 {')
    content = content.replace(/\bclass\s+(\w+)\s*\{/gi, '$1 {')
    
    // Convert property format from "- field (description)" to "type field"
    content = content.replace(/-\s*(\w+)\s*\(([^)]*primary key[^)]*)\)/gi, 'int $1 PK')
    content = content.replace(/-\s*(\w+)\s*\(([^)]*foreign key[^)]*)\)/gi, 'int $1 FK')
    content = content.replace(/-\s*(\w+)\s*\([^)]*\)/gi, 'string $1')
    content = content.replace(/-\s*(\w+)\s*$/gm, 'string $1')
    
    // Remove trailing explanatory text
    const lines = content.split('\n')
    const cleanLines: string[] = []
    let inEntity = false
    let braceCount = 0
    
    for (const line of lines) {
      const trimmed = line.trim()
      
      // Track brace nesting
      braceCount += (line.match(/\{/g) || []).length
      braceCount -= (line.match(/\}/g) || []).length
      
      // Stop at explanatory text (outside of entities)
      if (braceCount === 0 && (
        trimmed.startsWith('**') ||
        trimmed.startsWith('This ERD') ||
        trimmed.startsWith('The ') ||
        trimmed.match(/^\d+\./) ||
        trimmed.startsWith('Explanation') ||
        trimmed.startsWith('Note:')
      )) {
        break
      }
      
      // Include diagram content
      if (trimmed.startsWith('erDiagram') || 
          trimmed.match(/^\w+\s*\{/) ||
          trimmed.match(/^\w+\s+\w+/) ||  // property line
          trimmed === '}' ||
          trimmed.match(/\w+\s*\|.*\|.*\w+/) ||  // relationship line
          braceCount > 0 ||
          trimmed === ''
      ) {
        cleanLines.push(line)
      }
    }
    
    return cleanLines.join('\n').trim()
  }

  parseFromMermaid(mermaidCode: string): DiagramParseResult {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []

    // Clean the code first
    const cleanCode = this.cleanMermaidCode(mermaidCode)

    // Extract entities with properties
    // Match: EntityName { ... } (handles both standard and converted CLASS syntax)
    const entityRegex = /^[ \t]*(\w+)\s*\{([^}]*)\}/gms
    const entityMatches = cleanCode.matchAll(entityRegex)

    const entityMap = new Map<string, { properties: string[] }>()

    for (const match of entityMatches) {
      let entityName = match[1].trim()
      
      // Skip if it's a keyword like erDiagram
      if (entityName.toLowerCase() === 'erdiagram') continue
      
      const propertiesBlock = match[2]

      // Extract properties (type propertyName or propertyName type)
      const properties: string[] = []
      const propLines = propertiesBlock.split('\n')
      
      for (const propLine of propLines) {
        const trimmed = propLine.trim()
        if (!trimmed) continue
        
        // Handle various formats:
        // "int id PK" or "string name" or "id int" or "- id (primary key)"
        const standardMatch = trimmed.match(/^(\w+)\s+(\w+)(?:\s+(PK|FK))?$/)
        if (standardMatch) {
          const pk = standardMatch[3] ? ` ${standardMatch[3]}` : ''
          properties.push(`${standardMatch[1]} ${standardMatch[2]}${pk}`)
        } else {
          // Fallback: just use the line as-is if it looks like a property
          const simpleMatch = trimmed.match(/^[\w\s]+$/)
          if (simpleMatch) {
            properties.push(trimmed)
          }
        }
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
    // Mermaid ERD relationship format: Entity1 ||--o{ Entity2 : "label"
    // Cardinality: || (exactly one), |o (zero or one), }| (one or more), }o (zero or more)
    const relationshipRegex = /(\w+)\s*(\|\||\|o|\}o|\}\|)--(\|\||\|o|o\{|\{)?\s*(\w+)\s*:\s*"?([^"\n]*)"?/g
    const altRelRegex = /(\w+)\s*\|\|--o\{\s*(\w+)\s*:\s*"?([^"\n]*)"?/g
    const altRelRegex2 = /(\w+)\s*\|\|--\|\{\s*(\w+)\s*:\s*"?([^"\n]*)"?/g
    
    let edgeIndex = 0
    
    // Try standard format first
    for (const match of cleanCode.matchAll(relationshipRegex)) {
      const from = match[1]
      const fromCard = match[2]
      const toCard = match[3] || ''
      const to = match[4]
      const label = match[5]?.trim()

      // Determine relationship type
      let relationType = 'one-to-one'
      if (toCard.includes('{') || toCard.includes('o{')) {
        relationType = 'one-to-many'
      } else if (fromCard.includes('}')) {
        relationType = 'many-to-one'
      }

      edges.push({
        id: `rel_${edgeIndex++}`,
        source: from,
        target: to,
        label,
        type: 'relationship',
        data: { relationType },
      } as any)
    }
    
    // Try alternate format: ||--o{
    for (const match of cleanCode.matchAll(altRelRegex)) {
      const from = match[1]
      const to = match[2]
      const label = match[3]?.trim()
      
      // Check if we already have this edge
      const exists = edges.some(e => e.source === from && e.target === to)
      if (!exists) {
        edges.push({
          id: `rel_${edgeIndex++}`,
          source: from,
          target: to,
          label,
          type: 'relationship',
          data: { relationType: 'one-to-many' },
        } as any)
      }
    }
    
    // Try alternate format: ||--|{
    for (const match of cleanCode.matchAll(altRelRegex2)) {
      const from = match[1]
      const to = match[2]
      const label = match[3]?.trim()
      
      const exists = edges.some(e => e.source === from && e.target === to)
      if (!exists) {
        edges.push({
          id: `rel_${edgeIndex++}`,
          source: from,
          target: to,
          label,
          type: 'relationship',
          data: { relationType: 'one-to-many' },
        } as any)
      }
    }

    return { nodes, edges }
  }

  generateMermaid(
    nodes: ReactFlowNode[],
    edges: ReactFlowEdge[],
    options?: MermaidGenerateOptions
  ): string {
    if (nodes.length === 0) {
      return 'erDiagram\n  User {\n    int id PK\n    string name\n  }'
    }

    let mermaid = 'erDiagram\n'

    // Create a map from internal node.id to the entity name used in Mermaid
    const idToEntityMap = new Map<string, string>()

    // Add entities with properties
    for (const node of nodes) {
      // Use label as entity name if it looks like a valid identifier, otherwise use sanitized id
      const label = node.data.label || node.id
      const entityName = this.sanitizeId(label.replace(/\s+/g, '_'))
      
      // Store mapping from internal ID to entity name
      idToEntityMap.set(node.id, entityName)
      
      mermaid += `  ${entityName} {\n`

      const properties = node.data.properties as string[] || []
      for (const prop of properties) {
        // Normalize property format to "type name [PK|FK]"
        const normalizedProp = this.normalizeProperty(prop)
        mermaid += `    ${normalizedProp}\n`
      }

      // If no properties, add a placeholder
      if (properties.length === 0) {
        mermaid += `    int id PK\n`
      }

      mermaid += '  }\n'
    }

    mermaid += '\n'

    // Add relationships using the ID map to get proper entity names
    for (const edge of edges) {
      // Look up entity names from the map, fall back to sanitized ID if not found
      const from = idToEntityMap.get(edge.source) || this.sanitizeId(edge.source)
      const to = idToEntityMap.get(edge.target) || this.sanitizeId(edge.target)
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
   * Normalize property format to "type name [PK|FK]"
   */
  private normalizeProperty(prop: string): string {
    const trimmed = prop.trim()
    
    // Already in correct format: "type name" or "type name PK/FK"
    if (trimmed.match(/^\w+\s+\w+(\s+(PK|FK))?$/)) {
      return trimmed
    }
    
    // Handle "name (PK)" or "name (primary key)" format
    const pkMatch = trimmed.match(/^(\w+)\s*\((.*primary.*key.*|PK)\)$/i)
    if (pkMatch) {
      return `int ${pkMatch[1]} PK`
    }
    
    // Handle "name (FK)" or "name (foreign key)" format
    const fkMatch = trimmed.match(/^(\w+)\s*\((.*foreign.*key.*|FK)\)$/i)
    if (fkMatch) {
      return `int ${fkMatch[1]} FK`
    }
    
    // Handle "name (type)" format
    const typeMatch = trimmed.match(/^(\w+)\s*\((\w+)\)$/)
    if (typeMatch) {
      return `${typeMatch[2]} ${typeMatch[1]}`
    }
    
    // Just a name - default to string type
    if (trimmed.match(/^\w+$/)) {
      return `string ${trimmed}`
    }
    
    // Fallback: return as-is
    return trimmed
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

