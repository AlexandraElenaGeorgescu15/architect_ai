/**
 * Sequence Diagram Adapter
 * Handles Mermaid sequence diagrams
 */

import { BaseDiagramAdapter, DiagramParseResult, MermaidGenerateOptions } from './baseDiagramAdapter'
import { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class SequenceAdapter extends BaseDiagramAdapter {
  parseFromMermaid(mermaidCode: string): DiagramParseResult {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []

    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/dfc1763a-e24e-49d7-baae-a7a908b307cd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'sequenceAdapter.ts:parseFromMermaid',message:'SequenceAdapter parsing',data:{codeLength:mermaidCode.length,hasSequenceDiagram:mermaidCode.includes('sequenceDiagram'),codePreview:mermaidCode.substring(0,400)},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H5'})}).catch(()=>{});
    // #endregion

    // Extract participants
    const participantRegex = /participant\s+(\w+)(?:\s+as\s+(.+))?/g
    const participantMatches = mermaidCode.matchAll(participantRegex)

    const participants = new Map<string, string>()

    for (const match of participantMatches) {
      const id = match[1]
      const label = match[2]?.trim() || id
      participants.set(id, label)
    }

    // Extract messages (interactions)
    const messageRegex = /(\w+)\s*(->>?|-->>?)\s*(\w+)\s*:\s*([^\n]+)/g
    const messageMatches = mermaidCode.matchAll(messageRegex)

    // Auto-detect participants from messages if not explicitly declared
    for (const match of messageMatches) {
      const from = match[1]
      const to = match[3]
      if (!participants.has(from)) {
        participants.set(from, from)
      }
      if (!participants.has(to)) {
        participants.set(to, to)
      }
    }

    // Create participant nodes (horizontal layout)
    let index = 0
    const horizontalSpacing = 250
    for (const [id, label] of participants.entries()) {
      nodes.push({
        id,
        type: 'participant',
        data: {
          label,
          color: this.getColorForParticipant(label),
        },
        position: {
          x: index * horizontalSpacing + 100,
          y: 100,
        },
      })
      index++
    }

    // Create message edges (vertical flow)
    let messageIndex = 0
    const messageMatchesArray = Array.from(mermaidCode.matchAll(messageRegex))

    for (let i = 0; i < messageMatchesArray.length; i++) {
      const match = messageMatchesArray[i]
      const from = match[1]
      const arrowType = match[2]
      const to = match[3]
      const message = match[4]?.trim()

      // Determine if it's synchronous or asynchronous
      const isAsync = arrowType.includes('--')

      edges.push({
        id: `msg_${messageIndex++}`,
        source: from,
        target: to,
        label: message,
        type: 'message',
        data: {
          messageType: isAsync ? 'async' : 'sync',
          order: i + 1,
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
      return 'sequenceDiagram\n  participant A\n  participant B\n  A->>B: Message'
    }

    let mermaid = 'sequenceDiagram\n'

    // Create a map from internal node.id to the participant ID used in Mermaid
    const idToParticipantMap = new Map<string, string>()

    // Add participants
    for (const node of nodes) {
      const label = node.data.label || node.id
      // Use label as participant ID if it's a valid identifier, otherwise sanitize
      const participantId = label.match(/^[a-zA-Z][a-zA-Z0-9_]*$/)
        ? label
        : this.sanitizeId(label.replace(/\s+/g, '_'))
      const cleanLabel = this.sanitizeLabel(label)
      
      // Store mapping from internal ID to participant ID
      idToParticipantMap.set(node.id, participantId)
      
      if (participantId === cleanLabel) {
        mermaid += `  participant ${participantId}\n`
      } else {
        mermaid += `  participant ${participantId} as ${cleanLabel}\n`
      }
    }

    mermaid += '\n'

    // Sort edges by order if available
    const sortedEdges = [...edges].sort((a, b) => {
      const orderA = (a as any).data?.order || 0
      const orderB = (b as any).data?.order || 0
      return orderA - orderB
    })

    // Add messages using the ID map for proper participant names
    for (const edge of sortedEdges) {
      const from = idToParticipantMap.get(edge.source) || this.sanitizeId(edge.source)
      const to = idToParticipantMap.get(edge.target) || this.sanitizeId(edge.target)
      const message = this.sanitizeLabel(edge.label || 'Message')
      const messageType = (edge as any).data?.messageType || 'sync'

      const arrow = messageType === 'async' ? '-->>' : '->>'

      mermaid += `  ${from}${arrow}${to}: ${message}\n`
    }

    return mermaid
  }

  validate(mermaidCode: string): { valid: boolean; errors: string[] } {
    const errors: string[] = []

    if (!mermaidCode.includes('sequenceDiagram')) {
      errors.push('Missing "sequenceDiagram" declaration')
    }

    // Check for at least one message
    if (!mermaidCode.match(/\w+\s*(->>?|-->>?)\s*\w+/)) {
      errors.push('No messages found. Use format: A->>B: message')
    }

    return {
      valid: errors.length === 0,
      errors,
    }
  }

  getDefaultNodeType(): string {
    return 'participant'
  }

  getDefaultEdgeType(): string {
    return 'message'
  }

  /**
   * Assign colors based on participant role
   */
  private getColorForParticipant(label: string): string {
    const lowerLabel = label.toLowerCase()

    if (lowerLabel.includes('user') || lowerLabel.includes('client')) {
      return '#3b82f6' // blue
    }
    if (lowerLabel.includes('server') || lowerLabel.includes('api')) {
      return '#22c55e' // green
    }
    if (lowerLabel.includes('database') || lowerLabel.includes('db')) {
      return '#f97316' // orange
    }
    if (lowerLabel.includes('cache') || lowerLabel.includes('redis')) {
      return '#ef4444' // red
    }
    if (lowerLabel.includes('queue') || lowerLabel.includes('mq')) {
      return '#a855f7' // purple
    }

    return '#6366f1' // default indigo
  }
}

