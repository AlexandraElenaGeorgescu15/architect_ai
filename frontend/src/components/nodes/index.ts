/**
 * Custom Node Components Index
 * Exports all custom node types for React Flow
 */

import EditableNode from './EditableNode'
import EntityNode from './EntityNode'
import ParticipantNode from './ParticipantNode'

// Node type mapping for React Flow
export const nodeTypes = {
  custom: EditableNode,
  entity: EntityNode,
  participant: ParticipantNode,
  component: EditableNode, // Reuse editable node
  decision: EditableNode, // Reuse editable node with different styling
}

export { EditableNode, EntityNode, ParticipantNode }

export type { NodeData } from './EditableNode'

