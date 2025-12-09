/**
 * Code Editor Component
 * For editing Mermaid diagram code (inspired by MiroMaid)
 * Now collapsible to give more space to the canvas
 */

import React, { useEffect, useState } from 'react'
import { RefreshCw, Wand2, AlertCircle, ChevronLeft, ChevronRight, Code } from 'lucide-react'

interface CodeEditorProps {
  code: string
  onCodeChange: (code: string) => void
  onSync: () => void
  onMagic: () => void
  isSyncing: boolean
  diagramType?: string
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  onCodeChange,
  onSync,
  onMagic,
  isSyncing,
  diagramType = 'Mermaid',
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const [localCode, setLocalCode] = useState(code)

  useEffect(() => {
    setLocalCode(code)
  }, [code])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalCode(e.target.value)
    onCodeChange(e.target.value)
  }

  // Collapsed state - show just a thin bar with expand button
  if (isCollapsed) {
    return (
      <div className="flex flex-col h-full bg-white border-l border-gray-200 shadow-xl w-10 flex-shrink-0 transition-all duration-300">
        <button
          onClick={onToggleCollapse}
          className="flex-1 flex flex-col items-center justify-center gap-2 hover:bg-gray-50 transition-colors group"
          title="Expand code editor"
        >
          <ChevronLeft size={18} className="text-gray-400 group-hover:text-indigo-600" />
          <div className="writing-vertical text-xs font-medium text-gray-500 group-hover:text-indigo-600 rotate-180" style={{ writingMode: 'vertical-rl' }}>
            Code Editor
          </div>
          <Code size={16} className="text-gray-400 group-hover:text-indigo-600" />
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200 shadow-xl w-full md:w-96 flex-shrink-0 transition-all duration-300">
      <div className="p-3 border-b border-gray-100 flex items-center justify-between bg-gray-50">
        <div className="flex items-center gap-2">
          {/* Collapse button */}
          <button
            onClick={onToggleCollapse}
            className="p-1.5 hover:bg-gray-200 rounded-md transition-colors"
            title="Collapse code editor"
          >
            <ChevronRight size={16} className="text-gray-500" />
          </button>
          <h2 className="font-semibold text-gray-700 flex items-center gap-2 text-sm">
            <span className="text-indigo-600 font-mono text-xs">&lt;/&gt;</span> {diagramType.replace('mermaid_', '').replace(/_/g, ' ')}
          </h2>
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={onMagic}
            disabled={isSyncing}
            className="p-1.5 text-purple-600 hover:bg-purple-50 rounded-md transition-colors flex items-center gap-1 text-xs font-medium border border-transparent hover:border-purple-100 disabled:opacity-50"
            title="AI Auto-Fix: Clean up and improve the diagram code"
          >
            <Wand2 size={14} />
            <span className="hidden sm:inline">Fix</span>
          </button>
          <button
            onClick={onSync}
            disabled={isSyncing}
            className={`
              px-2.5 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium 
              flex items-center gap-1 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm
              ${isSyncing ? 'animate-pulse' : ''}
            `}
          >
            <RefreshCw size={12} className={isSyncing ? 'animate-spin' : ''} />
            {isSyncing ? '...' : 'Render'}
          </button>
        </div>
      </div>

      <div className="flex-1 relative bg-white overflow-hidden">
        <textarea
          value={localCode}
          onChange={handleChange}
          className="w-full h-full p-3 font-mono text-xs resize-none focus:outline-none text-gray-800 bg-white leading-relaxed"
          placeholder="graph TD&#10;  A[Start] --> B[End]"
          spellCheck={false}
        />
      </div>

      <div className="p-2 bg-gray-50 border-t border-gray-200 text-[10px] text-gray-500 flex gap-2 items-start">
        <AlertCircle size={12} className="mt-0.5 flex-shrink-0 text-indigo-400" />
        <p>
          Edit code and click <b>Render</b>. Canvas changes sync automatically.
        </p>
      </div>
    </div>
  )
}

export default CodeEditor
