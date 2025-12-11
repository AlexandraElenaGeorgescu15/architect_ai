/**
 * Generic Diagram Adapter
 * Fallback adapter for diagram types that don't have specific parsers
 * Supports: pie, journey, mindmap, timeline, git_graph, etc.
 * 
 * This adapter creates a simple visual representation showing
 * the diagram content as nodes, allowing basic canvas interaction.
 */

import { BaseDiagramAdapter } from './baseDiagramAdapter'
import type { ReactFlowNode, ReactFlowEdge } from '../diagramService'

export class GenericAdapter extends BaseDiagramAdapter {
  private diagramType: string

  constructor(diagramType: string = 'generic') {
    super()
    this.diagramType = diagramType
  }

  /**
   * Parse diagram content to a simple node representation
   */
  parseFromMermaid(mermaidCode: string): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    
    const lines = mermaidCode.split('\n')
      .map(l => l.trim())
      .filter(l => l && !l.startsWith('%%') && !l.startsWith('```'))
    
    // Detect diagram type from first line
    const firstLine = lines[0]?.toLowerCase() || ''
    let detectedType = this.diagramType
    
    if (firstLine.startsWith('pie')) detectedType = 'pie'
    else if (firstLine.startsWith('journey')) detectedType = 'journey'
    else if (firstLine.startsWith('mindmap')) detectedType = 'mindmap'
    else if (firstLine.startsWith('timeline')) detectedType = 'timeline'
    else if (firstLine.startsWith('gitgraph') || firstLine.startsWith('git')) detectedType = 'git_graph'
    else if (firstLine.startsWith('quadrant')) detectedType = 'quadrant'
    else if (firstLine.startsWith('requirementdiagram') || firstLine.startsWith('requirement')) detectedType = 'requirement'
    
    // Create appropriate visualization based on type
    switch (detectedType) {
      case 'pie':
        return this.parsePieChart(lines)
      case 'journey':
        return this.parseJourney(lines)
      case 'mindmap':
        return this.parseMindmap(lines)
      case 'timeline':
        return this.parseTimeline(lines)
      case 'git_graph':
        return this.parseGitGraph(lines)
      default:
        return this.parseGeneric(lines, detectedType)
    }
  }

  private parsePieChart(lines: string[]): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    let yOffset = 0
    
    // Add title node
    const titleLine = lines.find(l => l.toLowerCase().startsWith('title'))
    if (titleLine) {
      nodes.push({
        id: 'pie_title',
        type: 'default',
        data: { label: `🥧 ${titleLine.replace(/^title\s*/i, '')}`, color: '#f59e0b' },
        position: { x: 200, y: yOffset },
      })
      yOffset += 80
    }
    
    // Parse pie sections
    for (const line of lines) {
      if (line.toLowerCase().startsWith('pie') || line.toLowerCase().startsWith('title')) continue
      
      // Match: "Label" : value
      const match = line.match(/^"([^"]+)"\s*:\s*([\d.]+)$/)
      if (match) {
        const [, label, value] = match
        nodes.push({
          id: `pie_${nodes.length}`,
          type: 'default',
          data: {
            label: `${label}: ${value}%`,
            color: this.getColorForIndex(nodes.length),
          },
          position: { x: 100 + (nodes.length % 2) * 250, y: yOffset },
        })
        if (nodes.length % 2 === 0) yOffset += 70
      }
    }
    
    return { nodes, edges: [] }
  }

  private parseJourney(lines: string[]): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    let yOffset = 0
    let currentSection = ''
    let lastNodeId = ''
    
    for (const line of lines) {
      if (line.toLowerCase().startsWith('journey')) continue
      
      // Title
      if (line.toLowerCase().startsWith('title')) {
        nodes.push({
          id: 'journey_title',
          type: 'default',
          data: { label: `🗺️ ${line.replace(/^title\s*/i, '')}`, color: '#0ea5e9' },
          position: { x: 200, y: yOffset },
        })
        yOffset += 80
        continue
      }
      
      // Section
      if (line.toLowerCase().startsWith('section')) {
        currentSection = line.replace(/^section\s*/i, '')
        const nodeId = `section_${nodes.length}`
        nodes.push({
          id: nodeId,
          type: 'default',
          data: { label: `📋 ${currentSection}`, color: '#6366f1', isSection: true },
          position: { x: 50, y: yOffset },
        })
        if (lastNodeId) {
          edges.push({ id: `${lastNodeId}-${nodeId}`, source: lastNodeId, target: nodeId, type: 'smoothstep' })
        }
        lastNodeId = nodeId
        yOffset += 60
        continue
      }
      
      // Task: TaskName: score: actor1, actor2
      const taskMatch = line.match(/^([^:]+):\s*(\d+)(?:\s*:\s*(.+))?$/)
      if (taskMatch) {
        const [, taskName, score, actors] = taskMatch
        const nodeId = `task_${nodes.length}`
        
        // Color based on score (1-5)
        const scoreNum = parseInt(score)
        const color = scoreNum >= 4 ? '#22c55e' : scoreNum >= 3 ? '#f59e0b' : '#ef4444'
        
        nodes.push({
          id: nodeId,
          type: 'default',
          data: {
            label: `${taskName} (${score}/5)${actors ? `\n👤 ${actors}` : ''}`,
            color,
            score: scoreNum,
          },
          position: { x: 200, y: yOffset },
        })
        
        if (lastNodeId) {
          edges.push({ id: `${lastNodeId}-${nodeId}`, source: lastNodeId, target: nodeId, type: 'smoothstep' })
        }
        lastNodeId = nodeId
        yOffset += 60
      }
    }
    
    return { nodes, edges }
  }

  private parseMindmap(lines: string[]): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    
    let rootId = ''
    const nodeStack: { id: string; indent: number }[] = []
    let yOffset = 0
    
    for (const line of lines) {
      if (line.toLowerCase().startsWith('mindmap')) continue
      
      // Count indentation (spaces or tabs)
      const indentMatch = line.match(/^(\s*)(.+)$/)
      if (!indentMatch) continue
      
      const [, indent, content] = indentMatch
      const indentLevel = indent.length
      const nodeId = `mm_${nodes.length}`
      const label = content.replace(/^[\(\)\[\]\{\}]|[\(\)\[\]\{\}]$/g, '').trim()
      
      // Determine color based on depth
      const depth = nodeStack.filter(n => n.indent < indentLevel).length
      const colors = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#22c55e']
      const color = colors[depth % colors.length]
      
      nodes.push({
        id: nodeId,
        type: 'default',
        data: { label: `🧠 ${label}`, color, depth },
        position: { x: 100 + depth * 150, y: yOffset },
      })
      
      // Find parent (last node with smaller indent)
      const parentNode = [...nodeStack].reverse().find(n => n.indent < indentLevel)
      if (parentNode) {
        edges.push({
          id: `${parentNode.id}-${nodeId}`,
          source: parentNode.id,
          target: nodeId,
          type: 'smoothstep',
        })
      } else if (nodes.length === 1) {
        rootId = nodeId
      }
      
      // Update stack
      while (nodeStack.length > 0 && nodeStack[nodeStack.length - 1].indent >= indentLevel) {
        nodeStack.pop()
      }
      nodeStack.push({ id: nodeId, indent: indentLevel })
      
      yOffset += 60
    }
    
    return { nodes, edges }
  }

  private parseTimeline(lines: string[]): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    let xOffset = 0
    let lastNodeId = ''
    
    for (const line of lines) {
      if (line.toLowerCase().startsWith('timeline')) continue
      
      // Title
      if (line.toLowerCase().startsWith('title')) {
        nodes.push({
          id: 'timeline_title',
          type: 'default',
          data: { label: `📅 ${line.replace(/^title\s*/i, '')}`, color: '#6366f1' },
          position: { x: xOffset, y: 0 },
        })
        xOffset += 200
        lastNodeId = 'timeline_title'
        continue
      }
      
      // Section (time period)
      if (line.toLowerCase().startsWith('section')) {
        const nodeId = `period_${nodes.length}`
        nodes.push({
          id: nodeId,
          type: 'default',
          data: { label: `⏰ ${line.replace(/^section\s*/i, '')}`, color: '#0ea5e9', isPeriod: true },
          position: { x: xOffset, y: 50 },
        })
        if (lastNodeId) {
          edges.push({ id: `${lastNodeId}-${nodeId}`, source: lastNodeId, target: nodeId, type: 'smoothstep' })
        }
        lastNodeId = nodeId
        xOffset += 180
        continue
      }
      
      // Event
      if (line.trim() && !line.includes(':')) {
        const nodeId = `event_${nodes.length}`
        nodes.push({
          id: nodeId,
          type: 'default',
          data: { label: `📌 ${line}`, color: '#22c55e' },
          position: { x: xOffset - 90, y: 120 },
        })
        if (lastNodeId) {
          edges.push({ id: `${lastNodeId}-${nodeId}`, source: lastNodeId, target: nodeId, type: 'smoothstep' })
        }
      }
    }
    
    return { nodes, edges }
  }

  private parseGitGraph(lines: string[]): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    let yOffset = 0
    let lastCommit = ''
    const branches: Record<string, string> = { main: '#22c55e', develop: '#3b82f6', feature: '#f59e0b' }
    let currentBranch = 'main'
    
    for (const line of lines) {
      if (line.toLowerCase().startsWith('gitgraph') || line.toLowerCase().startsWith('%%')) continue
      
      // Commit
      if (line.toLowerCase().startsWith('commit')) {
        const idMatch = line.match(/id:\s*"([^"]+)"/)
        const tagMatch = line.match(/tag:\s*"([^"]+)"/)
        const nodeId = idMatch ? idMatch[1] : `commit_${nodes.length}`
        
        nodes.push({
          id: nodeId,
          type: 'default',
          data: {
            label: `⚫ ${tagMatch ? tagMatch[1] : nodeId}`,
            color: branches[currentBranch] || '#64748b',
            branch: currentBranch,
          },
          position: { x: 200, y: yOffset },
        })
        
        if (lastCommit) {
          edges.push({ id: `${lastCommit}-${nodeId}`, source: lastCommit, target: nodeId, type: 'smoothstep' })
        }
        lastCommit = nodeId
        yOffset += 60
        continue
      }
      
      // Branch
      if (line.toLowerCase().startsWith('branch')) {
        currentBranch = line.replace(/^branch\s*/i, '').trim()
        if (!branches[currentBranch]) {
          branches[currentBranch] = this.getColorForIndex(Object.keys(branches).length)
        }
        continue
      }
      
      // Checkout
      if (line.toLowerCase().startsWith('checkout')) {
        currentBranch = line.replace(/^checkout\s*/i, '').trim()
        continue
      }
      
      // Merge
      if (line.toLowerCase().startsWith('merge')) {
        const mergeBranch = line.replace(/^merge\s*/i, '').trim()
        const nodeId = `merge_${nodes.length}`
        nodes.push({
          id: nodeId,
          type: 'default',
          data: { label: `🔀 Merge ${mergeBranch}`, color: '#ec4899' },
          position: { x: 200, y: yOffset },
        })
        if (lastCommit) {
          edges.push({ id: `${lastCommit}-${nodeId}`, source: lastCommit, target: nodeId, type: 'smoothstep' })
        }
        lastCommit = nodeId
        yOffset += 60
      }
    }
    
    return { nodes, edges }
  }

  private parseGeneric(lines: string[], type: string): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    
    // Create a single node with diagram info
    nodes.push({
      id: 'diagram_info',
      type: 'default',
      data: {
        label: `📊 ${type.replace(/_/g, ' ').toUpperCase()}\n\n${lines.length} lines of content\n\n(Limited canvas support for this diagram type)`,
        color: '#64748b',
      },
      position: { x: 100, y: 100 },
    })
    
    return { nodes, edges: [] }
  }

  private getColorForIndex(index: number): string {
    const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#0ea5e9', '#14b8a6']
    return colors[index % colors.length]
  }

  /**
   * Generate Mermaid code - returns the original code since we can't fully reconstruct
   */
  generateMermaid(nodes: ReactFlowNode[], edges: ReactFlowEdge[]): string {
    // For generic diagrams, we store the original code in the first node's data
    const infoNode = nodes.find(n => n.id === 'diagram_info')
    if (infoNode?.data?.originalCode) {
      return infoNode.data.originalCode
    }
    
    // Otherwise, generate a basic representation
    return `%% Diagram type: ${this.diagramType}\n%% ${nodes.length} nodes`
  }

  /**
   * Clean Mermaid code
   */
  cleanMermaidCode(code: string): string {
    return code
      .replace(/```mermaid\s*/gi, '')
      .replace(/```\s*/g, '')
      .trim()
  }
}

