import { useState, useMemo } from 'react'
import { Artifact } from '../../types'
import { useArtifactStore } from '../../stores/artifactStore'
import ArtifactCard from './ArtifactCard'
import ArtifactViewer from './ArtifactViewer'
import { Search } from 'lucide-react'

type TabType = 'all' | 'diagrams' | 'code' | 'docs' | 'pm' | 'html' | 'prototypes'

const tabs: { value: TabType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'diagrams', label: 'Diagrams' },
  { value: 'html', label: 'HTML' },
  { value: 'code', label: 'Code' },
  { value: 'prototypes', label: 'Prototypes' },
  { value: 'docs', label: 'Docs' },
  { value: 'pm', label: 'PM' },
]

interface ArtifactTabsProps {
  searchQuery?: string
}

export default function ArtifactTabs({ searchQuery = '' }: ArtifactTabsProps) {
  const [activeTab, setActiveTab] = useState<TabType>('all')
  const { artifacts, currentArtifact, setCurrentArtifact, currentFolderId } = useArtifactStore()

  const filteredArtifacts = useMemo(() => {
    let filtered = artifacts
    
    // Apply folder filter first
    if (currentFolderId) {
      filtered = filtered.filter((artifact) => (artifact as any).folder_id === currentFolderId)
    }
    
    // Apply tab filter
    if (activeTab !== 'all') {
      filtered = filtered.filter((artifact) => {
        if (activeTab === 'diagrams') return artifact.type.startsWith('mermaid_')
        if (activeTab === 'html') return artifact.type.startsWith('html_')
        if (activeTab === 'code') return artifact.type === 'code_prototype'
        if (activeTab === 'prototypes') return ['visual_prototype', 'interactive_prototype', 'html_component'].includes(artifact.type)
        if (activeTab === 'docs') return artifact.type === 'api_docs'
        if (activeTab === 'pm') {
          return ['jira', 'workflows', 'backlog', 'personas', 'estimations', 'feature_scoring'].includes(artifact.type)
        }
        return true
      })
    }
    
    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter((artifact) => 
        artifact.type.toLowerCase().includes(query) ||
        artifact.content.toLowerCase().includes(query) ||
        (artifact.model_used && artifact.model_used.toLowerCase().includes(query))
      )
    }
    
    return filtered
  }, [artifacts, activeTab, searchQuery, currentFolderId])

  return (
    <div className="space-y-6 h-full flex flex-col" data-tour="artifacts-panel">
      {/* Tabs */}
      <div className="flex items-center justify-between">
         <div className="glass-panel rounded-full p-1 flex gap-1 bg-background/40 border-border/50 inline-flex">
           {tabs.map((tab) => (
             <button
               key={tab.value}
               onClick={() => setActiveTab(tab.value)}
               className={`px-4 py-1.5 text-xs font-medium rounded-full transition-all duration-300 ${
                 activeTab === tab.value
                   ? 'bg-primary text-primary-foreground shadow-md'
                   : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
               }`}
             >
               {tab.label} <span className="opacity-50 ml-1 text-[10px]">{(() => {
                  // Filter by folder first if one is selected
                  const folderFiltered = currentFolderId 
                    ? artifacts.filter(a => (a as any).folder_id === currentFolderId)
                    : artifacts
                  
                  if (tab.value === 'all') return folderFiltered.length
                  return folderFiltered.filter(a => {
                    if (tab.value === 'diagrams') return a.type.startsWith('mermaid_')
                    if (tab.value === 'html') return a.type.startsWith('html_')
                    if (tab.value === 'code') return a.type === 'code_prototype'
                    if (tab.value === 'prototypes') return ['visual_prototype', 'interactive_prototype', 'html_component'].includes(a.type)
                    if (tab.value === 'docs') return a.type === 'api_docs'
                    if (tab.value === 'pm') return ['jira', 'workflows', 'backlog', 'personas', 'estimations', 'feature_scoring'].includes(a.type)
                    return true
                  }).length
                })()}</span>
             </button>
           ))}
         </div>
      </div>

      {/* Content */}
      {currentArtifact ? (
        <div className="flex-1 flex flex-col space-y-4 min-h-0">
          <button
            onClick={() => setCurrentArtifact(null)}
            className="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-2 w-fit px-3 py-1.5 glass-button rounded-lg"
          >
            ← Back to Library
          </button>
          <div className="flex-1 overflow-hidden glass-panel rounded-2xl border border-border/50 bg-card/50 shadow-lg">
             <ArtifactViewer
               artifact={currentArtifact}
               onUpdate={(updated) => {
                 useArtifactStore.getState().updateArtifact(updated.id, updated)
                 setCurrentArtifact(updated)
               }}
             />
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 -mr-2">
           {filteredArtifacts.length === 0 ? (
             <div className="h-full flex flex-col items-center justify-center text-center py-12 text-muted-foreground glass-panel rounded-2xl border-dashed border-border/50 bg-transparent">
               <div className="w-16 h-16 bg-background/50 rounded-full flex items-center justify-center mb-4">
                  <Search className="w-8 h-8 opacity-30" />
               </div>
               <p className="text-lg font-medium">No artifacts found</p>
               <p className="text-sm mt-2 opacity-60">Generate artifacts in the Studio to see them here</p>
             </div>
           ) : (
             <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
               {filteredArtifacts.map((artifact) => (
                 <div key={artifact.id} className="animate-fade-in-up">
                    <ArtifactCard artifact={artifact} />
                 </div>
               ))}
             </div>
           )}
        </div>
      )}
    </div>
  )
}
