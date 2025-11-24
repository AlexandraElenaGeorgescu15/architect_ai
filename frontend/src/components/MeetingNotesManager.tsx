import { useState, useEffect, useMemo } from 'react'
import { Folder, FolderPlus, FileText, Upload, Sparkles, Check, X, Search, Info, ChevronRight, Trash2, Move, MoreVertical, Edit2 } from 'lucide-react'
import api from '../services/api'
import { useUIStore } from '../stores/uiStore'

interface Folder {
  id: string
  name: string
  notes_count: number
  created_at: string
}

interface Note {
  id: string
  name: string
  size: number
  created_at: string
  updated_at: string
}

interface FolderSuggestion {
  suggested_folder: string
  confidence: number
  alternatives: Array<{ folder: string; score: number }>
}

export default function MeetingNotesManager() {
  const { addNotification } = useUIStore()
  const [folders, setFolders] = useState<Folder[]>([])
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null)
  const [notes, setNotes] = useState<Note[]>([])
  const [newFolderName, setNewFolderName] = useState('')
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [suggestion, setSuggestion] = useState<FolderSuggestion | null>(null)
  const [suggesting, setSuggesting] = useState(false)
  const [folderSearch, setFolderSearch] = useState('')
  const [showMoveDialog, setShowMoveDialog] = useState<{ noteId: string; noteName: string } | null>(null)
  const [targetFolderId, setTargetFolderId] = useState<string>('')
  const [showFolderMenu, setShowFolderMenu] = useState<string | null>(null)
  const [showNoteMenu, setShowNoteMenu] = useState<string | null>(null)
  const [renamingFolder, setRenamingFolder] = useState<{ id: string; name: string } | null>(null)
  const [newFolderNameEdit, setNewFolderNameEdit] = useState('')

  const totalNotes = useMemo(
    () => folders.reduce((sum, folder) => sum + folder.notes_count, 0),
    [folders]
  )

  const filteredFolders = useMemo(() => {
    if (!folderSearch.trim()) {
      return folders
    }
    const query = folderSearch.toLowerCase()
    return folders.filter((folder) => folder.name.toLowerCase().includes(query))
  }, [folders, folderSearch])

  const selectedFolderDetails = useMemo(
    () => folders.find((folder) => folder.id === selectedFolder),
    [folders, selectedFolder]
  )

  useEffect(() => {
    loadFolders()
  }, [])

  useEffect(() => {
    if (selectedFolder) {
      loadNotes(selectedFolder)
    }
  }, [selectedFolder])

  const normalizeSuggestion = (raw: any): FolderSuggestion => {
    if (!raw) {
      return {
        suggested_folder: 'general',
        confidence: 0.5,
        alternatives: [],
      }
    }

    const suggestedFolder = typeof raw.suggested_folder === 'string'
      ? raw.suggested_folder
      : typeof raw.folder_id === 'string'
        ? raw.folder_id
        : 'general'

    const confidenceValue = typeof raw.confidence === 'number'
      ? raw.confidence
      : Number(raw.confidence ?? 0.5)

    const rawAlternatives = Array.isArray(raw.alternatives) ? raw.alternatives : []
    const alternatives = rawAlternatives
      .map((alt: any) => {
        if (Array.isArray(alt) && alt.length >= 1) {
          const [folder, score] = alt
          if (typeof folder !== 'string') {
            return null
          }
          return { folder, score: typeof score === 'number' ? score : Number(score ?? 0) }
        }
        if (alt && typeof alt === 'object') {
          if (typeof alt.folder === 'string') {
            return { folder: alt.folder, score: typeof alt.score === 'number' ? alt.score : Number(alt.score ?? 0) }
          }
          if (typeof alt.name === 'string') {
            return { folder: alt.name, score: typeof alt.score === 'number' ? alt.score : Number(alt.score ?? 0) }
          }
        }
        return null
      })
      .filter((item): item is { folder: string; score: number } => Boolean(item && item.folder))

    return {
      suggested_folder: suggestedFolder,
      confidence: Math.max(0, Math.min(1, confidenceValue)),
      alternatives,
    }
  }

  const loadFolders = async () => {
    try {
      const response = await api.get('/api/meeting-notes/folders')
      setFolders(response.data.folders || [])
    } catch (error) {
      // Failed to load folders - handle in UI
    }
  }

  const loadNotes = async (folderId: string) => {
    try {
      const response = await api.get(`/api/meeting-notes/folders/${folderId}/notes`)
      setNotes(response.data.notes || [])
    } catch (error) {
      // Failed to load notes - handle in UI
    }
  }

  const createFolder = async () => {
    if (!newFolderName.trim()) return

    try {
      await api.post('/api/meeting-notes/folders', {
        name: newFolderName
      })
      setNewFolderName('')
      setShowNewFolder(false)
      await loadFolders()
      addNotification('success', `Folder "${newFolderName}" created successfully`)
    } catch (error: any) {
      // Failed to create folder - show user error
      addNotification('error', error.response?.data?.detail || 'Failed to create folder')
    }
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      // First, get AI suggestion
      const content = await file.text()
      setSuggesting(true)
      const suggestResponse = await api.post('/api/meeting-notes/suggest-folder', {
        content: content.substring(0, 1000) // First 1000 chars for suggestion
      })
      const suggestionData = normalizeSuggestion(suggestResponse.data)
      setSuggestion(suggestionData)
      setSuggesting(false)

      // Upload with suggested folder (if user doesn't override)
      const formData = new FormData()
      formData.append('file', file)
      if (suggestionData.suggested_folder && !suggestion) {
        // Find folder by name if it's a name, not an ID
        const folder = folders.find(f => f.name === suggestionData.suggested_folder || f.id === suggestionData.suggested_folder)
        if (folder) {
          formData.append('folder_id', folder.id)
        }
      } else if (selectedFolder) {
        formData.append('folder_id', selectedFolder)
      }

      const uploadResponse = await api.post('/api/meeting-notes/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      if (uploadResponse.data.suggested_folder) {
        // Show suggestion and let user confirm
        setSuggestion({
          suggested_folder: uploadResponse.data.suggested_folder,
          confidence: suggestionData.confidence,
          alternatives: suggestionData.alternatives
        })
      } else {
        // Upload successful, refresh
        await loadFolders()
        if (uploadResponse.data.note?.folder_id && uploadResponse.data.note.folder_id === selectedFolder) {
          await loadNotes(selectedFolder!)
        }
        setSuggestion(null)
        addNotification('success', 'File uploaded successfully')
      }
    } catch (error: any) {
      // Failed to upload file - show user error
      addNotification('error', error.response?.data?.detail || 'Failed to upload file')
    } finally {
      setUploading(false)
      setSuggesting(false)
    }
  }

  const confirmSuggestion = async (folderId: string) => {
    setSuggestion(null)
    loadFolders()
    setSelectedFolder(folderId)
    loadNotes(folderId)
  }

  const deleteNote = async (noteId: string, noteName: string) => {
    if (!selectedFolder) return
    if (!confirm(`Delete note "${noteName}"? This action cannot be undone.`)) return

    try {
      await api.delete(`/api/meeting-notes/folders/${selectedFolder}/notes/${noteId}`)
      addNotification('success', `Note "${noteName}" deleted successfully`)
      await loadNotes(selectedFolder)
      await loadFolders() // Refresh folder counts
    } catch (error: any) {
      addNotification('error', error.response?.data?.detail || 'Failed to delete note')
    }
  }

  const deleteFolder = async (folderId: string, folderName: string) => {
    if (!confirm(`Delete folder "${folderName}" and all its notes? This action cannot be undone.`)) return

    try {
      await api.delete(`/api/meeting-notes/folders/${folderId}`)
      addNotification('success', `Folder "${folderName}" deleted successfully`)
      if (selectedFolder === folderId) {
        setSelectedFolder(null)
        setNotes([])
      }
      await loadFolders()
    } catch (error: any) {
      addNotification('error', error.response?.data?.detail || 'Failed to delete folder')
    }
  }

  const moveNote = async (noteId: string, noteName: string, targetFolder: string) => {
    if (!selectedFolder || !targetFolder) return

    try {
      await api.post('/api/meeting-notes/notes/move', {
        note_id: noteId,
        from_folder: selectedFolder,
        to_folder: targetFolder
      })
      addNotification('success', `Note "${noteName}" moved successfully`)
      await loadNotes(selectedFolder)
      await loadFolders()
      setShowMoveDialog(null)
      setTargetFolderId('')
    } catch (error: any) {
      addNotification('error', error.response?.data?.detail || 'Failed to move note')
    }
  }

  const renameFolder = async (folderId: string, newName: string) => {
    if (!newName.trim()) return

    try {
      await api.put(`/api/meeting-notes/folders/${folderId}/rename`, {
        new_name: newName
      })
      addNotification('success', 'Folder renamed successfully')
      await loadFolders()
      setRenamingFolder(null)
      setNewFolderNameEdit('')
    } catch (error: any) {
      addNotification('error', error.response?.data?.detail || 'Failed to rename folder')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex gap-2 ml-auto">
          <label
            className="px-4 py-2 glass-button rounded-xl text-foreground hover:text-primary cursor-pointer flex items-center gap-2 text-sm font-medium"
            title="Upload meeting notes (.md or .txt)"
          >
            <Upload className="w-4 h-4" />
            Upload Notes
            <input
              type="file"
              accept=".md,.txt"
              onChange={handleFileSelect}
              className="hidden"
              disabled={uploading || suggesting}
            />
          </label>
          <button
            onClick={() => setShowNewFolder(true)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 flex items-center gap-2 text-sm font-medium hover-scale shadow-lg shadow-primary/20"
            title="Create a new folder"
          >
            <FolderPlus className="w-4 h-4" />
            New Folder
          </button>
        </div>
      </div>

      {/* Unified Dashboard Strip */}
      <div className="glass-panel rounded-2xl p-4 flex items-center justify-between animate-fade-in-up border-border/50 bg-background/40">
        <div className="flex gap-8 divide-x divide-border/50">
          <div className="px-4">
             <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Folders</p>
             <p className="text-2xl font-bold text-foreground">{folders.length}</p>
          </div>
          <div className="px-4 pl-8">
             <p className="text-xs uppercase tracking-widest text-muted-foreground mb-1">Notes</p>
             <p className="text-2xl font-bold text-primary">{totalNotes}</p>
          </div>
        </div>
        
        <div className="flex gap-6 items-center">
          <div className="flex items-center gap-3 bg-background/30 px-4 py-2 rounded-xl border border-border/50">
             <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20">
                <Sparkles className="w-4 h-4 text-primary animate-pulse" />
             </div>
             <div>
                <p className="text-xs font-bold text-foreground">AI Auto-Sort</p>
                <p className="text-[10px] text-muted-foreground">Active on upload</p>
             </div>
          </div>
          
          <div className="flex items-center gap-3 bg-background/30 px-4 py-2 rounded-xl border border-border/50">
             <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center border border-accent/20">
                <Info className="w-4 h-4 text-accent" />
             </div>
             <div>
                <p className="text-xs font-bold text-foreground">Pro Tip</p>
                <p className="text-[10px] text-muted-foreground">Select folder for context</p>
             </div>
          </div>
        </div>
      </div>

      {/* AI Suggestion Modal */}
      {suggestion && (
        <div className="glass-panel rounded-2xl p-6 shadow-floating animate-slide-up-bounce border-2 border-primary/30 relative overflow-hidden bg-card">
          <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-primary via-accent to-primary animate-pulse-glow" />
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center border-2 border-primary/20 animate-pulse-glow">
               <Sparkles className="w-6 h-6 text-primary" />
            </div>
            <div>
               <h3 className="text-lg font-bold text-foreground">Smart Filing Suggestion</h3>
               <p className="text-xs text-muted-foreground font-medium">Based on AI content analysis</p>
            </div>
          </div>
          
          <div className="glass-panel bg-primary/5 border-2 border-primary/20 rounded-xl p-5 mb-6 flex items-center justify-between">
            <div>
               <p className="text-xs text-muted-foreground font-semibold mb-2 uppercase tracking-wider">Suggested Folder</p>
               <p className="text-xl font-bold text-primary flex items-center gap-2">
                  <Folder className="w-6 h-6" /> {suggestion.suggested_folder}
               </p>
            </div>
            <div className="text-right">
               <p className="text-xs text-muted-foreground font-semibold mb-2 uppercase tracking-wider">Confidence</p>
               <div className="px-4 py-2 bg-accent/10 border-2 border-accent/20 rounded-lg">
                 <p className="text-2xl font-bold text-accent">{Math.round(suggestion.confidence * 100)}%</p>
               </div>
            </div>
          </div>
          
          <div className="flex justify-end gap-3">
            <button
               onClick={() => setSuggestion(null)}
               className="px-5 py-2.5 glass-button border-2 border-border rounded-xl text-sm font-semibold text-muted-foreground hover:text-foreground hover:border-primary/30 transition-all duration-300"
            >
               Dismiss
            </button>
            <button
               onClick={() => confirmSuggestion(suggestion.suggested_folder)}
               className="px-5 py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl text-sm font-bold shadow-lg shadow-primary/30 hover:scale-105 active:scale-95 transition-all duration-300 flex items-center gap-2"
            >
               <Check className="w-5 h-5" /> Accept Suggestion
            </button>
          </div>

          {suggestion.alternatives.length > 0 && (
            <div className="mt-6 pt-4 border-t-2 border-border/50">
              <p className="text-xs uppercase tracking-widest text-muted-foreground font-bold mb-3">Other Options</p>
              <div className="flex gap-2 flex-wrap">
                {suggestion.alternatives.map((alternative) => (
                  <button
                    key={alternative.folder}
                    onClick={() => confirmSuggestion(alternative.folder)}
                    className="px-3 py-2 text-xs glass-button bg-background/30 hover:bg-primary/5 border-2 border-border/50 hover:border-primary/30 rounded-lg transition-all duration-300 flex items-center gap-2 text-foreground font-medium group"
                  >
                    <Folder className="w-3.5 h-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
                    {alternative.folder} 
                    <span className="px-1.5 py-0.5 bg-muted/50 rounded text-[10px] font-bold">{Math.round(alternative.score * 100)}%</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* New Folder Input */}
      {showNewFolder && (
        <div className="glass-panel rounded-xl p-4 animate-fade-in-up border border-accent/30 bg-background/50">
          <div className="flex gap-3">
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && createFolder()}
              placeholder="Enter folder name..."
              className="flex-1 px-4 py-2.5 glass-input rounded-xl text-foreground outline-none"
              autoFocus
            />
            <button
              onClick={createFolder}
              className="px-6 py-2.5 bg-accent hover:bg-accent/90 text-accent-foreground font-bold rounded-xl hover-scale"
            >
              Create
            </button>
            <button
              onClick={() => {
                setShowNewFolder(false)
                setNewFolderName('')
              }}
              className="px-4 py-2.5 glass-button rounded-xl"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[400px]">
        {/* Folders List */}
        <div className="glass-panel rounded-xl p-0 overflow-hidden flex flex-col border border-border/50 bg-background/40">
          <div className="p-4 border-b border-border/50 bg-background/30">
            <div className="relative">
              <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={folderSearch}
                onChange={(e) => setFolderSearch(e.target.value)}
                placeholder="Search folders..."
                className="w-full pl-9 pr-3 py-2 text-sm bg-background/30 border border-border/50 rounded-lg text-foreground focus:border-primary/50 outline-none transition-colors"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
            {filteredFolders.map((folder) => (
              <div key={folder.id} className="relative group/folder">
                {renamingFolder?.id === folder.id ? (
                  <div className="flex gap-2 p-2">
                    <input
                      type="text"
                      value={newFolderNameEdit}
                      onChange={(e) => setNewFolderNameEdit(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') renameFolder(folder.id, newFolderNameEdit)
                        if (e.key === 'Escape') {
                          setRenamingFolder(null)
                          setNewFolderNameEdit('')
                        }
                      }}
                      className="flex-1 px-3 py-1.5 glass-input rounded-lg text-foreground text-sm"
                      autoFocus
                    />
                    <button
                      onClick={() => renameFolder(folder.id, newFolderNameEdit)}
                      className="p-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
                    >
                      <Check className="w-4 h-4" />
                    </button>
              <button
                      onClick={() => {
                        setRenamingFolder(null)
                        setNewFolderNameEdit('')
                      }}
                      className="p-1.5 glass-button rounded-lg"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div
                onClick={() => setSelectedFolder(folder.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedFolder(folder.id) }}
                    className={`w-full text-left p-3 rounded-lg transition-all duration-200 flex items-center justify-between group cursor-pointer ${
                  selectedFolder === folder.id
                    ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20'
                    : 'hover:bg-background/50 text-muted-foreground hover:text-foreground'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Folder className={`w-4 h-4 ${selectedFolder === folder.id ? 'fill-current' : ''}`} />
                  <span className="font-medium text-sm">{folder.name}</span>
                </div>
                    <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                   selectedFolder === folder.id ? 'bg-white/20' : 'bg-black/10'
                }`}>
                   {folder.notes_count}
                </span>
                      <div className="relative">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setShowFolderMenu(showFolderMenu === folder.id ? null : folder.id)
                          }}
                          className={`p-1 rounded-md opacity-0 group-hover/folder:opacity-100 transition-opacity ${
                            selectedFolder === folder.id
                              ? 'hover:bg-white/20 text-primary-foreground'
                              : 'hover:bg-background/50'
                          }`}
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>
                        {showFolderMenu === folder.id && (
                          <div className="absolute right-0 mt-1 w-36 glass-panel rounded-lg shadow-elevated border border-border/50 py-1 z-50">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                setRenamingFolder({ id: folder.id, name: folder.name })
                                setNewFolderNameEdit(folder.name)
                                setShowFolderMenu(null)
                              }}
                              className="w-full text-left px-3 py-2 text-sm hover:bg-background/50 flex items-center gap-2 text-foreground"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                              Rename
                            </button>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                deleteFolder(folder.id, folder.name)
                                setShowFolderMenu(null)
                              }}
                              className="w-full text-left px-3 py-2 text-sm hover:bg-destructive/10 text-destructive flex items-center gap-2"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {filteredFolders.length === 0 && (
              <div className="text-center py-8 px-4">
                <p className="text-sm text-muted-foreground">
                  {folders.length === 0
                    ? 'No folders yet.'
                    : 'No matching folders.'}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Notes List */}
        <div className="lg:col-span-2 glass-panel rounded-xl p-0 overflow-hidden flex flex-col border border-border/50 bg-background/40">
          <div className="p-4 border-b border-border/50 bg-background/30 flex items-center justify-between">
            <h3 className="font-semibold flex items-center gap-2 text-foreground">
              <FileText className="w-5 h-5 text-primary" />
              {selectedFolder ? selectedFolderDetails?.name : 'Select a folder'}
            </h3>
            {selectedFolderDetails && (
              <span className="text-xs bg-primary/10 text-primary px-3 py-1 rounded-full border border-primary/20">
                {selectedFolderDetails.notes_count} notes
              </span>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
            {selectedFolder ? (
              <div className="space-y-2">
                {notes.map((note) => (
                  <div
                    key={note.id}
                    className="p-4 border border-border/50 rounded-xl bg-background/30 hover:bg-background/50 transition-all cursor-pointer group/note hover-lift"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                         <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover/note:bg-primary/20 transition-colors border border-primary/20">
                            <FileText className="w-5 h-5 text-primary" />
                         </div>
                         <div>
                            <p className="font-medium text-foreground group-hover/note:text-primary transition-colors">{note.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {(note.size / 1024).toFixed(1)} KB • {new Date(note.updated_at).toLocaleDateString()}
                            </p>
                         </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setShowMoveDialog({ noteId: note.id, noteName: note.name })
                          }}
                          className="p-2 rounded-lg hover:bg-primary/10 text-muted-foreground hover:text-primary opacity-0 group-hover/note:opacity-100 transition-all"
                          title="Move note"
                        >
                          <Move className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteNote(note.id, note.name)
                          }}
                          className="p-2 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive opacity-0 group-hover/note:opacity-100 transition-all"
                          title="Delete note"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
                {notes.length === 0 && (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-background/30 rounded-full flex items-center justify-center mx-auto mb-3 border border-border/50">
                       <FileText className="w-8 h-8 text-muted-foreground opacity-50" />
                    </div>
                    <p className="text-muted-foreground">Empty folder</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">Upload a file to get started</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <div className="w-20 h-20 bg-background/30 rounded-full flex items-center justify-center mb-4 animate-pulse-glow border border-border/50">
                   <Folder className="w-10 h-10 text-primary/30" />
                </div>
                <p className="font-medium">Select a folder to view notes</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Move Note Dialog */}
      {showMoveDialog && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in">
          <div className="glass-panel rounded-2xl p-6 max-w-md w-full mx-4 border border-border/50 shadow-floating animate-slide-up-bounce">
            <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
              <Move className="w-5 h-5 text-primary" />
              Move Note
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Move <strong className="text-foreground">"{showMoveDialog.noteName}"</strong> to:
            </p>
            <select
              value={targetFolderId}
              onChange={(e) => setTargetFolderId(e.target.value)}
              className="w-full px-4 py-3 glass-input rounded-xl text-foreground mb-4 border-2 border-border focus:border-primary/50 outline-none"
            >
              <option value="">Select a folder...</option>
              {folders
                .filter((f) => f.id !== selectedFolder)
                .map((folder) => (
                  <option key={folder.id} value={folder.id}>
                    {folder.name}
                  </option>
                ))}
            </select>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setShowMoveDialog(null)
                  setTargetFolderId('')
                }}
                className="px-4 py-2 glass-button rounded-xl text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={() => moveNote(showMoveDialog.noteId, showMoveDialog.noteName, targetFolderId)}
                disabled={!targetFolderId}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium flex items-center gap-2"
              >
                <Move className="w-4 h-4" />
                Move
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
