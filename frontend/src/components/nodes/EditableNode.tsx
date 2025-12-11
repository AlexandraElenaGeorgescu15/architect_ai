/**
 * Editable Node Component
 * Base editable node for React Flow (inspired by MiroMaid)
 */

import React, { memo, useCallback, useState } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Palette, Trash2, X } from 'lucide-react'

export interface NodeData {
  label: string
  color?: string
  onChange?: (id: string, data: Partial<NodeData>) => void
  onDelete?: (id: string) => void
  [key: string]: any
}

const COLORS = [
  '#ef4444', // red
  '#f97316', // orange
  '#eab308', // yellow
  '#22c55e', // green
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#6366f1', // indigo
  '#a855f7', // purple
  '#ec4899', // pink
  '#64748b', // slate
]

const EditableNode = ({ id, data, isConnectable, selected }: NodeProps<NodeData>) => {
  const [showColors, setShowColors] = useState(false)

  const onLabelChange = useCallback(
    (evt: React.ChangeEvent<HTMLInputElement>) => {
      if (data.onChange) {
        data.onChange(id, { label: evt.target.value })
      }
    },
    [data, id]
  )

  const onColorSelect = useCallback(
    (color: string) => {
      if (data.onChange) {
        data.onChange(id, { color })
      }
      setShowColors(false)
    },
    [data, id]
  )

  const onDeleteClick = useCallback(() => {
    if (data.onDelete) {
      data.onDelete(id)
    }
  }, [data, id])

  return (
    <div
      className={`
        relative group bg-card rounded-lg shadow-md border-2 transition-all min-w-[150px]
        ${selected ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-500/30' : 'border-transparent'}
      `}
      style={{
        borderColor: selected ? undefined : data.color || '#6366f1',
      }}
    >
      {/* Top Handle */}
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-muted-foreground hover:bg-blue-500 transition-colors"
      />

      {/* Toolbar (visible on hover/selected) */}
      <div
        className={`
        absolute -top-9 right-0 bg-card rounded-full shadow-lg p-1 flex gap-1
        transition-opacity duration-200 border border-border z-10
        ${selected || showColors ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto'}
      `}
      >
        <button
          onClick={() => setShowColors(!showColors)}
          className="p-1.5 hover:bg-muted rounded-full text-muted-foreground transition-colors"
          title="Change Color"
        >
          <Palette size={14} />
        </button>
        <div className="w-px bg-border my-1"></div>
        <button
          onClick={onDeleteClick}
          className="p-1.5 hover:bg-red-50 dark:hover:bg-red-500/20 text-muted-foreground hover:text-red-500 rounded-full transition-colors"
          title="Delete Node"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Color Picker Popup */}
      {showColors && (
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 bg-card p-2 rounded-xl shadow-xl border border-border grid grid-cols-5 gap-1.5 z-50 w-40">
          {COLORS.map((c) => (
            <button
              key={c}
              className="w-5 h-5 rounded-full hover:scale-110 transition-transform ring-1 ring-border"
              style={{ backgroundColor: c }}
              onClick={() => onColorSelect(c)}
            />
          ))}
          <button
            onClick={() => setShowColors(false)}
            className="col-span-5 text-xs text-muted-foreground hover:text-red-500 mt-1 flex items-center justify-center gap-1"
          >
            <X size={10} /> Close
          </button>
        </div>
      )}

      {/* Content */}
      <div
        className="px-4 py-3 rounded-lg bg-white dark:bg-gray-800"
        style={{ backgroundColor: `${data.color || '#6366f1'}15` }}
      >
        <input
          className="w-full bg-transparent text-center font-medium focus:outline-none focus:border-b border-border placeholder-gray-400 text-gray-900 dark:text-white"
          value={data.label}
          onChange={onLabelChange}
          placeholder="Node Label"
        />
      </div>

      {/* Bottom Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-muted-foreground hover:bg-blue-500 transition-colors"
      />
    </div>
  )
}

export default memo(EditableNode)

