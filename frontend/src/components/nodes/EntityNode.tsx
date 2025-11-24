/**
 * Entity Node Component
 * For ERD diagrams - displays entity name and properties
 */

import React, { memo, useCallback, useState } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { Palette, Trash2, X, Plus } from 'lucide-react'
import { NodeData } from './EditableNode'

interface EntityNodeData extends NodeData {
  properties?: string[]
}

const COLORS = [
  '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
  '#3b82f6', '#6366f1', '#a855f7', '#ec4899', '#64748b',
]

const EntityNode = ({ id, data, isConnectable, selected }: NodeProps<EntityNodeData>) => {
  const [showColors, setShowColors] = useState(false)
  const [newProperty, setNewProperty] = useState('')

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

  const onAddProperty = useCallback(() => {
    if (newProperty.trim() && data.onChange) {
      const properties = [...(data.properties || []), newProperty.trim()]
      data.onChange(id, { properties })
      setNewProperty('')
    }
  }, [newProperty, data, id])

  const onRemoveProperty = useCallback(
    (index: number) => {
      if (data.onChange && data.properties) {
        const properties = data.properties.filter((_, i) => i !== index)
        data.onChange(id, { properties })
      }
    },
    [data, id]
  )

  return (
    <div
      className={`
        relative group bg-white rounded-lg shadow-lg border-2 transition-all min-w-[200px]
        ${selected ? 'border-blue-500 ring-2 ring-blue-200' : 'border-transparent'}
      `}
      style={{
        borderColor: selected ? undefined : data.color || '#6366f1',
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-gray-400 hover:bg-blue-500 transition-colors"
      />

      {/* Toolbar */}
      <div
        className={`
        absolute -top-9 right-0 bg-white rounded-full shadow-lg p-1 flex gap-1
        transition-opacity duration-200 border border-gray-100 z-10
        ${selected || showColors ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto'}
      `}
      >
        <button
          onClick={() => setShowColors(!showColors)}
          className="p-1.5 hover:bg-gray-100 rounded-full text-gray-600 transition-colors"
          title="Change Color"
        >
          <Palette size={14} />
        </button>
        <div className="w-px bg-gray-200 my-1"></div>
        <button
          onClick={onDeleteClick}
          className="p-1.5 hover:bg-red-50 text-gray-600 hover:text-red-500 rounded-full transition-colors"
          title="Delete Entity"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Color Picker */}
      {showColors && (
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 bg-white p-2 rounded-xl shadow-xl border border-gray-200 grid grid-cols-5 gap-1.5 z-50 w-40">
          {COLORS.map((c) => (
            <button
              key={c}
              className="w-5 h-5 rounded-full hover:scale-110 transition-transform ring-1 ring-gray-200"
              style={{ backgroundColor: c }}
              onClick={() => onColorSelect(c)}
            />
          ))}
          <button
            onClick={() => setShowColors(false)}
            className="col-span-5 text-xs text-gray-500 hover:text-red-500 mt-1 flex items-center justify-center gap-1"
          >
            <X size={10} /> Close
          </button>
        </div>
      )}

      {/* Entity Header */}
      <div
        className="px-4 py-2 rounded-t-lg border-b-2"
        style={{
          backgroundColor: `${data.color || '#6366f1'}20`,
          borderColor: data.color || '#6366f1',
        }}
      >
        <input
          className="w-full bg-transparent text-center font-bold text-gray-800 focus:outline-none placeholder-gray-400"
          value={data.label}
          onChange={onLabelChange}
          placeholder="Entity Name"
        />
      </div>

      {/* Properties */}
      <div className="px-3 py-2 space-y-1 max-h-40 overflow-y-auto">
        {(data.properties || []).map((prop, index) => (
          <div
            key={index}
            className="flex items-center justify-between text-xs text-gray-700 hover:bg-gray-50 px-2 py-1 rounded"
          >
            <span className="font-mono">{prop}</span>
            <button
              onClick={() => onRemoveProperty(index)}
              className="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <X size={12} />
            </button>
          </div>
        ))}

        {/* Add Property */}
        <div className="flex gap-1 pt-1">
          <input
            type="text"
            value={newProperty}
            onChange={(e) => setNewProperty(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onAddProperty()}
            placeholder="+ Add property"
            className="flex-1 text-xs px-2 py-1 border border-gray-200 rounded focus:outline-none focus:border-blue-400"
          />
          <button
            onClick={onAddProperty}
            className="p-1 text-blue-600 hover:bg-blue-50 rounded"
            title="Add Property"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-gray-400 hover:bg-blue-500 transition-colors"
      />
    </div>
  )
}

export default memo(EntityNode)

