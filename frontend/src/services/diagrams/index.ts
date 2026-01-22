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

/**
 * Diagram adapter factory
 * Returns the appropriate adapter for a given diagram type
 */
export function getAdapterForDiagramType(diagramType: string): BaseDiagramAdapter {
  const type = diagramType.toLowerCase().replace('mermaid_', '').replace('html_', '')

  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/dfc1763a-e24e-49d7-baae-a7a908b307cd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'diagrams/index.ts:getAdapterForDiagramType',message:'Adapter selection',data:{originalType:diagramType,normalizedType:type},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
  // #endregion

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

    case 'class':
    case 'uml':
      return new ClassAdapter()

    // Add more as implemented...
    // case 'state':
    //   return new StateAdapter()

    // Default to flowchart adapter for unsupported types
    default:
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/dfc1763a-e24e-49d7-baae-a7a908b307cd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'diagrams/index.ts:getAdapterForDiagramType:fallback',message:'UNSUPPORTED TYPE - using FlowchartAdapter fallback',data:{originalType:diagramType,normalizedType:type},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'H1'})}).catch(()=>{});
      // #endregion
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
  ClassAdapter,
}

