import api from './api'

export interface ArtifactVersion {
  version: number
  artifact_id: string
  artifact_type: string
  content: string
  metadata: Record<string, unknown>
  created_at: string
  is_current: boolean
}

export interface VersionComparison {
  version1: { version: number; created_at: string; size: number; lines: number }
  version2: { version: number; created_at: string; size: number; lines: number }
  differences: { size_diff: number; lines_diff: number; similarity: number }
}

export async function listVersions(artifactId: string): Promise<ArtifactVersion[]> {
  const response = await api.get<ArtifactVersion[]>(`/api/versions/${artifactId}`)
  return response.data
}

export async function compareVersions(
  artifactId: string,
  version1: number,
  version2: number
): Promise<VersionComparison> {
  const response = await api.post<VersionComparison>(
    `/api/versions/${artifactId}/compare?version1=${version1}&version2=${version2}`,
    {}
  )
  return response.data
}

