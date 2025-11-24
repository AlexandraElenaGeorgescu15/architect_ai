/**
 * Diagram Adapters Index
 * Exports all diagram adapters and factory function
 */

import { BaseDiagramAdapter } from './baseDiagramAdapter'
import { FlowchartAdapter } from './flowchartAdapter'
import { ERDAdapter } from './erdAdapter'
import { SequenceAdapter } from './sequenceAdapter'
import { ArchitectureAdapter } from './architectureAdapter'

/**
 * Diagram adapter factory
 * Returns the appropriate adapter for a given diagram type
 */
export function getAdapterForDiagramType(diagramType: string): BaseDiagramAdapter {
  const type = diagramType.toLowerCase().replace('mermaid_', '').replace('html_', '')

  switch (type) {
    case 'flowchart':
    case 'flow':
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

    // Add more as implemented...
    // case 'class':
    //   return new ClassAdapter()
    // case 'state':
    //   return new StateAdapter()

    // Default to flowchart adapter for unsupported types
    default:
      console.warn(`No specific adapter for ${diagramType}, using FlowchartAdapter`)
      return new FlowchartAdapter()
  }
}

// Export all adapters
export {
  BaseDiagramAdapter,
  FlowchartAdapter,
  ERDAdapter,
  SequenceAdapter,
  ArchitectureAdapter,
}

