import api, { extractData } from './api'

export interface GraphNode {
  id: string
  label: string
  type: string
  properties: Record<string, any>
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  properties: Record<string, any>
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphStats {
  nodes: number
  edges: number
  components: number
  avg_degree: number
}

/**
 * Get knowledge graph statistics.
 */
export async function getGraphStats(): Promise<GraphStats> {
  const response = await api.get<GraphStats>('/api/knowledge-graph/stats')
  return extractData(response)
}

/**
 * Get full knowledge graph.
 */
export async function getGraph(): Promise<GraphData> {
  const response = await api.get<GraphData>('/api/knowledge-graph/graph')
  return extractData(response)
}

/**
 * Build knowledge graph from directory.
 */
export async function buildGraph(directory: string, recursive: boolean = true): Promise<{ message: string; directory: string }> {
  const response = await api.post<{ message: string; directory: string }>('/api/knowledge-graph/build', {
    directory,
    recursive,
    use_cache: true
  })
  return extractData(response)
}

