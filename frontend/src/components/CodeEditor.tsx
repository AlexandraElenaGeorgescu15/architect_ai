/**
 * Code Editor Component
 * For editing Mermaid diagram code (inspired by MiroMaid)
 * Now collapsible to give more space to the canvas
 */

import React, { useEffect, useState } from 'react'
import { RefreshCw, Wand2, AlertCircle, ChevronLeft, ChevronRight, Code, Wrench, Loader2 } from 'lucide-react'

interface CodeEditorProps {
  code: string
  onCodeChange: (code: string) => void
  onSync: () => void
  onMagic: () => void
  onFix?: () => void  // NEW: Separate repair function (aggressive fix)
  isSyncing: boolean
  isFixing?: boolean  // NEW: Loading state for fix operation
  diagramType?: string
  isCollapsed?: boolean
  onToggleCollapse?: () => void
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  code,
  onCodeChange,
  onSync,
  onMagic,
  onFix,
  isSyncing,
  isFixing = false,
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
      <div className="flex flex-col h-full bg-white dark:bg-card border-l border-gray-200 dark:border-border shadow-xl w-10 flex-shrink-0 transition-all duration-300">
        <button
          onClick={onToggleCollapse}
          className="flex-1 flex flex-col items-center justify-center gap-2 hover:bg-gray-50 dark:hover:bg-secondary transition-colors group"
          title="Expand code editor"
        >
          <ChevronLeft size={18} className="text-gray-400 dark:text-muted-foreground group-hover:text-indigo-600 dark:group-hover:text-primary" />
          <div className="writing-vertical text-xs font-medium text-gray-500 dark:text-muted-foreground group-hover:text-indigo-600 dark:group-hover:text-primary rotate-180" style={{ writingMode: 'vertical-rl' }}>
            Code Editor
          </div>
          <Code size={16} className="text-gray-400 dark:text-muted-foreground group-hover:text-indigo-600 dark:group-hover:text-primary" />
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-white dark:bg-card border-l border-gray-200 dark:border-border shadow-xl w-80 lg:w-96 flex-shrink-0 transition-all duration-300 max-h-full overflow-hidden">
      <div className="p-3 border-b border-gray-100 dark:border-border flex items-center justify-between bg-gray-50 dark:bg-secondary/30 flex-shrink-0">
        <div className="flex items-center gap-2">
          {/* Collapse button */}
          <button
            onClick={onToggleCollapse}
            className="p-1.5 hover:bg-gray-200 dark:hover:bg-secondary rounded-md transition-colors"
            title="Collapse code editor"
          >
            <ChevronRight size={16} className="text-gray-500 dark:text-muted-foreground" />
          </button>
          <h2 className="font-semibold text-gray-700 dark:text-foreground flex items-center gap-2 text-sm">
            <span className="text-indigo-600 dark:text-primary font-mono text-xs">&lt;/&gt;</span> {diagramType.replace('mermaid_', '').replace(/_/g, ' ')}
          </h2>
        </div>
        <div className="flex gap-1.5">
          {/* Fix button - Aggressive repair for broken diagrams */}
          {onFix && (
            <button
              onClick={onFix}
              disabled={isSyncing || isFixing}
              className="p-1.5 text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-950/30 rounded-md transition-colors flex items-center gap-1 text-xs font-medium border border-transparent hover:border-orange-100 dark:hover:border-orange-800 disabled:opacity-50"
              title="Fix: Aggressive repair for broken diagrams (retries until it works)"
            >
              {isFixing ? <Loader2 size={14} className="animate-spin" /> : <Wrench size={14} />}
              <span className="hidden sm:inline">Fix</span>
            </button>
          )}
          {/* Improve button - Enhance working diagrams */}
          <button
            onClick={onMagic}
            disabled={isSyncing || isFixing}
            className="p-1.5 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/30 rounded-md transition-colors flex items-center gap-1 text-xs font-medium border border-transparent hover:border-purple-100 dark:hover:border-purple-800 disabled:opacity-50"
            title="Improve: Add colors, styles, and enhance layout"
          >
            <Wand2 size={14} />
            <span className="hidden sm:inline">Improve</span>
          </button>
          <button
            onClick={onSync}
            disabled={isSyncing || isFixing}
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

      <div className="flex-1 relative bg-white dark:bg-card overflow-hidden min-h-0">
        <textarea
          value={localCode}
          onChange={handleChange}
          className="w-full h-full p-3 font-mono text-xs resize-none focus:outline-none text-gray-800 dark:text-foreground bg-white dark:bg-card leading-relaxed overflow-auto"
          placeholder="graph TD&#10;  A[Start] --> B[End]"
          spellCheck={false}
        />
      </div>

      <div className="p-2 bg-gray-50 dark:bg-secondary/30 border-t border-gray-200 dark:border-border text-[10px] text-gray-500 dark:text-muted-foreground flex gap-2 items-start flex-shrink-0">
        <AlertCircle size={12} className="mt-0.5 flex-shrink-0 text-indigo-400 dark:text-primary" />
        <p>
          Edit code and click <b>Render</b>. Canvas changes sync automatically.
        </p>
      </div>
    </div>
  )
}

export default CodeEditor
