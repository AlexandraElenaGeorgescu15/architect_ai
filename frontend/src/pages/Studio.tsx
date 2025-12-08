import { useState, useEffect, useMemo, useCallback, memo } from 'react'
import { useGeneration } from '../hooks/useGeneration'
import { useContext } from '../hooks/useContext'
import { useArtifactStore } from '../stores/artifactStore'
import { ArtifactType, listArtifacts } from '../services/generationService'
import UnifiedStudioTabs from '../components/UnifiedStudioTabs'
import { useLocation } from 'react-router-dom'
import { useUIStore } from '../stores/uiStore'

function Studio() {
  const [meetingNotes, setMeetingNotes] = useState('')
  const [selectedArtifactType, setSelectedArtifactType] = useState<ArtifactType>('mermaid_erd')
  const [contextId, setContextId] = useState<string | null>(null)
  
  const { isGenerating, progress, generate, clearProgress } = useGeneration()
  const { isBuilding, build } = useContext()
  const { artifacts, getArtifactsByType, setArtifacts, setLoading } = useArtifactStore()
  const { addNotification } = useUIStore()
  const location = useLocation()

  // Handle applied template from navigation state
  useEffect(() => {
    if (location.state?.appliedTemplate) {
      const payload = location.state.appliedTemplate
      setMeetingNotes(payload.meeting_notes)
      if (payload.artifact_types?.length) {
        setSelectedArtifactType(payload.artifact_types[0])
      }
      
      // Clean up state
      window.history.replaceState({}, document.title)
    }
  }, [location.state])

  // Load artifacts on mount and when location changes
  useEffect(() => {
    const loadArtifacts = async () => {
      try {
        setLoading(true)
        const loadedArtifacts = await listArtifacts()
        setArtifacts(loadedArtifacts)
      } catch (error) {
        console.error('Failed to load artifacts:', error)
      } finally {
        setLoading(false)
      }
    }
    loadArtifacts()
    
    // Also reload when window regains focus (user navigated back)
    const handleFocus = () => {
      loadArtifacts()
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [setArtifacts, setLoading])

  // Memoize artifact types to prevent recreation on every render
  const artifactTypes = useMemo<{ value: ArtifactType; label: string; category: string }[]>(() => [
    // Mermaid Diagrams (Fully Parsable to Canvas - 7 types)
    { value: 'mermaid_flowchart', label: 'Flowchart', category: 'Mermaid' },
    { value: 'mermaid_erd', label: 'ERD Diagram', category: 'Mermaid' },
    { value: 'mermaid_class', label: 'Class Diagram', category: 'Mermaid' },
    { value: 'mermaid_state', label: 'State Diagram', category: 'Mermaid' },
    { value: 'mermaid_sequence', label: 'Sequence Diagram', category: 'Mermaid' },
    { value: 'mermaid_architecture', label: 'Architecture Diagram', category: 'Mermaid' },
    { value: 'mermaid_api_sequence', label: 'API Sequence Diagram', category: 'Mermaid' },
    // Mermaid Diagrams (Recognized & Validated - 6 types)
    { value: 'mermaid_gantt', label: 'Gantt Chart', category: 'Mermaid' },
    { value: 'mermaid_pie', label: 'Pie Chart', category: 'Mermaid' },
    { value: 'mermaid_journey', label: 'User Journey', category: 'Mermaid' },
    { value: 'mermaid_git_graph', label: 'Git Graph', category: 'Mermaid' },
    { value: 'mermaid_mindmap', label: 'Mindmap', category: 'Mermaid' },
    { value: 'mermaid_timeline', label: 'Timeline', category: 'Mermaid' },
    // C4 Diagrams
    { value: 'mermaid_c4_context', label: 'C4 Context', category: 'Mermaid' },
    { value: 'mermaid_c4_container', label: 'C4 Container', category: 'Mermaid' },
    { value: 'mermaid_c4_component', label: 'C4 Component', category: 'Mermaid' },
    { value: 'mermaid_c4_deployment', label: 'C4 Deployment', category: 'Mermaid' },
    // Other Mermaid
    { value: 'mermaid_data_flow', label: 'Data Flow Diagram', category: 'Mermaid' },
    { value: 'mermaid_user_flow', label: 'User Flow Diagram', category: 'Mermaid' },
    { value: 'mermaid_component', label: 'Component Diagram', category: 'Mermaid' },
    { value: 'mermaid_system_overview', label: 'System Overview', category: 'Mermaid' },
    { value: 'mermaid_uml', label: 'UML Diagram', category: 'Mermaid' },
    // HTML Diagrams (one for each Mermaid type)
    { value: 'html_flowchart', label: 'HTML Flowchart', category: 'HTML' },
    { value: 'html_erd', label: 'HTML ERD', category: 'HTML' },
    { value: 'html_class', label: 'HTML Class Diagram', category: 'HTML' },
    { value: 'html_state', label: 'HTML State Diagram', category: 'HTML' },
    { value: 'html_sequence', label: 'HTML Sequence', category: 'HTML' },
    { value: 'html_architecture', label: 'HTML Architecture', category: 'HTML' },
    { value: 'html_api_sequence', label: 'HTML API Sequence', category: 'HTML' },
    { value: 'html_gantt', label: 'HTML Gantt Chart', category: 'HTML' },
    { value: 'html_pie', label: 'HTML Pie Chart', category: 'HTML' },
    { value: 'html_journey', label: 'HTML User Journey', category: 'HTML' },
    { value: 'html_git_graph', label: 'HTML Git Graph', category: 'HTML' },
    { value: 'html_mindmap', label: 'HTML Mindmap', category: 'HTML' },
    { value: 'html_timeline', label: 'HTML Timeline', category: 'HTML' },
    { value: 'html_c4_context', label: 'HTML C4 Context', category: 'HTML' },
    { value: 'html_c4_container', label: 'HTML C4 Container', category: 'HTML' },
    { value: 'html_c4_component', label: 'HTML C4 Component', category: 'HTML' },
    { value: 'html_c4_deployment', label: 'HTML C4 Deployment', category: 'HTML' },
    { value: 'html_data_flow', label: 'HTML Data Flow', category: 'HTML' },
    { value: 'html_user_flow', label: 'HTML User Flow', category: 'HTML' },
    { value: 'html_component', label: 'HTML Component', category: 'HTML' },
    { value: 'html_system_overview', label: 'HTML System Overview', category: 'HTML' },
    { value: 'html_uml', label: 'HTML UML', category: 'HTML' },
    // Code Artifacts
    { value: 'code_prototype', label: 'Code Prototype', category: 'Code' },
    { value: 'dev_visual_prototype', label: 'Visual Prototype', category: 'Code' },
    { value: 'api_docs', label: 'API Documentation', category: 'Code' },
    // PM Artifacts
    { value: 'jira', label: 'JIRA Tasks', category: 'PM' },
    { value: 'workflows', label: 'Workflows', category: 'PM' },
    { value: 'backlog', label: 'Backlog', category: 'PM' },
    { value: 'personas', label: 'Personas', category: 'PM' },
    { value: 'estimations', label: 'Estimations', category: 'PM' },
    { value: 'feature_scoring', label: 'Feature Scoring', category: 'PM' },
  ], [])

  return (
    <div className="h-full flex flex-col animate-fade-in-up min-h-0">
      <div className="flex-1 min-h-0 px-4 py-3">
        <UnifiedStudioTabs
        meetingNotes={meetingNotes}
        setMeetingNotes={setMeetingNotes}
        selectedArtifactType={selectedArtifactType}
        setSelectedArtifactType={setSelectedArtifactType}
        contextId={contextId}
        setContextId={setContextId}
        isGenerating={isGenerating}
        progress={progress}
        generate={generate}
        clearProgress={clearProgress}
        isBuilding={isBuilding}
        build={build}
        artifacts={artifacts}
        getArtifactsByType={getArtifactsByType}
        artifactTypes={artifactTypes}
        />
      </div>
    </div>
  )
}

export default memo(Studio)
