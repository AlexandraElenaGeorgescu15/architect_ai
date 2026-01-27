import api from './api'

export interface ClusterResult {
    cluster_labels: number[]
    cluster_stats: Record<string, {
        size: number
        samples: string[]
        avg_complexity: number
        avg_lines: number
    }>
    n_clusters: number
    method: string
    note?: string
}

export interface ClusterResponse {
    success: boolean
    result: ClusterResult
    files_analyzed: number
    message?: string
}

export interface ClusteringRequest {
    n_clusters?: number
    max_files?: number
}

/**
 * Cluster project code files using backend ML.
 */
export async function clusterProjectCode(request: ClusteringRequest = {}): Promise<ClusterResponse> {
    const response = await api.post('/api/analysis/ml-features/project/cluster', request)
    return response.data as ClusterResponse
}
