import api, { extractData } from './api'

export interface MetricsStats {
  counters: Record<string, number>
  gauges: Record<string, number>
  timers: Record<string, { count: number; sum: number; avg: number }>
  histograms: Record<string, any>
}

/**
 * Get metrics statistics.
 */
export async function getMetricsStats(): Promise<MetricsStats> {
  const response = await api.get<MetricsStats>('/api/metrics/stats')
  return extractData(response)
}

