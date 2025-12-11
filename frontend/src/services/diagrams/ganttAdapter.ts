/**
 * Gantt Chart Adapter
 * Parses Mermaid Gantt chart syntax to React Flow format
 */

import { BaseDiagramAdapter } from './baseDiagramAdapter'
import type { ReactFlowNode, ReactFlowEdge } from '../diagramService'

interface GanttTask {
  id: string
  name: string
  section: string
  status?: string
  startDate?: string
  duration?: string
}

export class GanttAdapter extends BaseDiagramAdapter {
  /**
   * Parse Mermaid Gantt chart to React Flow nodes/edges
   */
  parseFromMermaid(mermaidCode: string): { nodes: ReactFlowNode[]; edges: ReactFlowEdge[] } {
    const nodes: ReactFlowNode[] = []
    const edges: ReactFlowEdge[] = []
    const lines = mermaidCode.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('%%'))
    
    let currentSection = 'Default'
    let yOffset = 0
    const sectionYStart: Record<string, number> = {}
    
    for (const line of lines) {
      // Skip diagram declaration
      if (line.startsWith('gantt')) continue
      if (line.startsWith('title')) continue
      if (line.startsWith('dateFormat')) continue
      if (line.startsWith('axisFormat')) continue
      if (line.startsWith('excludes')) continue
      if (line.startsWith('todayMarker')) continue
      
      // Section declaration
      const sectionMatch = line.match(/^section\s+(.+)$/i)
      if (sectionMatch) {
        currentSection = sectionMatch[1].trim()
        if (!sectionYStart[currentSection]) {
          sectionYStart[currentSection] = yOffset
        }
        
        // Create section node
        nodes.push({
          id: `section_${currentSection.replace(/\s+/g, '_')}`,
          type: 'default',
          data: {
            label: `📋 ${currentSection}`,
            color: '#3b82f6',
            isSection: true,
          },
          position: { x: 50, y: yOffset },
        })
        yOffset += 60
        continue
      }
      
      // Task declaration: TaskName :status, id, start, duration
      // or: TaskName :id, start, duration
      // or: TaskName :start, duration
      const taskMatch = line.match(/^([^:]+):\s*(.+)$/)
      if (taskMatch) {
        const taskName = taskMatch[1].trim()
        const taskParams = taskMatch[2].split(',').map(p => p.trim())
        
        let status = ''
        let taskId = `task_${nodes.length}`
        let startDate = ''
        let duration = ''
        
        // Parse task parameters
        for (const param of taskParams) {
          if (param === 'done' || param === 'active' || param === 'crit') {
            status = param
          } else if (param.match(/^\d{4}-\d{2}-\d{2}/) || param.match(/^after\s+/)) {
            startDate = param
          } else if (param.match(/^\d+[dwmh]?$/)) {
            duration = param
          } else if (!param.includes(' ')) {
            taskId = param
          }
        }
        
        // Determine color based on status
        let color = '#64748b' // default gray
        if (status === 'done') color = '#22c55e' // green
        if (status === 'active') color = '#3b82f6' // blue
        if (status === 'crit') color = '#ef4444' // red
        
        nodes.push({
          id: taskId,
          type: 'default',
          data: {
            label: `${taskName}${duration ? ` (${duration})` : ''}`,
            color,
            status,
            section: currentSection,
            startDate,
            duration,
          },
          position: { x: 200, y: yOffset },
        })
        
        // Create edge from section to task
        const sectionId = `section_${currentSection.replace(/\s+/g, '_')}`
        if (nodes.find(n => n.id === sectionId)) {
          edges.push({
            id: `${sectionId}-${taskId}`,
            source: sectionId,
            target: taskId,
            type: 'smoothstep',
          })
        }
        
        // Handle "after" dependencies
        if (startDate.startsWith('after ')) {
          const afterTask = startDate.replace('after ', '').trim()
          edges.push({
            id: `${afterTask}-${taskId}`,
            source: afterTask,
            target: taskId,
            type: 'smoothstep',
            animated: true,
            label: 'after',
          })
        }
        
        yOffset += 50
      }
    }
    
    return { nodes, edges }
  }

  /**
   * Generate Mermaid Gantt chart from React Flow nodes/edges
   */
  generateMermaid(nodes: ReactFlowNode[], edges: ReactFlowEdge[]): string {
    const lines: string[] = ['gantt', '    dateFormat YYYY-MM-DD', '']
    
    // Group tasks by section
    const sections: Record<string, ReactFlowNode[]> = {}
    
    for (const node of nodes) {
      if (node.data?.isSection) continue
      
      const section = node.data?.section || 'Tasks'
      if (!sections[section]) {
        sections[section] = []
      }
      sections[section].push(node)
    }
    
    // Generate Mermaid code for each section
    for (const [sectionName, tasks] of Object.entries(sections)) {
      lines.push(`    section ${sectionName}`)
      
      for (const task of tasks) {
        const status = task.data?.status ? `${task.data.status}, ` : ''
        const taskId = task.id
        const duration = task.data?.duration || '1d'
        const startDate = task.data?.startDate || 'today'
        
        // Find if this task depends on another (has incoming "after" edge)
        const dependencyEdge = edges.find(e => e.target === taskId && e.label === 'after')
        const start = dependencyEdge ? `after ${dependencyEdge.source}` : startDate
        
        const label = task.data?.label?.replace(/\s*\([^)]+\)$/, '') || task.id
        lines.push(`    ${label} :${status}${taskId}, ${start}, ${duration}`)
      }
      lines.push('')
    }
    
    return lines.join('\n')
  }

  /**
   * Clean Mermaid code by extracting just the gantt diagram
   */
  cleanMermaidCode(code: string): string {
    // Find gantt block
    const ganttMatch = code.match(/gantt[\s\S]*?(?=```|$)/i)
    if (ganttMatch) {
      return ganttMatch[0].trim()
    }
    
    // Remove markdown code blocks
    const cleaned = code
      .replace(/```mermaid\s*/gi, '')
      .replace(/```\s*/g, '')
      .trim()
    
    // Ensure it starts with gantt
    if (!cleaned.toLowerCase().startsWith('gantt')) {
      return `gantt\n${cleaned}`
    }
    
    return cleaned
  }
}

