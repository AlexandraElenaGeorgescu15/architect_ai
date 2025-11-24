import api from './api'
import { ArtifactType } from './generationService'

export interface Template {
  id: string
  name: string
  description: string
  meeting_notes: string
  recommended_artifacts: ArtifactType[]
  tags: string[]
  complexity: 'low' | 'medium' | 'high'
}

export interface TemplateApplyResponse {
  template: Template
  meeting_notes: string
  artifact_types: ArtifactType[]
}

export async function listTemplates(): Promise<Template[]> {
  const response = await api.get<Template[]>('/api/templates/')
  return response.data
}

export async function applyTemplate(templateId: string): Promise<TemplateApplyResponse> {
  const response = await api.post<TemplateApplyResponse>('/api/templates/apply', {
    template_id: templateId,
  })
  return response.data
}

