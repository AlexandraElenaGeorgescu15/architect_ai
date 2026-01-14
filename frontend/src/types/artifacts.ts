/**
 * Artifact Types for Architect.AI
 */

export type ArtifactType =
  | 'mermaid_erd'
  | 'mermaid_flowchart'
  | 'mermaid_sequence'
  | 'mermaid_class'
  | 'mermaid_state'
  | 'mermaid_gantt'
  | 'mermaid_pie'
  | 'mermaid_journey'
  | 'mermaid_mindmap'
  | 'mermaid_timeline'
  | 'mermaid_git_graph'
  | 'mermaid_architecture'
  | 'mermaid_component'
  | 'mermaid_api_sequence'
  | 'mermaid_data_flow'
  | 'mermaid_user_flow'
  | 'mermaid_system_overview'
  | 'mermaid_uml'
  | 'mermaid_c4_context'
  | 'mermaid_c4_container'
  | 'mermaid_c4_component'
  | 'mermaid_c4_deployment'
  | 'html_erd'
  | 'html_flowchart'
  | 'html_sequence'
  | 'html_class'
  | 'html_state'
  | 'html_gantt'
  | 'html_pie'
  | 'html_journey'
  | 'html_mindmap'
  | 'html_timeline'
  | 'html_git_graph'
  | 'html_architecture'
  | 'html_component'
  | 'html_api_sequence'
  | 'html_data_flow'
  | 'html_user_flow'
  | 'html_system_overview'
  | 'html_uml'
  | 'html_c4_context'
  | 'html_c4_container'
  | 'html_c4_component'
  | 'html_c4_deployment'
  | 'dev_visual_prototype'
  | 'code_prototype'
  | 'api_docs'
  | 'backlog'
  | 'jira'
  | 'estimations'
  | 'personas'
  | 'feature_scoring'
  | 'workflows'

export interface Artifact {
  id: string
  type: ArtifactType | string
  content: string
  html_content?: string
  metadata?: {
    model_used?: string
    validation_score?: number
    created_at?: string
    version?: number
    [key: string]: any
  }
  created_at?: string
  updated_at?: string
}

export interface ArtifactVersion {
  version: number
  artifact_id: string
  artifact_type: string
  content: string
  metadata: {
    model_used?: string
    validation_score?: number
    [key: string]: any
  }
  created_at: string
  is_current: boolean
}
