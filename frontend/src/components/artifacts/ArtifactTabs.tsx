import { useState } from 'react'
import { Artifact } from '../../types'
import { useArtifactStore } from '../../stores/artifactStore'
import ArtifactCard from './ArtifactCard'
import ArtifactViewer from './ArtifactViewer'
import { Search } from 'lucide-react'

type TabType = 'all' | 'diagrams' | 'code' | 'docs' | 'pm'

const tabs: { value: TabType; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'diagrams', label: 'Diagrams' },
  { value: 'code', label: 'Code' },
  { value: 'docs', label: 'Docs' },
  { value: 'pm', label: 'PM' },
]

export default function ArtifactTabs() {
  const [activeTab, setActiveTab] = useState<TabType>('all')
  const { artifacts, currentArtifact, setCurrentArtifact } = useArtifactStore()

  const filteredArtifacts = artifacts.filter((artifact) => {
    if (activeTab === 'all') return true
    if (activeTab === 'diagrams') return artifact.type.startsWith('mermaid_')
    if (activeTab === 'code') return artifact.type === 'code_prototype'
    if (activeTab === 'docs') return artifact.type === 'api_docs'
    if (activeTab === 'pm') {
      return ['jira', 'workflows', 'backlog', 'personas', 'estimations', 'feature_scoring'].includes(artifact.type)
    }
    return true
  })

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
               {tab.label} <span className="opacity-50 ml-1 text-[10px]">{tab.value === 'all' ? artifacts.length : artifacts.filter(a => {
                  if (tab.value === 'diagrams') return a.type.startsWith('mermaid_')
                  if (tab.value === 'code') return a.type === 'code_prototype'
                  if (tab.value === 'docs') return a.type === 'api_docs'
                  if (tab.value === 'pm') return ['jira', 'workflows', 'backlog', 'personas', 'estimations', 'feature_scoring'].includes(a.type)
                  return true
               }).length}</span>
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
