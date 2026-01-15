/**
 * Project Service - Shows which projects are being indexed by RAG
 * 
 * Note: RAG automatically indexes ALL projects in the parent directory
 * (excluding Architect.AI itself). This service provides visibility into what's indexed.
 */

import api from './api'

export interface ProjectInfo {
  path: string
  name: string
  score: number
  is_selected: boolean
  markers: string[]  // e.g., ["Node.js", "Angular", "Has src/"]
}

export interface ProjectTargetResponse {
  current_target: string
  tool_directory: string
  available_projects: ProjectInfo[]
  configured_path: string | null
}

/**
 * Get information about all indexed projects
 */
export async function getProjectInfo(): Promise<ProjectTargetResponse> {
  const response = await api.get<ProjectTargetResponse>('/api/project-target/')
  return response.data
}

/**
 * Clear analysis cache (KG, Pattern Mining) - useful after project changes
 */
export async function clearAnalysisCache(): Promise<{ success: boolean; cleared_files: string[] }> {
  const response = await api.post<{ success: boolean; cleared_files: string[] }>('/api/project-target/clear-cache')
  return response.data
}
