/**
 * Diagram Adapters Index
 * Exports all diagram adapters and factory function
 */

import { BaseDiagramAdapter } from './baseDiagramAdapter'
import { FlowchartAdapter } from './flowchartAdapter'
import { ERDAdapter } from './erdAdapter'
import { SequenceAdapter } from './sequenceAdapter'
import { ArchitectureAdapter } from './architectureAdapter'
import { ClassAdapter } from './classAdapter'
import { GanttAdapter } from './ganttAdapter'
import { StateAdapter } from './stateAdapter'
import { C4Adapter } from './c4Adapter'
import { GenericAdapter } from './genericAdapter'

/**
 * Diagram adapter factory
 * Returns the appropriate adapter for a given diagram type
 */
export function getAdapterForDiagramType(diagramType: string): BaseDiagramAdapter {
  const type = diagramType.toLowerCase().replace('mermaid_', '').replace('html_', '')

  switch (type) {
    case 'flowchart':
    case 'flow':
    case 'data_flow':
    case 'user_flow':
      return new FlowchartAdapter()

    case 'erd':
    case 'entity':
      return new ERDAdapter()

    case 'sequence':
    case 'api_sequence':
      return new SequenceAdapter()

    case 'architecture':
    case 'component':
    case 'system_overview':
      return new ArchitectureAdapter()

    case 'class':
    case 'uml':
      return new ClassAdapter()

    case 'gantt':
      return new GanttAdapter()

    case 'state':
      return new StateAdapter()

    case 'c4_context':
    case 'c4_container':
    case 'c4_component':
    case 'c4_deployment':
      return new C4Adapter()

    // Generic adapter for diagram types with limited canvas support
    case 'pie':
    case 'journey':
    case 'mindmap':
    case 'timeline':
    case 'git_graph':
    case 'quadrant':
    case 'requirement':
      return new GenericAdapter(type)

    // Default to generic adapter for unknown types
    default:
      console.warn(`No specific adapter for ${diagramType}, using GenericAdapter`)
      return new GenericAdapter(type)
  }
}

// Export all adapters
export {
  BaseDiagramAdapter,
  FlowchartAdapter,
  ERDAdapter,
  SequenceAdapter,
  ArchitectureAdapter,
  ClassAdapter,
  GanttAdapter,
  StateAdapter,
  C4Adapter,
  GenericAdapter,
}

