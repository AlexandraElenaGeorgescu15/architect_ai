/**
 * Code Editor Component
 * For editing Mermaid diagram code (inspired by MiroMaid)
 */

import React, { useEffect, useState } from 'react'
import { RefreshCw, Wand2, AlertCircle } from 'lucide-react'

interface CodeEditorProps {
  code: string
  onCodeChange: (code: string) => void
  onSync: () => void
  onMagic: () => void
  isSyncing: boolean
  diagramType?: string
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  onCodeChange,
  onSync,
  onMagic,
  isSyncing,
  diagramType = 'Mermaid',
}) => {
  const [localCode, setLocalCode] = useState(code)

  useEffect(() => {
    setLocalCode(code)
  }, [code])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setLocalCode(e.target.value)
    onCodeChange(e.target.value)
  }

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200 shadow-xl w-full md:w-96 flex-shrink-0 transition-all">
      <div className="p-4 border-b border-gray-100 flex items-center justify-between bg-gray-50">
        <h2 className="font-semibold text-gray-700 flex items-center gap-2">
          <span className="text-indigo-600 font-mono text-sm">&lt;/&gt;</span> {diagramType}
        </h2>
        <div className="flex gap-2">
          <button
            onClick={onMagic}
            disabled={isSyncing}
            className="p-2 text-purple-600 hover:bg-purple-50 rounded-md transition-colors flex items-center gap-1.5 text-xs font-medium border border-transparent hover:border-purple-100"
            title="AI Clean Up"
          >
            <Wand2 size={14} /> Auto-Fix
          </button>
          <button
            onClick={onSync}
            disabled={isSyncing}
            className={`
              px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium 
              flex items-center gap-1.5 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm
              ${isSyncing ? 'animate-pulse' : ''}
            `}
          >
            <RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />
            {isSyncing ? 'Syncing...' : 'Render'}
          </button>
        </div>
      </div>

      <div className="flex-1 relative bg-white">
        <textarea
          value={localCode}
          onChange={handleChange}
          className="w-full h-full p-4 font-mono text-sm resize-none focus:outline-none text-gray-800 bg-white leading-relaxed"
          placeholder="graph TD&#10;  A[Start] --> B[End]"
          spellCheck={false}
        />
      </div>

      <div className="p-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 flex gap-2 items-start">
        <AlertCircle size={14} className="mt-0.5 flex-shrink-0 text-indigo-400" />
        <p>
          Edit the code above and click <b>Render</b> to update the canvas.
          Changes on the canvas update this code automatically.
        </p>
      </div>
    </div>
  )
}

export default CodeEditor
