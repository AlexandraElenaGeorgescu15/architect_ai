import { useState, useEffect, useRef } from 'react'
import { useArtifactStore } from '../stores/artifactStore'
import { FolderOpen, FolderClosed, ChevronDown, X, RefreshCw } from 'lucide-react'
import api from '../services/api'

interface Folder {
  id: string
  name: string
  notes_count: number
}

/**
 * Global Folder Selector component.
 * Allows users to select a project folder to scope all artifacts, diagrams, and versions.
 * When a folder is selected, only artifacts generated for that folder are shown across all views.
 */
export default function FolderSelector() {
  const [folders, setFolders] = useState<Folder[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  const { currentFolderId, setCurrentFolderId } = useArtifactStore()
  
  // Load folders from backend
  const loadFolders = async () => {
    setIsLoading(true)
    try {
      const response = await api.get('/api/meeting-notes/folders')
      setFolders(response.data.folders || [])
    } catch (error) {
      console.error('Failed to load folders:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  // Load folders on mount
  useEffect(() => {
    loadFolders()
  }, [])
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])
  
  const currentFolder = folders.find(f => f.id === currentFolderId)
  
  const handleSelectFolder = (folderId: string | null) => {
    setCurrentFolderId(folderId)
    setIsOpen(false)
  }
  
  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-all ${
          currentFolderId
            ? 'bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20'
            : 'bg-muted/50 text-muted-foreground border border-border hover:bg-muted hover:text-foreground'
        }`}
      >
        {currentFolderId ? (
          <FolderOpen className="w-4 h-4" />
        ) : (
          <FolderClosed className="w-4 h-4" />
        )}
        <span className="max-w-[120px] truncate font-medium">
          {currentFolder?.name || 'All Projects'}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-card border border-border rounded-xl shadow-lg z-50 overflow-hidden">
          {/* Header */}
          <div className="p-3 border-b border-border bg-muted/30">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Project Scope</h4>
              <button
                onClick={loadFolders}
                disabled={isLoading}
                className="p-1 hover:bg-muted rounded transition-colors"
                title="Refresh folders"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-muted-foreground ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground mt-1">
              Select a folder to filter artifacts by project
            </p>
          </div>
          
          {/* Options */}
          <div className="max-h-60 overflow-y-auto custom-scrollbar">
            {/* All Projects option */}
            <button
              onClick={() => handleSelectFolder(null)}
              className={`w-full px-3 py-2.5 text-left flex items-center gap-3 hover:bg-muted/50 transition-colors ${
                !currentFolderId ? 'bg-primary/10' : ''
              }`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                !currentFolderId ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
              }`}>
                <FolderClosed className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-foreground">All Projects</div>
                <div className="text-[10px] text-muted-foreground">Show all artifacts across folders</div>
              </div>
              {!currentFolderId && (
                <div className="w-2 h-2 rounded-full bg-primary" />
              )}
            </button>
            
            {/* Folder options */}
            {folders.length === 0 ? (
              <div className="px-3 py-4 text-center text-xs text-muted-foreground">
                {isLoading ? 'Loading folders...' : 'No project folders found'}
              </div>
            ) : (
              folders.map((folder) => (
                <button
                  key={folder.id}
                  onClick={() => handleSelectFolder(folder.id)}
                  className={`w-full px-3 py-2.5 text-left flex items-center gap-3 hover:bg-muted/50 transition-colors ${
                    currentFolderId === folder.id ? 'bg-primary/10' : ''
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    currentFolderId === folder.id ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground'
                  }`}>
                    <FolderOpen className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-foreground truncate">{folder.name}</div>
                    <div className="text-[10px] text-muted-foreground">{folder.notes_count} meeting note{folder.notes_count !== 1 ? 's' : ''}</div>
                  </div>
                  {currentFolderId === folder.id && (
                    <div className="w-2 h-2 rounded-full bg-primary" />
                  )}
                </button>
              ))
            )}
          </div>
          
          {/* Clear selection footer (only shown when a folder is selected) */}
          {currentFolderId && (
            <div className="p-2 border-t border-border bg-muted/20">
              <button
                onClick={() => handleSelectFolder(null)}
                className="w-full px-3 py-1.5 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors flex items-center justify-center gap-1.5"
              >
                <X className="w-3 h-3" />
                Clear folder filter
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
