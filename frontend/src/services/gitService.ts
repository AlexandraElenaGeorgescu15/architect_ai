import api from './api'

export interface GitCommitResponse {
    success: boolean
    branch: string
    files_updated: string[]
    pushed: boolean
    pr_url: string | null
    message: string
}

export async function commitArtifactToRepo(artifactId: string): Promise<GitCommitResponse> {
    const response = await api.post<GitCommitResponse>(`/api/git/commit/${artifactId}`)
    return response.data
}
