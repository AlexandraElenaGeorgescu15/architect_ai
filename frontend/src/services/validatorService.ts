import api from './api'

export interface CustomValidator {
  id: string
  name: string
  description?: string
  rule_type: 'regex'
  pattern: string
  severity: 'error' | 'warning'
  artifact_types: string[]
  message: string
}

export async function listCustomValidators(): Promise<CustomValidator[]> {
  const response = await api.get<CustomValidator[]>('/api/validators/custom')
  return response.data
}

export async function createCustomValidator(payload: Omit<CustomValidator, 'id'>): Promise<CustomValidator> {
  const response = await api.post<CustomValidator>('/api/validators/custom', payload)
  return response.data
}

export async function deleteCustomValidator(id: string): Promise<void> {
  await api.delete(`/api/validators/custom/${id}`)
}

