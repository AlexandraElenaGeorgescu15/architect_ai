/**
 * Participant Node Component
 * For sequence diagrams - displays participant/actor
 */

import React, { memo, useCallback, useState } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Palette, Trash2, X } from 'lucide-react'
import { NodeData } from './EditableNode'

const COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
  '#3b82f6', '#6366f1', '#a855f7', '#ec4899', '#64748b',
]

const ParticipantNode = ({ id, data, isConnectable, selected }: NodeProps<NodeData>) => {
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
        relative group bg-card rounded-lg shadow-md border-2 transition-all
        ${selected ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-500/30' : 'border-transparent'}
      `}
      style={{
        borderColor: selected ? undefined : data.color || '#6366f1',
        minWidth: '140px',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-muted-foreground hover:bg-blue-500 transition-colors"
      />

      {/* Toolbar */}
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
          title="Delete Participant"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Color Picker */}
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

      {/* Participant Icon/Avatar */}
      <div
        className="px-4 py-3 rounded-lg flex flex-col items-center gap-2"
        style={{ backgroundColor: `${data.color || '#6366f1'}15` }}
      >
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg"
          style={{ backgroundColor: data.color || '#6366f1' }}
        >
          {(data.label || 'P')[0].toUpperCase()}
        </div>
        <input
          className="w-full bg-transparent text-center font-medium focus:outline-none placeholder-gray-400 text-sm"
          style={{ color: '#1f2937' }}
          value={data.label}
          onChange={onLabelChange}
          placeholder="Participant"
        />
      </div>

      <Handle
        type="source"
        position={Position.Right}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-muted-foreground hover:bg-blue-500 transition-colors"
      />
    </div>
  )
}

export default memo(ParticipantNode)

