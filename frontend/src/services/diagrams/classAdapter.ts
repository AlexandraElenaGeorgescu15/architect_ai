/**
 * Class Diagram Adapter
 * Parses Mermaid class diagrams into React Flow nodes/edges and vice versa.
 * Uses the Entity node component so properties/methods are displayed on canvas.
 */

import { BaseDiagramAdapter, DiagramParseResult, MermaidGenerateOptions } from './baseDiagramAdapter'
import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

type RelationshipKind = 'inheritance' | 'composition' | 'aggregation' | 'association'

export class ClassAdapter extends BaseDiagramAdapter {
  parseFromMermaid(mermaidCode: string): DiagramParseResult {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []

    const clean = this.cleanMermaidCode(mermaidCode)

    // Extract classes with body
    const classRegex = /class\s+(\w+)\s*\{([^}]*)\}/gms
    const classes = new Map<string, { properties: string[] }>()

    for (const match of clean.matchAll(classRegex)) {
      const name = match[1]
      const body = match[2]
      const props: string[] = []

      for (const rawLine of body.split('\n')) {
        const line = rawLine.trim()
        if (!line) continue
        // Normalize visibility and method markers by stripping symbols
        const normalized = line.replace(/^[-+~#]/, '').trim()
        props.push(normalized)
      }

      classes.set(name, { properties: props })
    }

    // If no explicit class blocks found, attempt to capture simple declarations: class Foo
    const simpleClassRegex = /^\s*class\s+(\w+)/gm
    for (const match of clean.matchAll(simpleClassRegex)) {
      const name = match[1]
      if (!classes.has(name)) {
        classes.set(name, { properties: [] })
      }
    }

    // Layout positions
    const positions = this.calculateLayout(classes.size, 320)
    let idx = 0
    for (const [name, { properties }] of classes.entries()) {
      nodes.push({
        id: name,
        type: 'entity', // reuse EntityNode to render properties
        data: {
          label: name,
          properties,
          color: this.getColorForClass(name),
        },
        position: positions[idx] || { x: 0, y: 0 },
      })
      idx++
    }

    // Extract relationships
    // Inheritance: Child <|-- Parent
    const relRegex =
      /(\w+)\s*(<\|--|\*--|o--|--)\s*(\w+)(?:\s*:\s*([^\n]+))?/g
    let edgeIndex = 0
    for (const match of clean.matchAll(relRegex)) {
      const from = match[1]
      const arrow = match[2]
      const to = match[3]
      const label = match[4]?.trim()

      const relation = this.mapRelation(arrow)
      edges.push({
        id: `class_rel_${edgeIndex++}`,
        source: from,
        target: to,
        label,
        type: 'relationship',
        data: { relation },
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
      return `classDiagram
  class Example {
    id: int
    name: string
  }`
    }

    let mermaid = 'classDiagram\n'

    const idMap = new Map<string, string>()

    for (const node of nodes) {
      const label = node.data.label || node.id
      const className = this.sanitizeId(label.replace(/\s+/g, '_'))
      idMap.set(node.id, className)

      mermaid += `  class ${className} {\n`
      const props: string[] = (node.data.properties as string[]) || []
      if (props.length === 0) {
        mermaid += '    id: int\n'
      } else {
        for (const prop of props) {
          mermaid += `    ${this.sanitizeLabel(prop)}\n`
        }
      }
      mermaid += '  }\n'

      if (options?.includeStyles && node.data.color) {
        mermaid += `  classDef ${className}_style fill:${node.data.color},stroke:#333,stroke-width:1px;\n`
        mermaid += `  class ${className} ${className}_style;\n`
      }
    }

    mermaid += '\n'

    for (const edge of edges) {
      const source = idMap.get(edge.source) || this.sanitizeId(edge.source)
      const target = idMap.get(edge.target) || this.sanitizeId(edge.target)
      const relation = (edge as any).data?.relation as RelationshipKind | undefined
      const arrow = this.toArrow(relation)
      const label = edge.label ? ` : ${this.sanitizeLabel(edge.label)}` : ''

      mermaid += `  ${source} ${arrow} ${target}${label}\n`
    }

    return mermaid
  }

  validate(mermaidCode: string): { valid: boolean; errors: string[] } {
    const errors: string[] = []
    if (!mermaidCode.includes('classDiagram')) {
      errors.push('Missing "classDiagram" declaration')
    }
    if (!mermaidCode.match(/class\s+\w+/)) {
      errors.push('No classes found. Use "class ClassName { ... }" syntax.')
    }
    return { valid: errors.length === 0, errors }
  }

  getDefaultNodeType(): string {
    return 'entity'
  }

  getDefaultEdgeType(): string {
    return 'relationship'
  }

  private mapRelation(arrow: string): RelationshipKind {
    switch (arrow) {
      case '<|--':
        return 'inheritance'
      case '*--':
        return 'composition'
      case 'o--':
        return 'aggregation'
      default:
        return 'association'
    }
  }

  private toArrow(relation?: RelationshipKind): string {
    switch (relation) {
      case 'inheritance':
        return '<|--'
      case 'composition':
        return '*--'
      case 'aggregation':
        return 'o--'
      default:
        return '--'
    }
  }

  private getColorForClass(name: string): string {
    const lower = name.toLowerCase()
    if (lower.includes('service') || lower.includes('controller')) return '#3b82f6'
    if (lower.includes('repo') || lower.includes('repository')) return '#22c55e'
    if (lower.includes('dto') || lower.includes('model')) return '#a855f7'
    return '#6366f1'
  }
}


